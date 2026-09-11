"""create_page: create a new Confluence page.

Thin tool: validates input and delegates to the shared ConfluenceClient.
This is a write operation, gated the same way every write tool in this
skill is: refuses to execute without confirm=True unless
CONFLUENCE_AUTO_CONFIRM_WRITES is enabled.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from lib.confluence_client import get_client
from tools._common import require_str, run_tool


def create_page(
    space_key: str,
    title: str,
    body_storage: str,
    parent_id: Optional[str] = None,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Create a new page.

    Args:
        space_key: Destination space key, e.g. ``"ENG"``.
        title: Page title. Must be unique within the space.
        body_storage: Page content as Confluence storage-format XHTML
            (e.g. ``"<p>Hello</p>"``) -- not Markdown, not plain text.
        parent_id: Optional parent page id, to create this as a child
            page instead of a space-root page.
        confirm: Must be ``True`` (or CONFLUENCE_AUTO_CONFIRM_WRITES=true)
            for the page to actually be created.

    Returns:
        On success: ``{"confirmed": true, "page": {...}}``.
        When confirmation is required first: ``{"confirmed": false,
        "requires_confirmation": true, "pending_action": {...}}``.
    """

    def _run() -> Dict[str, Any]:
        key = require_str(space_key, "space_key")
        page_title = require_str(title, "title")
        body = require_str(body_storage, "body_storage")
        client = get_client()

        if not confirm and not client.config.auto_confirm_writes:
            return {
                "confirmed": False,
                "requires_confirmation": True,
                "pending_action": {
                    "action": "create_page",
                    "space_key": key,
                    "title": page_title,
                    "body_storage": body,
                    "parent_id": parent_id,
                },
            }

        created = client.create_page(key, page_title, body, parent_id=parent_id)
        return {"confirmed": True, "page": created.to_dict()}

    return run_tool("create_page", _run)
