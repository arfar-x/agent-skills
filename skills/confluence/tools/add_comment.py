"""add_comment: add a comment to a page.

Thin tool: delegates to the shared ConfluenceClient. Write operation,
gated the same way every write tool in this skill is.
"""

from __future__ import annotations

from typing import Any, Dict

from lib.confluence_client import get_client
from tools._common import require_str, run_tool


def add_comment(page_id: str, body_storage: str, confirm: bool = False) -> Dict[str, Any]:
    """Add a comment to a page.

    Args:
        page_id: Page to comment on.
        body_storage: Comment content, Confluence storage-format XHTML
            (e.g. ``"<p>...</p>"``) -- not Markdown, not plain text.
        confirm: Must be ``True`` (or CONFLUENCE_AUTO_CONFIRM_WRITES=true)
            for the comment to actually be posted.

    Returns:
        On success: ``{"confirmed": true, "comment": {...}}``.
        When confirmation is required first: ``{"confirmed": false,
        "requires_confirmation": true, "pending_action": {...}}``.
    """

    def _run() -> Dict[str, Any]:
        key = require_str(str(page_id), "page_id")
        body = require_str(body_storage, "body_storage")
        client = get_client()

        if not confirm and not client.config.auto_confirm_writes:
            return {
                "confirmed": False,
                "requires_confirmation": True,
                "pending_action": {"action": "add_comment", "page_id": key, "body_storage": body},
            }

        comment = client.add_comment(key, body)
        return {"confirmed": True, "comment": comment.to_dict()}

    return run_tool("add_comment", _run)
