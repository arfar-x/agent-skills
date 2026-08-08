#!/usr/bin/env python3
"""Interactive, human-run, one-time (per TTL) Telegram login.

**This script is not part of the agent's tool surface.** It is never
invoked by `scripts/telegram_tool.py`, never called from any `tools/`
module, and `SKILL.md` explicitly instructs the agent to never run it,
never ask for a phone number/code/2FA password, and never drive this
script on the user's behalf. It refuses outright when stdin is not a real
terminal, which is what actually makes that instruction hold even against
an agent that ignores it.

What it does, in order:

1. Refuses unless `sys.stdin.isatty()` -- no pipe, heredoc, or subprocess
   can drive this.
2. If a previous session file exists, connects with it and revokes it
   server-side (`log_out()`) before anything else, so there is never a
   window with two live authorizations for this skill.
3. Performs an interactive login: phone number, the code Telegram sends
   *to your device*, and a 2FA password if one is set. You type all of
   these yourself, at this terminal.
4. Resolves each id in `TELEGRAM_ALLOWED_CHATS` to its `{kind,
   access_hash, title}` -- the *only* moment this skill ever looks up a
   peer's identity. This requires Telegram to already recognize the
   account as having some relationship to that chat (a prior message, a
   contact, channel membership) -- that is a property of Telegram's own
   API, not a limitation introduced here. If resolution fails for an id,
   this script reports it and continues with the others.
5. Writes the session (`0600`, TTL-stamped) and resolved peers (`0600`,
   beside it) to disk, and prints nothing that reveals the session string.

Run this yourself, from this skill's directory, whenever your session
expires or `TELEGRAM_ALLOWED_CHATS` changes:

    python3 scripts/login.py
"""

from __future__ import annotations

import asyncio
import getpass
import os
import sys

_SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SKILL_ROOT not in sys.path:
    sys.path.insert(0, _SKILL_ROOT)

from lib import auth  # noqa: E402
from lib.client import input_peer_for, new_client  # noqa: E402
from lib.utils import is_service_notifications_peer, resolve_peer_kind  # noqa: E402


def _fail(message: str) -> "None":
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def _entity_title(entity) -> str:
    first = getattr(entity, "first_name", None)
    last = getattr(entity, "last_name", None)
    title = getattr(entity, "title", None)
    if title:
        return title
    name = " ".join(p for p in (first, last) if p)
    return name or getattr(entity, "username", None) or "(no title)"


def _entity_kind_and_hash(entity):
    from telethon.tl.types import Channel, Chat, User

    if isinstance(entity, User):
        return "user", getattr(entity, "access_hash", None)
    if isinstance(entity, Chat):
        return "chat", None
    if isinstance(entity, Channel):
        return "channel", getattr(entity, "access_hash", None)
    return "unknown", getattr(entity, "access_hash", None)


async def _revoke_existing(config) -> None:
    state = auth.load_session_state(config.session_file)
    if state is None:
        return
    print("Existing session found -- revoking it before creating a new one...")
    old_client = new_client(config, state.session_string)
    try:
        await old_client.connect()
        await old_client.log_out()
        print("Previous session revoked.")
    except Exception as exc:  # noqa: BLE001
        print(f"(Could not reach Telegram to revoke the previous session: {exc}. Continuing.)")
    finally:
        try:
            await old_client.disconnect()
        except Exception:  # noqa: BLE001
            pass
    auth.delete_session_state(config.session_file)


async def _interactive_login(config):
    from telethon import TelegramClient
    from telethon.errors import SessionPasswordNeededError
    from telethon.sessions import StringSession

    client = TelegramClient(StringSession(), config.api_id, config.api_hash)
    await client.connect()

    phone = input("Phone number (with country code, e.g. +15551234567): ").strip()
    sent = await client.send_code_request(phone)
    code = input("Code Telegram just sent you: ").strip()
    try:
        await client.sign_in(phone=phone, code=code, phone_code_hash=sent.phone_code_hash)
    except SessionPasswordNeededError:
        password = getpass.getpass("Two-factor password: ")
        await client.sign_in(password=password)

    return client


def main() -> None:
    if not sys.stdin.isatty():
        _fail(
            "stdin is not a real terminal. This script only ever runs "
            "interactively, by a human, at their own keyboard -- it refuses "
            "to be driven by a pipe, heredoc, or another process (including "
            "an agent). If you are a human seeing this in a non-interactive "
            "shell, re-run it directly in a real terminal."
        )

    config = auth.load_config()
    if not config.allowed_chats:
        print(
            "WARNING: TELEGRAM_ALLOWED_CHATS is not set. Login will still "
            "proceed, but no chat will be reachable until it is set and this "
            "script is re-run to resolve it."
        )

    asyncio.run(_run(config))


async def _run(config) -> None:
    await _revoke_existing(config)

    client = await _interactive_login(config)
    try:
        me = await client.get_me()
        print(f"Logged in as {getattr(me, 'first_name', '')} (user_id={me.id}).")

        session_string = client.session.save()
        auth.write_session_state(config.session_file, session_string, config.session_ttl_sec)
        print(
            f"Session saved to {config.session_file} "
            f"(TTL {config.session_ttl_sec}s -- re-run this script after it expires)."
        )

        peers = {}
        failures = []
        for marked_id in sorted(config.allowed_chats):
            if is_service_notifications_peer(marked_id):
                print(f"Skipping {marked_id}: this is Telegram's OTP/service account, never resolved or used.")
                continue
            try:
                entity = await client.get_entity(marked_id)
            except Exception as exc:  # noqa: BLE001
                failures.append(marked_id)
                print(
                    f"Could not resolve chat_id {marked_id}: {exc}. This account "
                    "needs some prior relationship with that chat (a message, "
                    "contact, or channel membership) for Telegram to hand out "
                    "its access_hash -- that's a property of Telegram's API, "
                    "not something this script can work around."
                )
                continue
            kind, access_hash = _entity_kind_and_hash(entity)
            title = _entity_title(entity)
            peers[marked_id] = {"kind": kind, "access_hash": access_hash, "title": title}
            print(f"Resolved chat_id {marked_id}: {kind} {title!r}")

        auth.write_peers(config.peers_file, peers)
        print(f"Peers saved to {config.peers_file} ({len(peers)} resolved).")

        if failures:
            print(f"\n{len(failures)} chat_id(s) could not be resolved: {failures}")
            sys.exit(1)
    finally:
        await client.disconnect()


if __name__ == "__main__":
    main()
