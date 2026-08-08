"""Small stateless helpers shared across the Telegram guard, auth, and tools.

Nothing in this module imports Telethon -- it stays pure Python so the
policy logic that depends on it (`lib/guard.py`) is unit-testable without a
real Telegram connection, per this skill's test plan.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional, Tuple

# --------------------------------------------------------------------------
# Chat id normalization
# --------------------------------------------------------------------------
#
# Telethon's own "marked id" scheme is the canonical form used everywhere in
# this skill (config, allowlist, peers.json, CLI args): a plain positive
# integer for a user, a plain negative integer for a basic group, and
# ``-1000000000000 - channel_id`` for a channel/supergroup. Every chat_id a
# caller can reasonably copy out of a Telegram client or a `whoami`/
# `read_messages` result is already in this form, so no separate "friendly"
# format is supported -- accepting one would mean looking a name/username up
# to resolve it, which this skill deliberately never does (no enumeration).

_CHANNEL_MARK_OFFSET = 1_000_000_000_000

# Telegram's official "Telegram" service-notifications account, which
# delivers login codes and account-recovery messages. See guard.py rule 3.
SERVICE_NOTIFICATIONS_USER_ID = 777000

_CHAT_ID_RE = re.compile(r"^(?P<sign>[+-])?0*(?P<digits>\d+)$")


class InvalidChatIdError(ValueError):
    """Raised when a caller-supplied chat_id string isn't a bare integer.

    Deliberately rejects anything that looks like a username, invite link,
    phone number, or display name -- accepting those would require a chat
    lookup, which this skill's "no enumeration" guarantee forbids.
    """


def normalize_chat_id(raw: object) -> int:
    """Parse a caller-supplied chat_id into its canonical marked-id integer.

    Accepts a bare (optionally signed, optionally zero-padded, optionally
    whitespace-padded) integer only -- ``"777000"``, ``" 777000 "``,
    ``"+777000"``, ``"0777000"``, ``-777000`` (already an int) all parse.
    Anything else (a ``@username``, a ``t.me/...`` link, a phone number, a
    display name, or an unparseable value from a spoofed argv) raises
    ``InvalidChatIdError``.
    """
    if isinstance(raw, int) and not isinstance(raw, bool):
        return raw
    if not isinstance(raw, str):
        raise InvalidChatIdError(
            f"chat_id must be a numeric id, got {type(raw).__name__}: {raw!r}"
        )
    match = _CHAT_ID_RE.match(raw.strip())
    if not match:
        raise InvalidChatIdError(
            f"{raw!r} is not a numeric chat_id. Usernames, invite links, phone "
            "numbers, and display names are never accepted -- this skill does "
            "not look chats up, it only ever addresses a chat_id already "
            "present in TELEGRAM_ALLOWED_CHATS."
        )
    value = int(match.group("digits"))
    if match.group("sign") == "-":
        value = -value
    return value


def resolve_peer_kind(marked_id: int) -> Tuple[str, int]:
    """Return ``(kind, bare_id)`` for a canonical marked chat id.

    ``kind`` is one of ``"user"``, ``"chat"`` (basic group), or ``"channel"``
    (channel/supergroup). ``bare_id`` is the id Telethon's ``InputPeer*``
    constructors expect.
    """
    if marked_id > 0:
        return "user", marked_id
    if marked_id <= -_CHANNEL_MARK_OFFSET:
        return "channel", -marked_id - _CHANNEL_MARK_OFFSET
    return "chat", -marked_id


def is_service_notifications_peer(marked_id: int) -> bool:
    """True if ``marked_id`` denotes (or plausibly spoofs) the OTP account.

    The canonical form is the bare positive user id ``777000``. This also
    refuses by numeric magnitude (``abs(marked_id) == 777000``) as
    defense-in-depth against sign/prefix spoofing -- e.g. a caller passing
    ``-777000`` technically addresses a different (and essentially
    nonexistent) basic-group id under Telethon's marking scheme, but a
    caller typing that is far more likely probing the denylist than
    addressing a real distinct chat, so it is refused too rather than let
    through on a technicality.
    """
    if abs(marked_id) == SERVICE_NOTIFICATIONS_USER_ID:
        return True
    kind, bare_id = resolve_peer_kind(marked_id)
    return kind == "channel" and bare_id == SERVICE_NOTIFICATIONS_USER_ID


# --------------------------------------------------------------------------
# Filesystem safety
# --------------------------------------------------------------------------


def is_inside_git_worktree(path: "os.PathLike[str] | str") -> bool:
    """True if ``path`` sits inside any git working tree, anywhere.

    Deliberately general (not scoped to this repo) -- session/audit files
    and download output must never land inside *any* git-tracked directory,
    since anything written there risks being committed and pushed. A
    worktree's ``.git`` is a file, not a directory, so this checks for
    either.
    """
    current = Path(path).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return True
    return False


_UNSAFE_FILENAME_EXTENSIONS = {
    ".sh", ".bash", ".zsh", ".py", ".pyc", ".exe", ".bat", ".cmd", ".com",
    ".scr", ".ps1", ".psm1", ".jar", ".msi", ".dll", ".so", ".command",
    ".app", ".desktop", ".vbs", ".js", ".apk", ".deb", ".rpm",
}


class UnsafeFilenameError(ValueError):
    """Raised when a downloaded file's name can't be made safe to write."""


def sanitize_download_filename(name: str) -> str:
    """Reduce a Telegram-supplied filename to a safe basename, or refuse.

    Strips any directory component (defeats path traversal via
    ``../../..``), refuses a name that is empty, is a hidden/dotfile, or
    carries an executable/script extension -- downloaded media is never
    meant to be run, and Telegram-supplied names are untrusted input.
    """
    base = os.path.basename((name or "").strip())
    if not base or base in (".", ".."):
        raise UnsafeFilenameError("Empty or unusable filename from Telegram.")
    if base.startswith("."):
        raise UnsafeFilenameError(f"Refusing a hidden/dotfile name: {base!r}")
    suffix = Path(base).suffix.lower()
    if suffix in _UNSAFE_FILENAME_EXTENSIONS:
        raise UnsafeFilenameError(
            f"Refusing to write a file with extension {suffix!r} ({base!r}) -- "
            "downloaded media is never executed, and this extension is "
            "treated as inherently unsafe to have on disk under this name."
        )
    return base


# --------------------------------------------------------------------------
# Redaction
# --------------------------------------------------------------------------
#
# Regex-based, best-effort. This is documented in skills/telegram/README.md
# as defense-in-depth, not a guarantee -- it will not catch a code split
# across lines, padded with zero-width characters, or written in non-ASCII
# digits. Tests pin these known misses so the limitation stays visible.

_CODE_WORDS = (
    r"code|login|log-in|otp|verification|verify|pin|password|passcode|"
    r"رمز|کد|كود"  # "رمز"/"کد"/"كود"
)
_OTP_NEAR_RE = re.compile(
    rf"(?:(?:{_CODE_WORDS})\D{{0,12}}(?P<code1>\d{{4,8}})|"
    rf"(?P<code2>\d{{4,8}})\D{{0,12}}(?:{_CODE_WORDS}))",
    re.IGNORECASE,
)

_TOKEN_RE = re.compile(
    r"\bsk-[A-Za-z0-9]{10,}\b"
    r"|\bBearer\s+[A-Za-z0-9\-_.]{10,}\b"
    r"|\b[a-fA-F0-9]{32,}\b"
    r"|\b(?=[A-Za-z0-9+/]{24,}\b)(?=[A-Za-z]*\d)(?=\d*[A-Za-z])[A-Za-z0-9+/]{24,}={0,2}\b"
)

_LOGIN_LINK_RE = re.compile(r"\bt\.me/login/\S+", re.IGNORECASE)


def redact(text: Optional[str]) -> Tuple[str, int]:
    """Mask OTP-shaped codes, token-shaped strings, and Telegram login links.

    Returns ``(masked_text, redactions_count)``. Callers must surface a
    nonzero count to the user rather than presenting the masked text as
    complete -- see `SKILL.md` rule 6.
    """
    if not text:
        return text or "", 0

    count = 0

    def _otp_sub(match: "re.Match[str]") -> str:
        nonlocal count
        count += 1
        return match.group(0).replace(
            match.group("code1") or match.group("code2"), "[REDACTED:otp]"
        )

    masked = _OTP_NEAR_RE.sub(_otp_sub, text)

    def _generic_sub(pattern: "re.Pattern[str]", label: str, value: str) -> str:
        nonlocal count

        def _sub(match: "re.Match[str]") -> str:
            nonlocal count
            count += 1
            return f"[REDACTED:{label}]"

        return pattern.sub(_sub, value)

    masked = _generic_sub(_TOKEN_RE, "token", masked)
    masked = _generic_sub(_LOGIN_LINK_RE, "token", masked)

    return masked, count
