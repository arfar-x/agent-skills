"""delete_page: permanently delete a page.

Thin tool: delegates to the shared ConfluenceClient. Destructive write
operation -- cannot be undone -- gated the same way every write tool in
this skill is.
"""

from __future__ import annotations

from typing import Any, Dict

from lib.confluence_client import get_client
from tools._common import require_str, run_tool


def delete_page(page_id: str, confirm: bool = False) -> Dict[str, Any]:
    """Permanently delete a page.

    Args:
        page_id: Target page id.
        confirm: Must be ``True`` (or CONFLUENCE_AUTO_CONFIRM_WRITES=true)
            for the page to actually be deleted. This cannot be undone --
            make sure the user has explicitly confirmed which page before
            setting this.

    Returns:
        On success: ``{"confirmed": true, "page_id": "...", "deleted": true}``.
        When confirmation is required first: ``{"confirmed": false,
        "requires_confirmation": true, "pending_action": {...}}``.
    """

    def _run() -> Dict[str, Any]:
        key = require_str(str(page_id), "page_id")
        client = get_client()

        if not confirm and not client.config.auto_confirm_writes:
            return {
                "confirmed": False,
                "requires_confirmation": True,
                "pending_action": {"action": "delete_page", "page_id": key},
            }

        client.delete_page(key)
        return {"confirmed": True, "page_id": key, "deleted": True}

    return run_tool("delete_page", _run)
