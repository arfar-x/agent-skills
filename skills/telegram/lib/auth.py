"""Environment configuration and session-file handling for the Telegram skill.

Credentials are sourced from environment variables (`TELEGRAM_API_ID`,
`TELEGRAM_API_HASH`), same as every other toolset in this repo -- but the
live session credential itself is deliberately **not** an env var: it lives
in a `0600` file outside the repo, rotated on a TTL by `scripts/login.py`.
See `skills/telegram/README.md`'s "Session storage" section for why this is
a documented, deliberate deviation from this repo's usual
credentials-only-from-env-vars convention.
"""

from __future__ import annotations

import json
import os
import stat
import time
from dataclasses import dataclass
from pathlib import Path
from typing import FrozenSet, Mapping, Optional

from .utils import InvalidChatIdError, is_inside_git_worktree, normalize_chat_id

_APP_DIR_NAME = "agent-skills-telegram"
_DEFAULT_TTL_SEC = 86400
_DEFAULT_MAX_READ_LIMIT = 200
_CLOCK_SKEW_TOLERANCE_SEC = 60


class ConfigurationError(RuntimeError):
    """Raised when the skill is misconfigured (missing/invalid env vars)."""


class SessionSecurityError(RuntimeError):
    """Raised when the on-disk session/peers file fails a safety check.

    Covers both configuration mistakes (a session path inside a git work
    tree) and active forgery attempts (loose file permissions, a
    `created_at` timestamp in the future). Either way the correct response
    is the same: refuse and say why, never silently proceed.
    """


@dataclass(frozen=True)
class TelegramConfig:
    api_id: int
    api_hash: str
    allowed_chats: FrozenSet[int]
    session_file: Path
    peers_file: Path
    audit_log: Path
    session_ttl_sec: int = _DEFAULT_TTL_SEC
    confirm_mode: str = "tty"  # "tty" | "flag"
    download_dir: Optional[Path] = None
    max_read_limit: int = _DEFAULT_MAX_READ_LIMIT

    def auth_summary(self) -> str:
        """Redacted, human-readable description -- never the credential itself."""
        return (
            f"Telethon user session (api_id={self.api_id}, "
            f"confirm_mode={self.confirm_mode}, ttl={self.session_ttl_sec}s)"
        )


