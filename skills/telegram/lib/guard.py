"""The enforcement layer. Every tool routes through this module before it
is allowed to reach Telethon at all.

This is the code the plan calls "genuinely agent-proof": these functions
don't trust a `--confirm` flag as a substitute for real verification where
one is available (the `tty` confirmation mode), and every check here holds
for a caller that never read `SKILL.md`, or deleted it -- `SKILL.md` is
advisory; this module is the guarantee. No function in this file, and no
CLI flag anywhere in `scripts/telegram_tool.py`, provides a bypass -- there
is no `--force`, no `--no-confirm`, no allowlist override. If you're
looking for one, it does not exist; that's the point.

Deliberately Telethon-free: everything here is pure Python so it's
unit-testable (including every adversarial test in `tests/`) without a real
Telegram connection.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Sequence

from .auth import TelegramConfig
from .utils import (
    InvalidChatIdError,
    UnsafeFilenameError,
    is_inside_git_worktree,
    is_service_notifications_peer,
    normalize_chat_id,
    redact as _redact,
    sanitize_download_filename,
)

DEFAULT_READ_LIMIT = 20
MAX_BULK_RECIPIENTS = 10
MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024


class GuardError(RuntimeError):
    """A hard refusal. `kind` is a stable machine-readable reason code."""

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind


# --------------------------------------------------------------------------
# Rule 2 + Rule 3: allowlist required, OTP chat denied unconditionally
# --------------------------------------------------------------------------


def authorize_chat(config: TelegramConfig, raw_chat_id: object) -> int:
    """Validate one target and return its canonical marked chat id.

    Every caller-supplied target must already be a bare numeric chat_id
    present in `TELEGRAM_ALLOWED_CHATS` -- usernames, links, phone numbers,
    and display names are rejected before they ever reach this function's
    allowlist check, by `normalize_chat_id` itself (that's rule 2's "no
    lookup" half). The OTP-account check (rule 3) runs *before* the
    allowlist check and cannot be satisfied by allowlisting it.
    """
    if not config.allowed_chats:
        raise GuardError(
            "no_allowlist_configured",
            "TELEGRAM_ALLOWED_CHATS is not set. This toolset refuses to do "
            "anything at all until an explicit allowlist is configured.",
        )
    try:
        marked_id = normalize_chat_id(raw_chat_id)
    except InvalidChatIdError as exc:
        raise GuardError("invalid_chat_id", str(exc)) from exc
    if is_service_notifications_peer(marked_id):
        raise GuardError(
            "otp_chat_denied",
            "Telegram's service-notifications account (delivers login codes "
            "and account-recovery messages) is refused for every action, "
            "unconditionally -- even if it is present in TELEGRAM_ALLOWED_CHATS. "
            "No environment variable overrides this.",
        )
    if marked_id not in config.allowed_chats:
        raise GuardError(
            "not_allowlisted",
            f"chat_id {marked_id} is not present in TELEGRAM_ALLOWED_CHATS. "
            "Only explicitly allowlisted chats are reachable -- this skill "
            "never looks a chat up by name, username, or membership.",
        )
    return marked_id


def authorize_targets(config: TelegramConfig, raw_targets: Sequence[object]) -> List[int]:
    """Validate a `send_bulk` recipient list. No dedup, ever.

    The cap is checked against the *raw* list length, before any
    deduplication -- deduplicating first would let 11 copies of the same
    recipient quietly pass a "at most 10" check. There is no deduplication
    anywhere in this path, on purpose.
    """
    if not raw_targets:
        raise GuardError("invalid_targets", "send_bulk requires at least one --to recipient.")
    if len(raw_targets) > MAX_BULK_RECIPIENTS:
        raise GuardError(
            "too_many_targets",
            f"send_bulk accepts at most {MAX_BULK_RECIPIENTS} recipients, got "
            f"{len(raw_targets)}. No wildcard, group, contact-list, or 'all' "
            "expansion is ever accepted -- every recipient must be named "
            "individually, and duplicates count toward the cap.",
        )
    return [authorize_chat(config, target) for target in raw_targets]


# --------------------------------------------------------------------------
# Rule 4: confirmation on every action, no exceptions
# --------------------------------------------------------------------------


def _open_tty():
    """Isolated so tests can substitute a fake terminal. Not a hook for bypass:
    it only ever changes *what stream the prompt reads from* in a test, and a
    test still has to type the same literal ``yes`` a human would.
    """
    return open("/dev/tty", "r+")


def _tty_confirm(summary: str) -> None:
    """Block on a literal ``yes`` typed at a real controlling terminal.

    Reads only from `/dev/tty`, never from stdin -- a pipe, heredoc, or
    `echo yes |` cannot answer this prompt, and an agent driving the CLI
    non-interactively cannot satisfy it either. Hard-refuses when no
    controlling terminal exists, rather than falling back to stdin.
    """
    try:
        tty = _open_tty()
    except OSError as exc:
        raise GuardError(
            "tty_unavailable",
            "This action requires a 'yes' typed at a real terminal, and no "
            "controlling terminal (/dev/tty) is available in this process. "
            "Hand the user the exact command to run themselves -- do not "
            "retry with --confirm, and do not pipe an answer into stdin.",
        ) from exc
    try:
        tty.write(f"\n{summary}\nType exactly 'yes' to proceed: ")
        tty.flush()
        answer = tty.readline().strip()
    finally:
        tty.close()
    if answer != "yes":
        raise GuardError(
            "tty_declined",
            "Confirmation was not given (expected the literal text 'yes').",
        )


def gate(
    config: TelegramConfig,
    *,
    tool: str,
    outbound: bool,
    confirm: bool,
    summary: str,
    pending_action: Dict[str, object],
) -> Optional[Dict[str, object]]:
    """The single confirmation checkpoint every tool calls before acting.

    Returns ``None`` when the caller may proceed. Otherwise returns the
    ``{"confirmed": false, "requires_confirmation": true, ...}`` shape the
    tool must return as-is (mirrors `skills/jira/tools/worklog.py`) -- this
    is not a `GuardError`, because declining to act without confirmation is
    the expected, non-exceptional first call, not a failure.

    ``outbound`` marks actions with a real-world effect the other party can
    observe: `send_message`, `send_bulk`, `forward_message`, and
    `--no-seen false` on a read. Everything else (plain reads, search,
    mark_read, download, whoami, logout) is *not* outbound even though it
    is still gated -- it just never gets the `tty`-mode terminal prompt,
    only the two-step.

    In `tty` mode (the default), an outbound action ignores ``confirm``
    entirely and always goes through `_tty_confirm` -- passing `--confirm`
    on the very first call does not skip the terminal prompt. In `flag`
    mode, and for every non-outbound action in either mode, this is a plain
    two-step: the first call (``confirm=False``) returns the pending-action
    dict; a second, identical call with ``confirm=True`` proceeds.
    """
    if outbound and config.confirm_mode == "tty":
        _tty_confirm(summary)
        return None
    if not confirm:
        return {
            "confirmed": False,
            "requires_confirmation": True,
            "pending_action": {**pending_action, "action": tool, "summary": summary},
        }
    return None


# --------------------------------------------------------------------------
# Rule 6: redaction
# --------------------------------------------------------------------------


def redact_outbound(text: Optional[str]) -> tuple[str, int]:
    """Mask OTP/token-shaped substrings before a message body leaves this
    process, inbound (report to the agent) or outbound (about to be sent).

    Regex-based and imperfect -- see `lib/utils.py` and
    `skills/telegram/README.md`'s security model for what this does not
    catch. Callers must surface a nonzero `redactions` count rather than
    presenting the masked text as complete.
    """
    return _redact(text)


# --------------------------------------------------------------------------
# Rule 7: hard caps
# --------------------------------------------------------------------------


def clamp_read_limit(config: TelegramConfig, requested: Optional[object]) -> int:
    if requested is None:
        return DEFAULT_READ_LIMIT
    try:
        value = int(requested)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise GuardError("invalid_limit", f"--limit must be an integer, got {requested!r}.") from exc
    if value <= 0:
        raise GuardError("invalid_limit", f"--limit must be a positive integer, got {value}.")
    return min(value, config.max_read_limit)


# --------------------------------------------------------------------------
# Rule 8: download hardening
# --------------------------------------------------------------------------

_DANGEROUS_EXACT_DIRS = {Path("/"), Path.home()}


def authorize_download_dir(out_dir: Optional[object]) -> Path:
    """Validate `--out_dir`/`TELEGRAM_DOWNLOAD_DIR`. There is no default."""
    if out_dir is None:
        raise GuardError(
            "missing_out_dir",
            "download_media requires an explicit --out_dir (or "
            "TELEGRAM_DOWNLOAD_DIR) -- there is no default location inside "
            "this skill or the repo.",
        )
    resolved = Path(out_dir).expanduser().resolve()
    if resolved in _DANGEROUS_EXACT_DIRS or len(resolved.parts) <= 2:
        raise GuardError(
            "unsafe_out_dir",
            f"Refusing to download into {resolved} -- too broad a target. "
            "Pick a specific subdirectory.",
        )
    if is_inside_git_worktree(resolved):
        raise GuardError(
            "unsafe_out_dir",
            f"Refusing to download into {resolved} -- it resolves inside a "
            "git work tree (this repo, or any other).",
        )
    return resolved


def authorize_download_size(size_bytes: Optional[int]) -> None:
    if size_bytes is not None and size_bytes > MAX_DOWNLOAD_BYTES:
        raise GuardError(
            "oversize",
            f"Refusing to download {size_bytes} bytes -- exceeds the "
            f"{MAX_DOWNLOAD_BYTES}-byte cap.",
        )


def authorize_filename(name: str) -> str:
    try:
        return sanitize_download_filename(name)
    except UnsafeFilenameError as exc:
        raise GuardError("unsafe_filename", str(exc)) from exc
