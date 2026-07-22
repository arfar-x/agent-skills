"""worklog_edit: update an existing worklog entry's duration/description/date.

Thin tool: validates input, delegates to the shared JiraClient. This is a
write operation and follows the same confirmation gate as worklog() and
transition() -- it refuses to execute unless confirm=True (or
JIRA_AUTO_CONFIRM_WRITES is enabled).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from lib.jira_client import get_client
from lib.utils import (
    InvalidDateError,
    InvalidDurationError,
    format_jira_timestamp,
    parse_duration_to_seconds,
    parse_worklog_date,
)
from tools._common import ToolInputError, require_str, run_tool


def worklog_edit(
    issue_key: str,
    worklog_id: str,
    duration: Optional[str] = None,
    description: Optional[str] = None,
    date: Optional[str] = None,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Update an existing worklog entry. Only the fields you pass are changed.

    Args:
        issue_key: Issue key, e.g. ``PAY-412``.
        worklog_id: The worklog entry's id (from ``issue_summary``'s
            ``worklogs[].id``, or the id returned by ``worklog()``).
        duration: New Jira-style duration, e.g. ``"2h"``. Omit to leave
            the existing duration unchanged.
        description: New description. Omit to leave unchanged.
        date: New date -- same formats as ``worklog()``'s ``date``
            (relative, ISO date, or ISO datetime). Resolve relative
            phrasing yourself first. Omit to leave unchanged.
        confirm: Must be ``True`` (or JIRA_AUTO_CONFIRM_WRITES=true) for
            the edit to actually be submitted.

    Returns:
        On success: ``{"confirmed": true, "issue_key": ..., "worklog_id": ...,
        "worklog": {...}}``. When confirmation is required first:
        ``{"confirmed": false, "requires_confirmation": true, "pending_action": {...}}``.
    """

    def _run() -> Dict[str, Any]:
        key = require_str(issue_key, "issue_key")
        wl_id = require_str(worklog_id, "worklog_id")

        if duration is None and description is None and date is None:
            raise ToolInputError(
                "At least one of 'duration', 'description', or 'date' must be "
                "provided to edit a worklog."
            )

        seconds = None
        if duration is not None:
            if not isinstance(duration, str) or not duration.strip():
                raise ToolInputError("'duration' must be a non-empty string, e.g. '2h', '1d 30m'.")
            try:
                seconds = parse_duration_to_seconds(duration)
            except InvalidDurationError as exc:
                raise ToolInputError(str(exc)) from exc

        started = None
        if date is not None:
            try:
                started = format_jira_timestamp(parse_worklog_date(date))
            except InvalidDateError as exc:
                raise ToolInputError(str(exc)) from exc

        client = get_client()

        if not confirm and not client.config.auto_confirm_writes:
            return {
                "confirmed": False,
                "requires_confirmation": True,
                "pending_action": {
                    "action": "worklog_edit",
                    "issue_key": key,
                    "worklog_id": wl_id,
                    "duration": duration,
                    "duration_seconds": seconds,
                    "description": description,
                    "date": date,
                    "started": started,
                },
            }

        updated = client.update_worklog(
            key, wl_id, duration_seconds=seconds, description=description, started=started
        )
        return {"confirmed": True, "issue_key": key, "worklog_id": wl_id, "worklog": updated.to_dict()}

    return run_tool("worklog_edit", _run)
