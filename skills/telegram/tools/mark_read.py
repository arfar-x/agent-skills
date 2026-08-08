"""mark_read: explicitly send a read receipt for an entire chat.

This is the observable-side-effect action `read_messages`'s `--no-seen`
default exists to avoid triggering by accident. Gated with the two-step
(not the `tty` prompt) per this skill's confirmation-mode split -- see
`lib/guard.py`'s `gate()` docstring.
"""

from __future__ import annotations

from typing import Any, Dict

from lib import audit, client as client_lib, guard
from lib.auth import load_config
from tools._common import resolve_peer_record, run_connected, run_tool


def mark_read(chat_id: object, confirm: bool = False) -> Dict[str, Any]:
    def _run() -> Dict[str, Any]:
        config = load_config()
        marked_id = guard.authorize_chat(config, chat_id)
        record = resolve_peer_record(config, marked_id)
        title = record.get("title")
        summary = (
            f"Mark all messages in chat {marked_id}{f' ({title})' if title else ''} as read. "
            "This sends a visible read receipt to the other party."
        )
        pending = guard.gate(
            config,
            tool="mark_read",
            outbound=False,
            confirm=confirm,
            summary=summary,
            pending_action={"chat_id": marked_id},
        )
        if pending is not None:
            return pending

        peer = client_lib.input_peer_for(marked_id, record)

        async def _body(client):
            await client_lib.acknowledge_read(client, peer, max_id=0)

        run_connected(config, _body)
        audit.append_event(
            config.audit_log,
            tool="mark_read",
            chat_id=marked_id,
            chat_title=title,
            message_id=None,
            counts=None,
            outcome="executed",
        )
        return {"confirmed": True, "chat_id": marked_id, "marked_read": True}

    return run_tool("mark_read", _run)
