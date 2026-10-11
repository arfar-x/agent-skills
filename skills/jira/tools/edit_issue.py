"""edit_issue: update fields on an existing issue or subtask.

Thin tool: validates input and delegates to the shared JiraClient. This is
a write operation and follows the same confirmation gate as worklog() and
transition(). Works on subtasks the same way as parent issues -- pass the
subtask's own issue_key.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from lib.jira_client import get_client
from lib.text_patch import PatchError, replace_pairs
from tools._common import ToolInputError, require_str, run_tool


def edit_issue(
    issue_key: str,
    summary: Optional[str] = None,
    description: Optional[str] = None,
    labels: Optional[List[str]] = None,
    assignee_account_id: Optional[str] = None,
    priority: Optional[str] = None,
    components: Optional[List[str]] = None,
    custom_fields: Optional[Dict[str, Any]] = None,
    confirm: bool = False,
    description_find: Optional[List[str]] = None,
    description_replace: Optional[List[str]] = None,
    add_labels: Optional[List[str]] = None,
    remove_labels: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Update one or more fields on an existing issue (or subtask).

    Args:
        issue_key: Issue key, e.g. ``PAY-412``.
        summary: New title (omit to leave unchanged).
        description: New plain-text description (omit to leave unchanged).
        labels: New label list, replacing the existing one (omit to leave
            unchanged).
        assignee_account_id: A user's ``account_id`` -- resolve a name via
            ``search_users`` first, never guess it from a display name.
        priority: New priority name, e.g. ``"High"``.
        components: New component name list, replacing the existing one.
        custom_fields: Any field to set/replace by its real
            ``customfield_NNNNN`` id -- resolve the id and its expected
            value shape via ``list_fields`` first, never guess either.
        description_find: Exact texts to find in the current description,
            paired in order with ``description_replace`` -- a partial edit,
            instead of resending the whole description. Each must occur
            exactly once. Can't be combined with ``description``.
        description_replace: Replacement for each ``description_find``.
        add_labels: Labels to add, keeping the existing ones.
        remove_labels: Labels to remove, keeping the rest. Can't be
            combined with ``labels``.
        confirm: Must be ``True`` (or JIRA_AUTO_CONFIRM_WRITES=true) for
            the edit to actually execute. Hermes should set this only
            after the user has explicitly confirmed the action.

    Returns:
        On success: ``{"confirmed": true, "issue": {...}}``.
        When confirmation is required first: ``{"confirmed": false,
        "requires_confirmation": true, "pending_action": {...}}``.
    """

    def _run() -> Dict[str, Any]:
        key = require_str(issue_key, "issue_key")

        finds, replaces = list(description_find or []), list(description_replace or [])
        if (finds or replaces) and description is not None:
            raise ToolInputError("Pass either 'description' or 'description_find'/'description_replace', not both.")
        if (add_labels or remove_labels) and labels is not None:
            raise ToolInputError("Pass either 'labels' or 'add_labels'/'remove_labels', not both.")
        if (
            summary is None
            and description is None
            and not finds
            and not add_labels
            and not remove_labels
            and labels is None
            and assignee_account_id is None
            and priority is None
            and components is None
            and not custom_fields
        ):
            raise ToolInputError(
                "At least one of 'summary', 'description', 'labels', "
                "'assignee_account_id', 'priority', 'components', or "
                "'custom_fields' must be provided."
            )

        client = get_client()

        new_description = description
        description_edits: List[dict] = []
        if finds or replaces:
            current = client.get_issue(key, fields=["description"]).description or ""
            try:
                new_description, description_edits = replace_pairs(current, finds, replaces)
            except PatchError as exc:
                raise ToolInputError(f"description: {exc}") from exc

        if not confirm and not client.config.auto_confirm_writes:
            return {
                "confirmed": False,
                "requires_confirmation": True,
                "pending_action": {
                    "action": "edit_issue",
                    "issue_key": key,
                    "summary": summary,
                    "description": description,
                    "labels": labels,
                    "assignee_account_id": assignee_account_id,
                    "priority": priority,
                    "components": components,
                    "custom_fields": custom_fields,
                    "description_edits": description_edits,
                    "add_labels": add_labels,
                    "remove_labels": remove_labels,
                },
            }

        updated = client.edit_issue(
            key,
            summary=summary,
            description=new_description,
            labels=labels,
            assignee_account_id=assignee_account_id,
            priority=priority,
            components=components,
            custom_fields=custom_fields,
            add_labels=add_labels,
            remove_labels=remove_labels,
        )
        result: Dict[str, Any] = {"confirmed": True, "issue": updated.to_dict()}
        if description_edits:
            result["description_edits"] = description_edits
        return result

    return run_tool("edit_issue", _run)
