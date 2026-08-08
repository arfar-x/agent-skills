"""search_messages: server-side text search scoped to one allowlisted chat.

Same `--no-seen` semantics as `read_messages` (default `true`, no read
receipt sent; turning it off is gated like a send). Read-only otherwise --
this never enumerates chats, it searches within the one chat_id given.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from lib import audit, client as client_lib, guard
from lib.auth import load_config
from tools._common import require_str, resolve_peer_record, run_connected, run_tool
from tools.read_messages import _to_message_dict


def search_messages(
    chat_id: object,
    query: str,
    limit: Optional[object] = None,
    no_seen: bool = True,
    confirm: bool = False,
) -> Dict[str, Any]:
    def _run() -> Dict[str, Any]:
        config = load_config()
        query_val = require_str(query, "query")
        marked_id = guard.authorize_chat(config, chat_id)
        effective_limit = guard.clamp_read_limit(config, limit)
        record = resolve_peer_record(config, marked_id)
        title = record.get("title")

        seen_clause = (
            "leaving no read receipt for the other party (default)"
            if no_seen
            else "AND mark them as read -- a visible read receipt is sent to the other party"
        )
        summary = (
            f"Search chat {marked_id}{f' ({title})' if title else ''} for "
            f"{query_val!r} (up to {effective_limit} results), {seen_clause}."
        )
        pending = guard.gate(
            config,
            tool="search_messages",
            outbound=not no_seen,
            confirm=confirm,
            summary=summary,
            pending_action={
                "chat_id": marked_id,
                "query": query_val,
                "limit": effective_limit,
                "no_seen": no_seen,
            },
        )
        if pending is not None:
            return pending

        peer = client_lib.input_peer_for(marked_id, record)

        async def _body(client):
            fetched = await client_lib.fetch_messages(client, peer, limit=effective_limit, search_text=query_val)
            if not no_seen and fetched:
                await client_lib.acknowledge_read(client, peer, max_id=fetched[0].id)
            return fetched

        messages = run_connected(config, _body)
        message_dicts: List[Dict[str, Any]] = [_to_message_dict(marked_id, m) for m in messages]
        total_redactions = sum(m["redactions"] for m in message_dicts)

        audit.append_event(
            config.audit_log,
            tool="search_messages",
            chat_id=marked_id,
            chat_title=title,
            message_id=(messages[0].id if messages else None),
            counts={"messages": len(message_dicts), "redactions": total_redactions},
            outcome="executed",
        )
        return {
            "confirmed": True,
            "chat_id": marked_id,
            "query": query_val,
            "no_seen": no_seen,
            "messages": message_dicts,
            "redactions": total_redactions,
        }

    return run_tool("search_messages", _run)
