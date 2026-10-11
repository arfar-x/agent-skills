"""create_page: create a new Confluence page.

Thin tool: validates input and delegates to the shared ConfluenceClient.
This is a write operation, gated the same way every write tool in this
skill is: refuses to execute without confirm=True unless
CONFLUENCE_AUTO_CONFIRM_WRITES is enabled.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from lib.confluence_client import get_client
from lib.markdown_storage import render_page
from tools._common import ToolInputError, require_str, run_tool


def create_page(
    space_key: str,
    title: str,
    body_storage: Optional[str] = None,
    parent_id: Optional[str] = None,
    confirm: bool = False,
    body_markdown: Optional[str] = None,
    source_title: Optional[str] = None,
    labels: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Create a new page.

    Args:
        space_key: Destination space key, e.g. ``"ENG"``.
        title: Page title. Must be unique within the space.
        body_storage: Page content as Confluence storage-format XHTML
            (e.g. ``"<p>Hello</p>"``). Pass this or ``body_markdown``.
        body_markdown: Page content as Markdown, rendered to storage
            format by the tool (see ``lib/markdown_storage.py``).
        source_title: With ``body_markdown``, also keep the Markdown on the
            page as a collapsed source block under this title -- what lets
            ``patch_page`` edit the page later.
        labels: Labels to add right after creating the page.
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
        body = _body(body_storage, body_markdown, source_title)
        label_names = [name.strip() for name in labels or [] if name and name.strip()]
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
                    "labels": label_names,
                },
            }

        created = client.create_page(key, page_title, body, parent_id=parent_id)
        result: Dict[str, Any] = {"confirmed": True, "page": created.to_dict()}
        if label_names:
            result["labels"] = client.add_labels(created.id, label_names)
        return result

    return run_tool("create_page", _run)


def _body(body_storage: Optional[str], body_markdown: Optional[str], source_title: Optional[str]) -> str:
    """Exactly one of storage XHTML or Markdown; Markdown is rendered here."""
    has_storage = bool(body_storage and body_storage.strip())
    has_markdown = bool(body_markdown and body_markdown.strip())
    if has_storage == has_markdown:
        raise ToolInputError("Pass exactly one of 'body_storage' or 'body_markdown'.")
    if source_title and not has_markdown:
        raise ToolInputError("'source_title' only applies with 'body_markdown'.")
    if has_markdown:
        return render_page(body_markdown, source_title)
    return body_storage.strip()