def _env(source: Mapping[str, str], name: str) -> Optional[str]:
    value = source.get(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _env_int(source: Mapping[str, str], name: str, default: int) -> int:
    raw = _env(source, name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name}={raw!r} is not a valid integer.") from exc
    if value <= 0:
        raise ConfigurationError(f"{name}={raw!r} must be a positive integer.")
    return value


def _runtime_base_dir() -> Path:
    xdg = _env(os.environ, "XDG_RUNTIME_DIR")
    if xdg:
        return Path(xdg) / _APP_DIR_NAME
    uid = getattr(os, "getuid", lambda: 0)()
    return Path(f"/tmp/{_APP_DIR_NAME}-{uid}")


def _resolve_paths(source: Mapping[str, str]) -> tuple[Path, Path, Path]:
    """Resolve (session_file, peers_file, audit_log), per README's order.

    1. `TELEGRAM_SESSION_FILE`, if set -- `peers.json`/`audit.log` live
       beside it.
    2. `$XDG_RUNTIME_DIR/agent-skills-telegram/` (preferred: tmpfs, `0700`,
       per-user, wiped on logout).
    3. `/tmp/agent-skills-telegram-$UID/` when `XDG_RUNTIME_DIR` is unset.
    """
    explicit = _env(source, "TELEGRAM_SESSION_FILE")
    if explicit:
        session_file = Path(explicit)
        base_dir = session_file.parent
    else:
        base_dir = _runtime_base_dir()
        session_file = base_dir / "session.json"

    peers_file = base_dir / "peers.json"

    audit_override = _env(source, "TELEGRAM_AUDIT_LOG")
    audit_log = Path(audit_override) if audit_override else base_dir / "audit.log"

    for path, label in ((session_file, "session file"), (peers_file, "peers file"), (audit_log, "audit log")):
        if is_inside_git_worktree(path.parent if not path.exists() else path):
            raise SessionSecurityError(
                f"Refusing to use a {label} path inside a git work tree: {path}. "
                "This repo (and any git checkout) is not a safe place for a live "
                "Telegram session credential -- set TELEGRAM_SESSION_FILE to a "
                "path outside any repository."
            )

    return session_file, peers_file, audit_log


def load_config(env: Optional[Mapping[str, str]] = None) -> TelegramConfig:
    """Load and validate configuration from environment variables.

    Raises:
        ConfigurationError: missing/invalid required variables. Message
            names exactly what's wrong.
        SessionSecurityError: a resolved path is unsafe (inside a git work
            tree).

    Environment variables:
        TELEGRAM_API_ID / TELEGRAM_API_HASH (required): from my.telegram.org.
        TELEGRAM_ALLOWED_CHATS (required): comma-separated numeric chat_ids.
            Unset or empty means this toolset does nothing at all -- every
            tool refuses. This is deliberate; see guard.py rule 2.
        TELEGRAM_SESSION_TTL_SEC (optional, default 86400): absolute session
            lifetime in seconds.
        TELEGRAM_SESSION_FILE (optional): explicit session path override.
        TELEGRAM_CONFIRM_MODE (optional, default "tty"): "tty" or "flag".
        TELEGRAM_AUDIT_LOG (optional): explicit audit log path override.
        TELEGRAM_DOWNLOAD_DIR (optional): default `download_media` output dir.
        TELEGRAM_MAX_READ_LIMIT (optional, default 200): may only lower the
            hard ceiling, never raise it.
    """
    source: Mapping[str, str] = env if env is not None else os.environ

    api_id_raw = _env(source, "TELEGRAM_API_ID")
    api_hash = _env(source, "TELEGRAM_API_HASH")
    missing = [name for name, value in (("TELEGRAM_API_ID", api_id_raw), ("TELEGRAM_API_HASH", api_hash)) if not value]
    if missing:
        raise ConfigurationError(
            f"The following environment variables are missing: {', '.join(missing)}. "
            "Get them from https://my.telegram.org."
        )
    try:
        api_id = int(api_id_raw)  # type: ignore[arg-type]
    except ValueError as exc:
        raise ConfigurationError(f"TELEGRAM_API_ID={api_id_raw!r} is not a valid integer.") from exc

    allowed_raw = _env(source, "TELEGRAM_ALLOWED_CHATS")
    allowed_chats: FrozenSet[int] = frozenset()
    if allowed_raw:
        parsed = []
        for entry in allowed_raw.split(","):
            entry = entry.strip()
            if not entry:
                continue
            try:
                parsed.append(normalize_chat_id(entry))
            except InvalidChatIdError as exc:
                raise ConfigurationError(
                    f"TELEGRAM_ALLOWED_CHATS entry {entry!r} is not a numeric chat_id: {exc}"
                ) from exc
        allowed_chats = frozenset(parsed)
    # An empty/unset allowlist is not an error at config-load time -- every
    # tool call individually refuses via guard.py rule 2, with a clear
    # message, rather than the whole skill failing to even start. This lets
    # `whoami`-style diagnostics still explain *why* nothing works.

    confirm_mode = _env(source, "TELEGRAM_CONFIRM_MODE") or "tty"
    if confirm_mode not in ("tty", "flag"):
        raise ConfigurationError(f"TELEGRAM_CONFIRM_MODE={confirm_mode!r} must be 'tty' or 'flag'.")

    session_ttl_sec = _env_int(source, "TELEGRAM_SESSION_TTL_SEC", _DEFAULT_TTL_SEC)

    requested_max_read = _env_int(source, "TELEGRAM_MAX_READ_LIMIT", _DEFAULT_MAX_READ_LIMIT)
    max_read_limit = min(_DEFAULT_MAX_READ_LIMIT, requested_max_read)

    download_dir_raw = _env(source, "TELEGRAM_DOWNLOAD_DIR")
    download_dir = Path(download_dir_raw) if download_dir_raw else None

    session_file, peers_file, audit_log = _resolve_paths(source)

    return TelegramConfig(
        api_id=api_id,
        api_hash=api_hash,  # type: ignore[arg-type]
        allowed_chats=allowed_chats,
        session_file=session_file,
        peers_file=peers_file,
        audit_log=audit_log,
        session_ttl_sec=session_ttl_sec,
        confirm_mode=confirm_mode,
        download_dir=download_dir,
        max_read_limit=max_read_limit,
    )


# --------------------------------------------------------------------------
# Session blob
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class SessionState:
    session_string: str
    created_at: float
    ttl_sec: int


def _check_mode(path: Path, expected: int, label: str) -> None:
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode != expected:
        raise SessionSecurityError(
            f"Refusing to use {label} {path} -- mode is {oct(mode)}, expected "
            f"{oct(expected)}. A session/peers file with loose permissions is "
            "treated as forged/tampered and never trusted."
        )


def load_session_state(session_file: Path) -> Optional[SessionState]:
    """Load and validate the session blob, or return None if absent.

    Raises SessionSecurityError for a present-but-untrustworthy file: loose
    permissions, or a `created_at` in the future (clock skew or forgery).
    Does not itself check TTL expiry -- see `is_expired()`.
    """
    if not session_file.exists():
        return None
    _check_mode(session_file, 0o600, "session file")
    try:
        data = json.loads(session_file.read_text())
        session_string = data["session"]
        created_at = float(data["created_at"])
        ttl_sec = int(data["ttl_sec"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise SessionSecurityError(f"Session file {session_file} is malformed: {exc}") from exc

    if created_at > time.time() + _CLOCK_SKEW_TOLERANCE_SEC:
        raise SessionSecurityError(
            f"Session file {session_file} has created_at in the future -- "
            "treated as forged/tampered, refusing to use it."
        )
    return SessionState(session_string=session_string, created_at=created_at, ttl_sec=ttl_sec)


def is_expired(state: SessionState, config: TelegramConfig) -> bool:
    """TTL is absolute from creation, and the smaller of blob/env always wins.

    A blob can never extend its own life past what the current environment
    configures -- otherwise a captured blob with a large `ttl_sec` baked in
    would outlive whatever TTL the operator currently intends.
    """
    effective_ttl = min(state.ttl_sec, config.session_ttl_sec)
    return (time.time() - state.created_at) > effective_ttl


def write_session_state(session_file: Path, session_string: str, ttl_sec: int) -> SessionState:
    """Write the session blob. `0700` parent dir, `0600` file. USER-RUN only.

    Only ever called from `scripts/login.py` -- no runtime tool writes a
    session.
    """
    session_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    state = SessionState(session_string=session_string, created_at=time.time(), ttl_sec=ttl_sec)
    payload = {"session": state.session_string, "created_at": state.created_at, "ttl_sec": state.ttl_sec}
    fd = os.open(str(session_file), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, json.dumps(payload).encode("utf-8"))
    finally:
        os.close(fd)
    os.chmod(session_file, 0o600)
    return state


def delete_session_state(session_file: Path) -> None:
    session_file.unlink(missing_ok=True)


def load_peers(peers_file: Path) -> dict:
    """Load the `{marked_id: {kind, access_hash, title}}` map, or {} if absent."""
    if not peers_file.exists():
        return {}
    _check_mode(peers_file, 0o600, "peers file")
    try:
        raw = json.loads(peers_file.read_text())
    except json.JSONDecodeError as exc:
        raise SessionSecurityError(f"Peers file {peers_file} is malformed: {exc}") from exc
    return {int(k): v for k, v in raw.items()}


def write_peers(peers_file: Path, peers: dict) -> None:
    """Write the resolved-peer cache. USER-RUN only, from `scripts/login.py`."""
    peers_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    payload = {str(k): v for k, v in peers.items()}
    fd = os.open(str(peers_file), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, json.dumps(payload).encode("utf-8"))
    finally:
        os.close(fd)
    os.chmod(peers_file, 0o600)
