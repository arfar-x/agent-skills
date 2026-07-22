"""worklog_delete: permanently delete a worklog entry.

Thin tool: delegates to the shared JiraClient. This is a destructive
write operation and follows the same confirmation gate as worklog(),
transition(), and worklog_edit() -- it refuses to execute unless
confirm=True (or JIRA_AUTO_CONFIRM_WRITES is enabled).
"""

from __future__ import annotations

from typing import Any, Dict

from lib.jira_client import get_client
from tools._common import require_str, run_tool


def worklog_delete(issue_key: str, worklog_id: str, confirm: bool = False) -> Dict[str, Any]:
    """Permanently delete a worklog entry. Cannot be undone.

    Args:
        issue_key: Issue key, e.g. ``PAY-412``.
        worklog_id: The worklog entry's id (from ``issue_summary``'s
            ``worklogs[].id``, or the id returned by ``worklog()``).
        confirm: Must be ``True`` (or JIRA_AUTO_CONFIRM_WRITES=true) for
            the deletion to actually execute.

    Returns:
        On success: ``{"confirmed": true, "issue_key": ..., "worklog_id": ...,
        "deleted": true}``. When confirmation is required first:
        ``{"confirmed": false, "requires_confirmation": true, "pending_action": {...}}``.
    """

    def _run() -> Dict[str, Any]:
        key = require_str(issue_key, "issue_key")
        wl_id = require_str(worklog_id, "worklog_id")
        client = get_client()

        if not confirm and not client.config.auto_confirm_writes:
            return {
                "confirmed": False,
                "requires_confirmation": True,
                "pending_action": {"action": "worklog_delete", "issue_key": key, "worklog_id": wl_id},
            }

        client.delete_worklog(key, wl_id)
        return {"confirmed": True, "issue_key": key, "worklog_id": wl_id, "deleted": True}

    return run_tool("worklog_delete", _run)
