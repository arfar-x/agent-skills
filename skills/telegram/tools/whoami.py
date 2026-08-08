"""whoami: identify which Telegram account this session belongs to.

Read-only, but gated like every other action in this skill (rule 4: no
exceptions) -- the first call always returns `requires_confirmation`.
"""

from __future__ import annotations

from typing import Any, Dict

from lib import audit, client as client_lib, guard
from lib.auth import load_config
from lib.models import Whoami
from tools._common import run_connected, run_tool


def whoami(confirm: bool = False) -> Dict[str, Any]:
    def _run() -> Dict[str, Any]:
        config = load_config()
        summary = "Report which Telegram account this session is authenticated as (no chat is touched)."
        pending = guard.gate(
            config, tool="whoami", outbound=False, confirm=confirm, summary=summary, pending_action={}
        )
        if pending is not None:
            return pending

        me = run_connected(config, client_lib.whoami)
        result = Whoami(
            user_id=me.id,
            display_name=" ".join(p for p in (me.first_name, me.last_name) if p) or None,
            username=me.username,
            phone_last4=(me.phone[-4:] if getattr(me, "phone", None) else None),
        )
        audit.append_event(
            config.audit_log,
            tool="whoami",
            chat_id=None,
            chat_title=None,
            message_id=None,
            counts=None,
            outcome="executed",
        )
        return {"confirmed": True, "whoami": result.to_dict()}

    return run_tool("whoami", _run)
