"""allowed_chats: list the configured allowlist. No network call.

This is the closest thing to "browsing chats" this skill offers, and it is
deliberately not that -- it only ever echoes `TELEGRAM_ALLOWED_CHATS`
cross-referenced with the titles `scripts/login.py` cached at login time.
It never calls Telegram, and it never lists anything beyond what is already
present in the allowlist -- see `lib/guard.py`'s module docstring on why no
dialog/chat-enumeration code path exists anywhere in this package.
"""

from __future__ import annotations

from typing import Any, Dict

from lib import audit, auth, guard
from lib.auth import load_config
from lib.utils import is_service_notifications_peer
from tools._common import run_tool


def allowed_chats(confirm: bool = False) -> Dict[str, Any]:
    def _run() -> Dict[str, Any]:
        config = load_config()
        summary = "List the chat_ids currently in TELEGRAM_ALLOWED_CHATS with their cached titles -- no network call."
        pending = guard.gate(
            config, tool="allowed_chats", outbound=False, confirm=confirm, summary=summary, pending_action={}
        )
        if pending is not None:
            return pending

        peers = auth.load_peers(config.peers_file)
        chats = []
        for marked_id in sorted(config.allowed_chats):
            if is_service_notifications_peer(marked_id):
                # Always refused elsewhere, so it's misleading to list it as
                # usable here even though it's technically in the allowlist.
                continue
            record = peers.get(marked_id, {})
            chats.append(
                {
                    "chat_id": marked_id,
                    "title": record.get("title"),
                    "kind": record.get("kind"),
                    "resolved": marked_id in peers,
                }
            )
        audit.append_event(
            config.audit_log,
            tool="allowed_chats",
            chat_id=None,
            chat_title=None,
            message_id=None,
            counts={"chats": len(chats)},
            outcome="executed",
        )
        return {"confirmed": True, "allowed_chats": chats}

    return run_tool("allowed_chats", _run)
