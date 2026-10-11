"""get_attachments: list an issue's attachments (metadata only).

Read-only. Use it to find an attachment's id for get_attachment.
"""

from __future__ import annotations

from typing import Any, Dict

from lib.jira_client import get_client
from tools._common import require_str, run_tool


def get_attachments(issue_key: str) -> Dict[str, Any]:
    """List an issue's attachments.

    Args:
        issue_key: Issue key, e.g. ``PAY-412``.

    Returns:
        ``{"issue_key": ..., "count": N, "attachments": [{"id", "filename",
        "size_bytes", "media_type", "created", "author"}, ...]}``.
    """

    def _run() -> Dict[str, Any]:
        key = require_str(issue_key, "issue_key")
        attachments = get_client().get_attachments(key)
        return {"issue_key": key, "count": len(attachments), "attachments": attachments}

    return run_tool("get_attachments", _run)
