"""forward_message: forward one message between two allowlisted chats.

Write, gated. Both the source and destination chat must individually pass
`guard.authorize_chat` -- including the OTP-chat and allowlist checks --
there is no partial trust from one side of a forward to the other.
"""

from __future__ import annotations

from typing import Any, Dict

from lib import audit, client as client_lib, guard
from lib.auth import load_config
from tools._common import require_int, resolve_peer_record, run_connected, run_tool


def forward_message(
    from_chat_id: object, message_id: object, to_chat_id: object, confirm: bool = False
) -> Dict[str, Any]:
    def _run() -> Dict[str, Any]:
        config = load_config()
        message_id_val = require_int(message_id, "message_id")
        from_id = guard.authorize_chat(config, from_chat_id)
        to_id = guard.authorize_chat(config, to_chat_id)
        from_record = resolve_peer_record(config, from_id)
        to_record = resolve_peer_record(config, to_id)
        from_title = from_record.get("title")
        to_title = to_record.get("title")

        summary = (
            f"Forward message {message_id_val} from chat {from_id}"
            f"{f' ({from_title})' if from_title else ''} to chat {to_id}"
            f"{f' ({to_title})' if to_title else ''}."
        )
        pending = guard.gate(
            config,
            tool="forward_message",
            outbound=True,
            confirm=confirm,
            summary=summary,
            pending_action={"from_chat_id": from_id, "to_chat_id": to_id, "message_id": message_id_val},
        )
        if pending is not None:
            return pending

        from_peer = client_lib.input_peer_for(from_id, from_record)
        to_peer = client_lib.input_peer_for(to_id, to_record)

        async def _body(client):
            return await client_lib.forward_one(client, from_peer=from_peer, to_peer=to_peer, message_id=message_id_val)

        result = run_connected(config, _body)
        forwarded_id = getattr(result, "id", None)
        audit.append_event(
            config.audit_log,
            tool="forward_message",
            chat_id=to_id,
            chat_title=to_title,
            message_id=forwarded_id,
            counts=None,
            outcome="executed",
        )
        return {
            "confirmed": True,
            "from_chat_id": from_id,
            "to_chat_id": to_id,
            "forwarded_message_id": forwarded_id,
        }

    return run_tool("forward_message", _run)
