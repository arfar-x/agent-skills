"""delete_attachment: permanently delete one issue attachment.

Destructive write operation, gated the same way every write tool in this
skill is: refuses to execute without confirm=True unless
JIRA_AUTO_CONFIRM_WRITES is enabled. The attachment is looked up first, so
the pending action shows exactly which file would go and a wrong id fails
before the gate.
"""

from __future__ import annotations

from typing import Any, Dict

from lib.jira_client import get_client
from tools._common import ToolInputError, require_str, run_tool


def delete_attachment(attachment_id: str, confirm: bool = False) -> Dict[str, Any]:
    """Permanently delete an attachment. Cannot be undone.

    Args:
        attachment_id: The attachment's id (from ``get_attachments``).
        confirm: Must be ``True`` (or JIRA_AUTO_CONFIRM_WRITES=true) for the
            deletion to actually execute.

    Returns:
        On success: ``{"confirmed": true, "deleted": true, "attachment": {...}}``
        (the metadata of what was deleted). When confirmation is required
        first: ``{"confirmed": false, "requires_confirmation": true,
        "pending_action": {...}}``.
    """

    def _run() -> Dict[str, Any]:
        att_id = require_str(attachment_id, "attachment_id")
        if not att_id.isdigit():
            raise ToolInputError("'attachment_id' must be numeric (the `id` from get_attachments).")
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
