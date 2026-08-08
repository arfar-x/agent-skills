"""Shared plumbing for tool entry points (not itself a tool).

Mirrors `skills/jira/tools/_common.py`'s `run_tool`/`ToolInputError`
pattern (errors-to-JSON at the tool boundary, never a raw traceback to the
model), plus this skill's own peer-resolution and connected-client helpers
that every chat-scoped tool routes through.
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Dict, Optional, TypeVar

from lib import audit, client as client_lib, guard
from lib.auth import ConfigurationError, SessionSecurityError, load_config
from lib.client import NoSessionError, SessionExpiredError

logger = logging.getLogger("telegram_skill.tools")

T = TypeVar("T")


class ToolInputError(ValueError):
    """Raised by tools when caller-supplied arguments are invalid."""


def run_tool(tool_name: str, fn: Callable[[], Any]) -> Any:
    """Execute a tool body, normalizing every error into structured JSON.

    A guard refusal (`guard.GuardError`) is reported the same way as any
    other handled error -- it is the expected, designed-for outcome of a
    caller (agent or otherwise) attempting something this skill forbids,
    not a bug.
    """
    try:
        result = fn()
        logger.info("Tool %s succeeded", tool_name)
        return result
    except ToolInputError as exc:
        logger.warning("Tool %s rejected invalid input: %s", tool_name, exc)
        return {"error": {"type": "invalid_input", "message": str(exc)}}
    except guard.GuardError as exc:
        logger.warning("Tool %s refused (%s): %s", tool_name, exc.kind, exc)
        return {"error": {"type": f"guard_{exc.kind}", "message": str(exc)}}
    except ConfigurationError as exc:
        logger.error("Tool %s misconfigured: %s", tool_name, exc)
        return {"error": {"type": "configuration_error", "message": str(exc)}}
    except SessionSecurityError as exc:
        logger.error("Tool %s session security check failed: %s", tool_name, exc)
        return {"error": {"type": "session_security_error", "message": str(exc)}}
    except NoSessionError as exc:
        logger.warning("Tool %s has no session: %s", tool_name, exc)
        return {"error": {"type": "no_session", "message": str(exc)}}
    except SessionExpiredError as exc:
        logger.warning("Tool %s session expired: %s", tool_name, exc)
        return {"error": {"type": "session_expired", "message": str(exc)}}
    except Exception as exc:  # noqa: BLE001 - last-resort safety net for a tool boundary
        logger.exception("Tool %s failed unexpectedly", tool_name)
        return {"error": {"type": "internal_error", "message": str(exc)}}


def require_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ToolInputError(f"'{field_name}' is required and must be a non-empty string.")
    return value.strip()


def require_int(value: Any, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ToolInputError(f"'{field_name}' must be an integer, got {value!r}.") from exc


def resolve_peer_record(config, marked_id: int) -> Dict[str, Any]:
    """Look up an allowlisted chat's cached `{kind, access_hash, title}`.

    Raises `guard.GuardError` (not a lower-level exception) if the id is
    allowlisted but was never resolved at login time -- this is a "re-run
    login.py" situation, not an internal error.
    """
    from lib import auth

    peers = auth.load_peers(config.peers_file)
    record = peers.get(marked_id)
    if record is None:
        raise guard.GuardError(
            "peer_not_resolved",
            f"chat_id {marked_id} is present in TELEGRAM_ALLOWED_CHATS but has "
            "no cached entry in peers.json. Re-run scripts/login.py so it can "
            "be resolved -- this skill never resolves a peer at any other time.",
        )
    return record


def peer_title(config, marked_id: int) -> Optional[str]:
    from lib import auth

    peers = auth.load_peers(config.peers_file)
    record = peers.get(marked_id)
    return record.get("title") if record else None


def run_connected(config, body: Callable[[Any], Awaitable[T]]) -> T:
    """Connect (enforcing TTL expiry), run one async body, always disconnect."""

    async def _wrapped() -> T:
        conn = await client_lib.ensure_live_session(config)
        try:
            return await body(conn)
        finally:
            await conn.disconnect()

    return client_lib.run_sync(_wrapped())
