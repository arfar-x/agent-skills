"""add_label: add a label to a page.

Thin tool: delegates to the shared ConfluenceClient. Write operation,
gated the same way every write tool in this skill is.
"""

from __future__ import annotations

from typing import Any, Dict

from lib.confluence_client import get_client
from tools._common import require_str, run_tool


def add_label(page_id: str, label: str, confirm: bool = False) -> Dict[str, Any]:
    """Add a label to a page.

    Args:
        page_id: Target page id.
        label: Label name to add, e.g. ``"onboarding"``.
        confirm: Must be ``True`` (or CONFLUENCE_AUTO_CONFIRM_WRITES=true)
            for the label to actually be added.

    Returns:
        On success: ``{"confirmed": true, "page_id": "...", "labels": [...]}``
        (the page's full label list after adding).
        When confirmation is required first: ``{"confirmed": false,
        "requires_confirmation": true, "pending_action": {...}}``.
    """

    def _run() -> Dict[str, Any]:
        key = require_str(str(page_id), "page_id")
        label_name = require_str(label, "label")
        client = get_client()

        if not confirm and not client.config.auto_confirm_writes:
            return {
                "confirmed": False,
                "requires_confirmation": True,
                "pending_action": {"action": "add_label", "page_id": key, "label": label_name},
            }

        labels = client.add_label(key, label_name)
        return {"confirmed": True, "page_id": key, "labels": labels}

    return run_tool("add_label", _run)
