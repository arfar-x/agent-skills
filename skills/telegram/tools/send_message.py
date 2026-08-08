"""send_message: send one message to one allowlisted chat. Write, gated.

Redaction (rule 6) applies to the outgoing text too, not just what's read
back -- the exact text shown in the confirmation summary is the exact text
that gets sent, always computed after redaction, never before.
"""

from __future__ import annotations

from typing import Any, Dict

from lib import audit, client as client_lib, guard
from lib.auth import load_config
from tools._common import require_str, resolve_peer_record, run_connected, run_tool


def send_message(chat_id: object, text: str, confirm: bool = False) -> Dict[str, Any]:
    def _run() -> Dict[str, Any]:
        config = load_config()
        text_val = require_str(text, "text")
        marked_id = guard.authorize_chat(config, chat_id)
        record = resolve_peer_record(config, marked_id)
        title = record.get("title")

        masked_text, redactions = guard.redact_outbound(text_val)
        redaction_note = (
            f" ({redactions} secret-shaped substring(s) redacted before this summary)" if redactions else ""
        )
        summary = (
            f"Send this message to chat {marked_id}{f' ({title})' if title else ''}"
            f"{redaction_note}:\n\n{masked_text}"
        )
        pending = guard.gate(
            config,
            tool="send_message",
            outbound=True,
            confirm=confirm,
            summary=summary,
            pending_action={"chat_id": marked_id, "text": masked_text, "redactions": redactions},
        )
        if pending is not None:
            return pending

        peer = client_lib.input_peer_for(marked_id, record)

        async def _body(client):
            return await client_lib.send_text(client, peer, masked_text)

        sent = run_connected(config, _body)
        audit.append_event(
            config.audit_log,
            tool="send_message",
            chat_id=marked_id,
            chat_title=title,
            message_id=getattr(sent, "id", None),
            counts=None,
            outcome="executed",
        )
        return {
            "confirmed": True,
            "chat_id": marked_id,
            "message_id": getattr(sent, "id", None),
            "redactions": redactions,
        }

    return run_tool("send_message", _run)
