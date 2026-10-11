"""delete_attachment: permanently delete one page attachment.

Destructive write operation, gated the same way every write tool in this
skill is: refuses to execute without confirm=True unless
CONFLUENCE_AUTO_CONFIRM_WRITES is enabled. The attachment is looked up
first (and must really be an attachment, never a page), so the pending
action shows exactly which file would go and a wrong id fails before the
gate.
"""

from __future__ import annotations

from typing import Any, Dict

from lib.confluence_client import get_client
from tools._common import require_str, run_tool


def delete_attachment(attachment_id: str, confirm: bool = False) -> Dict[str, Any]:
    """Permanently delete an attachment, with all of its versions.

    Args:
        attachment_id: The attachment's content id (from ``get_attachments``).
        confirm: Must be ``True`` (or CONFLUENCE_AUTO_CONFIRM_WRITES=true)
            for the deletion to actually execute.

    Returns:
        On success: ``{"confirmed": true, "deleted": true, "attachment": {...}}``
        (the metadata of what was deleted, including the page it was on).
        When confirmation is required first: ``{"confirmed": false,
        "requires_confirmation": true, "pending_action": {...}}``.
    """

    def _run() -> Dict[str, Any]:
        att_id = require_str(attachment_id, "attachment_id")
        client = get_client()
        info = client.get_attachment_info(att_id)

        if not confirm and not client.config.auto_confirm_writes:
            return {
                "confirmed": False,
                "requires_confirmation": True,
                "pending_action": {"action": "delete_attachment", "attachment": info},
            }
        client.delete_attachment(att_id)
        return {"confirmed": True, "deleted": True, "attachment": info}

    return run_tool("delete_attachment", _run)
