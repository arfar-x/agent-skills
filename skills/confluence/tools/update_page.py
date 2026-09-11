"""update_page: update an existing page's title and/or content.

Thin tool: validates input and delegates to the shared ConfluenceClient,
which handles fetching the page's current version and incrementing it --
callers never pass a version themselves in the normal case. Write
operation, gated the same way every write tool in this skill is.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from lib.confluence_client import get_client
from tools._common import ToolInputError, require_str, run_tool


def update_page(
    page_id: str,
    title: Optional[str] = None,
    body_storage: Optional[str] = None,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Update a page's title and/or content.

    Args:
        page_id: Target page id.
        title: New title (omit to leave unchanged).
        body_storage: New content, Confluence storage-format XHTML (omit
            to leave unchanged). Replaces the entire body -- there is no
            partial/append update.
        confirm: Must be ``True`` (or CONFLUENCE_AUTO_CONFIRM_WRITES=true)
            for the update to actually be submitted.

    Returns:
        On success: ``{"confirmed": true, "page": {...}}``.
        When confirmation is required first: ``{"confirmed": false,
        "requires_confirmation": true, "pending_action": {...}}``.
        If the page was edited since it was last read, Confluence rejects
        the write with a 409 (surfaced as
        ``{"error": {"type": "ConfluenceValidationError", ...}}``) --
        re-fetch the page and show the user what changed rather than
        blindly retrying.
    """

    def _run() -> Dict[str, Any]:
        key = require_str(str(page_id), "page_id")
        if title is None and body_storage is None:
            raise ToolInputError("At least one of title/body_storage must be provided.")
        client = get_client()

        if not confirm and not client.config.auto_confirm_writes:
            return {
                "confirmed": False,
                "requires_confirmation": True,
                "pending_action": {
                    "action": "update_page",
                    "page_id": key,
                    "title": title,
                    "body_storage": body_storage,
                },
            }

        updated = client.update_page(key, title=title, body_storage=body_storage)
        return {"confirmed": True, "page": updated.to_dict()}

    return run_tool("update_page", _run)
