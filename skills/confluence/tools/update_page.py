"""update_page: update an existing page's title and/or content.

Thin tool: validates input and delegates to the shared ConfluenceClient,
which handles fetching the page's current version and incrementing it --
callers never pass a version themselves in the normal case. Write
operation, gated the same way every write tool in this skill is.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from lib.confluence_client import get_client
from lib.markdown_storage import render_page
from tools._common import ToolInputError, require_str, run_tool


def update_page(
    page_id: str,
    title: Optional[str] = None,
    body_storage: Optional[str] = None,
    confirm: bool = False,
    body_markdown: Optional[str] = None,
    source_title: Optional[str] = None,
) -> Dict[str, Any]:
    """Update a page's title and/or content.

    Args:
        page_id: Target page id.
        title: New title (omit to leave unchanged).
        body_storage: New content, Confluence storage-format XHTML (omit
            to leave unchanged). Replaces the entire body; for a partial
            edit of a page with a Markdown source block, use
            ``patch_page`` instead.
        body_markdown: New content as Markdown, rendered by the tool.
            Mutually exclusive with ``body_storage``.
        source_title: With ``body_markdown``, keep the Markdown on the page
            as a collapsed source block under this title.
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
        if body_storage is not None and body_markdown is not None:
            raise ToolInputError("Pass at most one of 'body_storage' or 'body_markdown'.")
        if source_title and body_markdown is None:
            raise ToolInputError("'source_title' only applies with 'body_markdown'.")
        if title is None and body_storage is None and body_markdown is None:
            raise ToolInputError("At least one of title/body_storage/body_markdown must be provided.")
        body = render_page(body_markdown, source_title) if body_markdown is not None else body_storage
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
                    "body_markdown": body_markdown,
                    "source_title": source_title,
                },
            }

        updated = client.update_page(key, title=title, body_storage=body)
        return {"confirmed": True, "page": updated.to_dict()}

    return run_tool("update_page", _run)
