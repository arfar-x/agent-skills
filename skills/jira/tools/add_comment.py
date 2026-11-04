"""add_comment: post a comment on an issue (write, gated), once per ``marker``.

Idempotent by ``marker``: when a comment on the issue already carries the marker line, nothing is posted, so a run that is
resumed after a crash cannot post the same comment twice.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from lib.jira_client import get_client
from tools._common import require_str, run_tool


def add_comment(issue_key: str, body: str, marker: Optional[str] = None, confirm: bool = False) -> Dict[str, Any]:
    """Comment on ``issue_key`` with ``body`` (Jira wiki markup or plain text).

    Args:
        issue_key: Issue key, e.g. ``PAY-412``.
        body: The comment text.
        marker: A unique line appended to the comment. A comment already carrying it is returned instead of posting another.
        confirm: Must be ``True`` (or JIRA_AUTO_CONFIRM_WRITES=true) for the comment to be posted.

    Returns:
        ``{"confirmed": true, "comment": {...}}``, ``{"confirmed": true, "skipped": "exists", "comment": {...}}``, or the
        confirmation request ``{"confirmed": false, "requires_confirmation": true, "pending_action": {...}}``.
    """

    def _run() -> Dict[str, Any]:
        key, text = require_str(issue_key, "issue_key"), require_str(body, "body")
        line = marker.strip() if isinstance(marker, str) and marker.strip() else None
        client = get_client()
        full = f"{text}\n\n{line}" if line else text
        if not confirm and not client.config.auto_confirm_writes:
            return {"confirmed": False, "requires_confirmation": True,
                    "pending_action": {"action": "add_comment", "issue_key": key, "body": full}}
        if line:
            for existing in client.get_comments(key):
                if line in (existing.body or ""):
                    return {"confirmed": True, "skipped": "exists", "comment": {"id": existing.id, "author": existing.author}}
        return {"confirmed": True, "comment": client.add_comment(key, full)}

    return run_tool("add_comment", _run)
