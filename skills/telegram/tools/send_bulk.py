"""send_bulk: send the SAME message to a small, explicitly named recipient
list. Write, gated. At most 10 recipients, no wildcard/group/"all"
expansion, no deduplication (so 11 copies of one recipient still refuses).
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

from lib import audit, client as client_lib, guard
from lib.auth import load_config
from tools._common import require_str, resolve_peer_record, run_connected, run_tool


def send_bulk(to: Sequence[object], text: str, confirm: bool = False) -> Dict[str, Any]:
    def _run() -> Dict[str, Any]:
        config = load_config()
        text_val = require_str(text, "text")
        marked_ids = guard.authorize_targets(config, list(to))
        records = {mid: resolve_peer_record(config, mid) for mid in marked_ids}

        masked_text, redactions = guard.redact_outbound(text_val)
        redaction_note = (
            f" ({redactions} secret-shaped substring(s) redacted before this summary)" if redactions else ""
        )
        recipient_desc = ", ".join(
            f"{mid} ({records[mid].get('title')})" if records[mid].get("title") else str(mid) for mid in marked_ids
        )
        summary = (
            f"Send this SAME message to {len(marked_ids)} recipient(s): "
            f"{recipient_desc}{redaction_note}:\n\n{masked_text}"
        )
        pending = guard.gate(
            config,
            tool="send_bulk",
            outbound=True,
            confirm=confirm,
            summary=summary,
            pending_action={"to": marked_ids, "text": masked_text, "redactions": redactions},
        )
        if pending is not None:
            return pending

        results: List[Dict[str, Any]] = []
        for marked_id in marked_ids:
            record = records[marked_id]
            peer = client_lib.input_peer_for(marked_id, record)

            async def _body(client, _peer=peer):
                return await client_lib.send_text(client, _peer, masked_text)

            sent = run_connected(config, _body)
            audit.append_event(
                config.audit_log,
                tool="send_bulk",
                chat_id=marked_id,
                chat_title=record.get("title"),
                message_id=getattr(sent, "id", None),
                counts=None,
                outcome="executed",
            )
            results.append({"chat_id": marked_id, "message_id": getattr(sent, "id", None)})

        return {"confirmed": True, "sent": results, "redactions": redactions}

    return run_tool("send_bulk", _run)
