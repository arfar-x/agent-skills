"""read_messages: fetch recent messages from one allowlisted chat.

`--no-seen` (default `true`) fetches without ever calling Telegram's
read-acknowledge API -- the other party sees no "seen" marker and the
unread badge is left intact. That is the default specifically so that
ordinary reading is invisible to the other party; turning it off is a
real, observable side effect and is gated exactly like a send (rule 4/9).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from lib import audit, client as client_lib, guard
from lib.auth import load_config
from lib.models import Message
from tools._common import require_int, resolve_peer_record, run_connected, run_tool


def _to_message_dict(chat_id: int, m: Any) -> Dict[str, Any]:
    text, redactions = guard.redact_outbound(getattr(m, "message", None) or "")
    reply_id = None
    reply_to = getattr(m, "reply_to", None)
    if reply_to is not None:
        reply_id = getattr(reply_to, "reply_to_msg_id", None)
    media = getattr(m, "media", None)
    model = Message(
        id=m.id,
        chat_id=chat_id,
        sender_id=getattr(m, "sender_id", None),
        date=m.date.isoformat() if getattr(m, "date", None) else None,
        text=text,
        redactions=redactions,
        has_media=media is not None,
        media_kind=type(media).__name__ if media is not None else None,
        reply_to_msg_id=reply_id,
    )
    return model.to_dict()


def read_messages(
    chat_id: object,
    limit: Optional[object] = None,
    no_seen: bool = True,
    confirm: bool = False,
) -> Dict[str, Any]:
    def _run() -> Dict[str, Any]:
        config = load_config()
        marked_id = guard.authorize_chat(config, chat_id)
        effective_limit = guard.clamp_read_limit(config, limit)
        # Resolved before the confirmation step, same as authorize_chat --
        # an unresolvable peer fails fast rather than after the user says yes.
        record = resolve_peer_record(config, marked_id)
        title = record.get("title")

        seen_clause = (
            "leaving no read receipt for the other party (default)"
            if no_seen
            else "AND mark them as read -- a visible read receipt is sent to the other party"
        )
        summary = (
            f"Read up to {effective_limit} messages from chat {marked_id}"
            f"{f' ({title})' if title else ''}, {seen_clause}."
        )
        pending = guard.gate(
            config,
            tool="read_messages",
            outbound=not no_seen,
            confirm=confirm,
            summary=summary,
            pending_action={"chat_id": marked_id, "limit": effective_limit, "no_seen": no_seen},
        )
        if pending is not None:
            return pending

        peer = client_lib.input_peer_for(marked_id, record)

        async def _body(client):
            fetched = await client_lib.fetch_messages(client, peer, limit=effective_limit)
            if not no_seen and fetched:
                await client_lib.acknowledge_read(client, peer, max_id=fetched[0].id)
            return fetched

        messages = run_connected(config, _body)
        message_dicts: List[Dict[str, Any]] = [_to_message_dict(marked_id, m) for m in messages]
        total_redactions = sum(m["redactions"] for m in message_dicts)

        audit.append_event(
            config.audit_log,
            tool="read_messages",
            chat_id=marked_id,
            chat_title=record.get("title"),
            message_id=(messages[0].id if messages else None),
            counts={"messages": len(message_dicts), "redactions": total_redactions},
            outcome="executed",
        )
        return {
            "confirmed": True,
            "chat_id": marked_id,
            "no_seen": no_seen,
            "messages": message_dicts,
            "redactions": total_redactions,
        }

    return run_tool("read_messages", _run)
