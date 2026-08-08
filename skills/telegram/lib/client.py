"""The single Telethon wrapper. Every actual Telegram API call in this
skill goes through this module, and nowhere else.

Structural guards live here too, not just in `lib/guard.py`:

- ``receive_updates=False`` -- no update loop, no incoming-event stream.
  Every action in this skill is a one-shot request/response, never a
  listener, so there is nothing ambient running between calls.
- ``entity_cache_limit=0`` -- no in-memory peer directory accumulates from
  ordinary use, on top of never populating one via enumeration.
- **No dialog/chat-enumeration method appears anywhere in this file.**
  ``get_dialogs``, ``iter_dialogs``, and every equivalent are not gated,
  they are simply never called -- `tests/` asserts this by grepping the
  whole package, not by testing a guard around them.

Peer addressing never triggers a lookup: `input_peer_for()` reconstructs a
Telethon ``InputPeer*`` object directly from the ``{kind, access_hash}``
`scripts/login.py` cached at login time. This was validated against a real
installed Telethon (1.44.0) before anything else in this skill was built --
`get_input_entity` short-circuits on an already-``InputPeer`` argument with
zero cache lookup and zero network call, confirmed by reading
`telethon/client/users.py` directly. See the plan's "top implementation
risk" section.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, TypeVar

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import InputPeerChannel, InputPeerChat, InputPeerUser

from . import auth
from .auth import SessionSecurityError, TelegramConfig
from .utils import resolve_peer_kind

T = TypeVar("T")


class SessionExpiredError(RuntimeError):
    """The session TTL elapsed (or Telegram itself revoked it). Re-run login.py."""


class NoSessionError(RuntimeError):
    """No session file exists yet. Run login.py."""


def input_peer_for(marked_id: int, peer_record: Dict[str, Any]):
    """Reconstruct an ``InputPeer*`` from a stored peers.json record.

    Zero cache lookup, zero network call -- this is the whole point of
    caching ``access_hash`` at login time instead of enumerating dialogs at
    runtime.
    """
    kind, bare_id = resolve_peer_kind(marked_id)
    if kind == "chat":
        return InputPeerChat(bare_id)
    access_hash = peer_record.get("access_hash")
    if access_hash is None:
        raise SessionSecurityError(
            f"No access_hash cached for {kind} peer {marked_id}. Re-run "
            "scripts/login.py to (re)resolve TELEGRAM_ALLOWED_CHATS."
        )
    if kind == "user":
        return InputPeerUser(bare_id, access_hash)
    return InputPeerChannel(bare_id, access_hash)


def new_client(config: TelegramConfig, session_string: str) -> TelegramClient:
    return TelegramClient(
        StringSession(session_string),
        config.api_id,
        config.api_hash,
        receive_updates=False,
        entity_cache_limit=0,
    )


async def ensure_live_session(config: TelegramConfig) -> TelegramClient:
    """Load the session blob, enforce TTL, connect, and return a live client.

    On expiry: connects once for the sole purpose of ``log_out()`` (which
    revokes the authorization server-side), deletes the local blob, and
    raises ``SessionExpiredError``. No other Telegram API call is ever made
    on an expired blob -- this function either returns a freshly verified
    live client, or raises before any message/chat operation is possible.
    """
    state = auth.load_session_state(config.session_file)
    if state is None:
        raise NoSessionError(
            "No Telegram session found. Run scripts/login.py yourself, "
            "interactively, to create one -- the agent must never do this "
            "on your behalf; see SKILL.md rule 2."
        )

    if auth.is_expired(state, config):
        revoke_client = new_client(config, state.session_string)
        try:
            await revoke_client.connect()
            await revoke_client.log_out()
        except Exception:
            # Best-effort: even if server-side revocation fails (e.g. no
            # network right now), the local blob is deleted below regardless,
            # so nothing locally trusts an expired credential again.
            pass
        finally:
            try:
                await revoke_client.disconnect()
            except Exception:
                pass
        auth.delete_session_state(config.session_file)
        raise SessionExpiredError(
            f"Session exceeded its TTL ({config.session_ttl_sec}s) and has "
            "been revoked. Run scripts/login.py yourself to create a new one."
        )

    client = new_client(config, state.session_string)
    await client.connect()
    if not await client.is_user_authorized():
        auth.delete_session_state(config.session_file)
        await client.disconnect()
        raise SessionExpiredError(
            "The stored session is no longer authorized (revoked from "
            "another device, or invalidated by Telegram). Run "
            "scripts/login.py yourself to create a new one."
        )
    return client


def run_sync(coro: Awaitable[T]) -> T:
    """Run one async client operation from the synchronous tool layer."""
    return asyncio.run(coro)


# --------------------------------------------------------------------------
# Thin, explicit wrappers around each Telegram operation this skill uses.
#
# Kept one function per operation (rather than one do-everything method) so
# that "no read-acknowledge happens unless explicitly requested" is visible
# structurally: fetch_messages() never calls acknowledge_read(), and no
# other function in this file does either, except mark_read's own path.
# --------------------------------------------------------------------------


async def whoami(client: TelegramClient):
    return await client.get_me()


async def do_logout(client: TelegramClient) -> None:
    await client.log_out()


async def fetch_messages(client: TelegramClient, peer, *, limit: int, search_text: Optional[str] = None) -> List[Any]:
    """Fetch messages. Never acknowledges them as read -- see module docstring."""
    kwargs: Dict[str, Any] = {"limit": limit}
    if search_text is not None:
        kwargs["search"] = search_text
    result = await client.get_messages(peer, **kwargs)
    return list(result)


async def acknowledge_read(client: TelegramClient, peer, *, max_id: int) -> None:
    """Explicitly mark a chat read up to ``max_id``. Only ever called from
    the `mark_read` tool, or from `read_messages`/`search_messages` after
    `--no-seen false` has separately passed the outbound confirmation gate.
    """
    await client.send_read_acknowledge(peer, max_id=max_id)


async def send_text(client: TelegramClient, peer, text: str):
    return await client.send_message(peer, text)


async def forward_one(client: TelegramClient, *, from_peer, to_peer, message_id: int):
    result = await client.forward_messages(to_peer, message_id, from_peer)
    return result[0] if isinstance(result, (list, tuple)) else result


async def get_one_message(client: TelegramClient, peer, message_id: int):
    return await client.get_messages(peer, ids=message_id)


async def download_to(client: TelegramClient, message, out_path: Path) -> Optional[str]:
    return await client.download_media(message, file=str(out_path))
