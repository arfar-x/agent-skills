"""search: run an arbitrary JQL query and return structured issue data.

Thin tool: validates the JQL is non-empty, delegates to the shared
JiraClient, and returns issue JSON. Query construction/interpretation is
the LLM's responsibility; this tool never rewrites or infers JQL.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from lib.jira_client import ISSUE_FIELD_MAP, get_client, resolve_issue_fields
from lib.utils import is_issue_blocked
from tools._common import ToolInputError, require_str, run_tool

#: Fetched from Jira for "blocked" detection regardless of `only`, without
#: forcing "status"/"links" into the output unless the caller asked for
#: them too -- see lib.utils.blocking_reasons().
_BLOCKED_DETECTION_FIELDS = ["status", "links"]


def search(
    jql: str,
    max_results: int = 100,
    fields: Optional[List[str]] = None,
    only: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Run a JQL query and return matching issues.

    Args:
        jql: A valid JQL query string, e.g.
            ``"project = PAY AND status = 'In Progress'"``.
        max_results: Safety cap on the number of issues returned.
        fields: Extra Jira fields to request, by id (``"customfield_10056"``)
            or by display name (``"Figma Link"``) -- names are resolved via
            ``list_fields``. Always included in each issue's
            ``custom_fields``, regardless of ``only``.
        only: Which named issue fields to fetch from Jira and include in
            the response -- the token-efficiency lever: ask for exactly
            what you need instead of everything. Valid names: ``summary``,
            ``status``, ``priority``, ``issue_type``, ``assignee``,
            ``reporter``, ``updated``, ``created``, ``due_date``,
            ``labels``, ``links``, ``description``, ``components``,
            ``subtasks``, ``original_estimate_seconds``,
            ``time_spent_seconds``, ``remaining_estimate_seconds``. Any
            other name (e.g. ``"Epic Link"``) is resolved as a Jira field
            display name and returned in ``custom_fields``.
            Defaults to every field except ``description`` and the three
            time-tracking fields when omitted. Pass ``description``
            explicitly (e.g. ``only=["summary", "description"]``) only
            when you actually need description text for a handful of
            issues -- for a single issue, prefer ``issue_summary`` or
            ``get_issue`` instead of a detailed search.

    Returns:
        ``{"jql": "...", "count": N, "issues": [...]}`` (plus
        ``"resolved_fields": {name: id}`` when names were resolved) -- each issue always
        includes ``key``, ``url``, ``custom_fields``, and ``blocked``,
        regardless of ``only``.
    """

    def _run() -> Dict[str, Any]:
        query = require_str(jql, "jql")
        client = get_client()
        named = [name for name in only if name in ISSUE_FIELD_MAP] if only is not None else None
        extra_names = [name for name in only if name not in ISSUE_FIELD_MAP] if only is not None else []
        resolved = _resolve_field_names(client, extra_names + list(fields or []))
        jira_fields, output_keys = resolve_issue_fields(named, always_fetch=_BLOCKED_DETECTION_FIELDS)
        requested_fields = jira_fields + [field_id for field_id in resolved.values() if field_id not in jira_fields]
        issues = client.search(query, max_results=max_results, fields=requested_fields)
        issue_dicts: List[Dict[str, Any]] = []
        for issue in issues:
            d = issue.to_dict(only=output_keys)
            d["blocked"] = is_issue_blocked(issue)
            issue_dicts.append(d)
        result: Dict[str, Any] = {"jql": query, "count": len(issue_dicts), "issues": issue_dicts}
        renamed = {name: field_id for name, field_id in resolved.items() if name != field_id}
        if renamed:
            result["resolved_fields"] = renamed
        return result

    return run_tool("search", _run)


def _resolve_field_names(client, names: List[str]) -> Dict[str, str]:
    """Map each requested field -- an id or a display name -- to its id.

    Ids pass through untouched; names are matched case-insensitively
    against ``list_fields`` (fetched only when a name needs it). An unknown
    name is an error listing the closest real fields, instead of a request
    Jira would reject.
    """
    resolved: Dict[str, str] = {}
    pending = []
    for name in dict.fromkeys(n.strip() for n in names if n and n.strip()):
        if name.startswith("customfield_") or name in ISSUE_FIELD_MAP.values():
            resolved[name] = name
        else:
            pending.append(name)
    if not pending:
        return resolved
    catalog = client.list_fields()
    by_id = {f["id"]: f["id"] for f in catalog if f.get("id")}
    by_name = {(f.get("name") or "").casefold(): f["id"] for f in catalog if f.get("id")}
    unknown = []
    for name in pending:
        field_id = by_id.get(name) or by_name.get(name.casefold())
        if field_id:
            resolved[name] = field_id
        else:
            unknown.append(name)
    if unknown:
        hints = sorted(
            f.get("name") for f in catalog
            if f.get("name") and any(u.casefold() in f["name"].casefold() for u in unknown)
        )[:10]
        raise ToolInputError(
            f"Unknown field(s) {unknown}. Named fields: {sorted(ISSUE_FIELD_MAP)}; "
            f"or a Jira field id/name from list_fields{f' (close: {hints})' if hints else ''}."
        )
    return resolved
