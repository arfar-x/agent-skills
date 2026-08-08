"""logout: revoke the current session server-side and delete it locally.

This is the same revocation `lib/client.py` performs automatically on TTL
expiry, exposed as an explicit action for a user who wants to end the
session early (e.g. before handing the machine to someone else).
"""

from __future__ import annotations

from typing import Any, Dict

from lib import audit, auth, client as client_lib, guard
from lib.auth import load_config
from tools._common import run_connected, run_tool


def logout(confirm: bool = False) -> Dict[str, Any]:
    def _run() -> Dict[str, Any]:
        config = load_config()
        summary = (
            "Revoke the current Telegram session server-side (log_out) and "
            "delete the local session file. A new session will require "
            "running scripts/login.py again, interactively."
        )
        pending = guard.gate(
            config, tool="logout", outbound=False, confirm=confirm, summary=summary, pending_action={}
        )
        if pending is not None:
            return pending

        try:
            run_connected(config, client_lib.do_logout)
        finally:
            # Delete the local blob regardless of whether the server-side
            # log_out succeeded -- an unreachable server is not a reason to
            # keep trusting a credential the user asked to end.
            auth.delete_session_state(config.session_file)

        audit.append_event(
            config.audit_log,
            tool="logout",
            chat_id=None,
            chat_title=None,
            message_id=None,
            counts=None,
            outcome="executed",
        )
        return {"confirmed": True, "logged_out": True}

    return run_tool("logout", _run)
