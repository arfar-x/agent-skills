"""ensure_mr: open a merge request for a branch, or return the one that is already open (write).

Idempotent by source branch: asking twice never makes a second merge request. The assignee is a GitLab username.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from lib.glab_client import get_client
from tools._common import ToolInputError, require_str, resolve_project, run_tool


def ensure_mr(
    source_branch: str,
    target_branch: str,
    title: str,
    description: str = "",
    project: Optional[str] = None,
    assignee_username: Optional[str] = None,
    labels: Optional[List[str]] = None,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Open an MR from ``source_branch`` into ``target_branch``, unless one is already open for that source branch.

    Returns ``{"confirmed": true, "created": bool, "mr": {iid, web_url, ...}}``.
    """

    def _run() -> Dict[str, Any]:
        proj = resolve_project(project)
        source, target = require_str(source_branch, "source_branch"), require_str(target_branch, "target_branch")
        heading = require_str(title, "title")
        client = get_client()
        if not confirm and not client.config.auto_confirm_writes:
            return {"confirmed": False, "requires_confirmation": True,
                    "pending_action": {"action": "ensure_mr", "project": proj, "source_branch": source, "target_branch": target,
                                       "title": heading, "assignee": assignee_username}}
        existing = client.find_open_mr(proj, source)
        if existing is not None:
            return {"confirmed": True, "created": False, "mr": _brief(existing)}
        assignee_id: Optional[int] = None
        if assignee_username:
            assignee_id = client.user_id_for(assignee_username.strip())
            if assignee_id is None:
                raise ToolInputError(f"No GitLab user {assignee_username!r}: the merge request was not opened.")
        mr = client.create_mr(proj, source, target, heading, description or "", assignee_id, labels)
        return {"confirmed": True, "created": True, "mr": _brief(mr)}

    return run_tool("ensure_mr", _run)


def _brief(mr: Dict[str, Any]) -> Dict[str, Any]:
    return {"iid": mr.get("iid"), "web_url": mr.get("web_url"), "title": mr.get("title"), "state": mr.get("state"),
            "source_branch": mr.get("source_branch"), "target_branch": mr.get("target_branch"),
            "assignee": (mr.get("assignee") or {}).get("username")}
