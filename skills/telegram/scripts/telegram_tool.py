#!/usr/bin/env python3
"""Command-line dispatcher for the Telegram skill's tools.

Mirrors `skills/jira/scripts/jira_tool.py`'s design: every tool in `tools/`
is exposed as a subcommand, and this always prints exactly one JSON
document to stdout, success or failure, so the agent can parse the result
the same way regardless of outcome.

There is no `--force`, `--no-confirm`, `--skip-guard`, or allowlist-override
flag anywhere below, on any subcommand -- that is not an oversight, see
`lib/guard.py`'s module docstring.

Usage:
    python scripts/telegram_tool.py whoami [--confirm]
    python scripts/telegram_tool.py allowed_chats [--confirm]
    python scripts/telegram_tool.py logout [--confirm]
    python scripts/telegram_tool.py read_messages --chat_id 123456 \\
        [--limit 20] [--no-seen true|false] [--confirm]
    python scripts/telegram_tool.py search_messages --chat_id 123456 \\
        --query "..." [--limit 20] [--no-seen true|false] [--confirm]
    python scripts/telegram_tool.py mark_read --chat_id 123456 [--confirm]
    python scripts/telegram_tool.py send_message --chat_id 123456 \\
        --text "..." [--confirm]
    python scripts/telegram_tool.py send_bulk --to 123456 --to 789012 \\
        --text "..." [--confirm]
    python scripts/telegram_tool.py forward_message --from_chat_id 123456 \\
        --message_id 42 --to_chat_id 789012 [--confirm]
    python scripts/telegram_tool.py download_media --chat_id 123456 \\
        --message_id 42 [--out_dir /path/to/dir] [--confirm]

Every subcommand prints JSON only (never prose) and always exits 0 on a
handled error -- failures are reported as {"error": {...}} in the JSON
body. A non-zero exit code means the CLI invocation itself was malformed.

In `TELEGRAM_CONFIRM_MODE=tty` (the default), `--confirm` is accepted on
every subcommand for uniformity but is *ignored* for the outbound actions
(`send_message`, `send_bulk`, `forward_message`, `--no-seen false`) -- those
always demand a literal `yes` typed at `/dev/tty` regardless of `--confirm`.
See `lib/guard.py`'s `gate()`.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

_SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SKILL_ROOT not in sys.path:
    sys.path.insert(0, _SKILL_ROOT)

from tools import (  # noqa: E402
    allowed_chats,
    download_media,
    forward_message,
    logout,
    mark_read,
    read_messages,
    search_messages,
    send_bulk,
    send_message,
    whoami,
)


def _bool_arg(raw: str) -> bool:
    lowered = raw.strip().lower()
    if lowered in ("true", "1", "yes"):
        return True
    if lowered in ("false", "0", "no"):
        return False
    raise argparse.ArgumentTypeError(f"expected true/false, got {raw!r}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="telegram_tool", description="Telegram skill tool dispatcher")
    subparsers = parser.add_subparsers(dest="tool", required=True)

    p = subparsers.add_parser("whoami", help="Identify which Telegram account this session belongs to")
    p.add_argument("--confirm", action="store_true")

    p = subparsers.add_parser("allowed_chats", help="List TELEGRAM_ALLOWED_CHATS with cached titles; no network call")
    p.add_argument("--confirm", action="store_true")

    p = subparsers.add_parser("logout", help="Revoke the session server-side and delete it locally")
    p.add_argument("--confirm", action="store_true")

    p = subparsers.add_parser("read_messages", help="Fetch recent messages from one allowlisted chat")
    p.add_argument("--chat_id", required=True)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument(
        "--no-seen", dest="no_seen", type=_bool_arg, default=True,
        help="Default true: fetch without sending a read receipt. false is gated like a send.",
    )
    p.add_argument("--confirm", action="store_true")

    p = subparsers.add_parser("search_messages", help="Server-side text search within one allowlisted chat")
    p.add_argument("--chat_id", required=True)
    p.add_argument("--query", required=True)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--no-seen", dest="no_seen", type=_bool_arg, default=True)
    p.add_argument("--confirm", action="store_true")

    p = subparsers.add_parser("mark_read", help="Explicitly send a read receipt for an entire chat")
    p.add_argument("--chat_id", required=True)
    p.add_argument("--confirm", action="store_true")

    p = subparsers.add_parser("send_message", help="Send one message to one allowlisted chat")
    p.add_argument("--chat_id", required=True)
    p.add_argument("--text", required=True)
    p.add_argument("--confirm", action="store_true")

    p = subparsers.add_parser("send_bulk", help="Send the same message to a small, explicit recipient list")
    p.add_argument("--to", action="append", required=True, help="Repeat --to once per recipient, max 10")
    p.add_argument("--text", required=True)
    p.add_argument("--confirm", action="store_true")

    p = subparsers.add_parser("forward_message", help="Forward one message between two allowlisted chats")
    p.add_argument("--from_chat_id", required=True)
    p.add_argument("--message_id", required=True)
    p.add_argument("--to_chat_id", required=True)
    p.add_argument("--confirm", action="store_true")

    p = subparsers.add_parser("download_media", help="Save one message's media attachment to disk")
    p.add_argument("--chat_id", required=True)
    p.add_argument("--message_id", required=True)
    p.add_argument("--out_dir", default=None)
    p.add_argument("--confirm", action="store_true")

    return parser


def dispatch(args: argparse.Namespace):
    if args.tool == "whoami":
        return whoami.whoami(confirm=args.confirm)
    if args.tool == "allowed_chats":
        return allowed_chats.allowed_chats(confirm=args.confirm)
    if args.tool == "logout":
        return logout.logout(confirm=args.confirm)
    if args.tool == "read_messages":
        return read_messages.read_messages(
            chat_id=args.chat_id, limit=args.limit, no_seen=args.no_seen, confirm=args.confirm
        )
    if args.tool == "search_messages":
        return search_messages.search_messages(
            chat_id=args.chat_id, query=args.query, limit=args.limit, no_seen=args.no_seen, confirm=args.confirm
        )
    if args.tool == "mark_read":
        return mark_read.mark_read(chat_id=args.chat_id, confirm=args.confirm)
    if args.tool == "send_message":
        return send_message.send_message(chat_id=args.chat_id, text=args.text, confirm=args.confirm)
    if args.tool == "send_bulk":
        return send_bulk.send_bulk(to=args.to, text=args.text, confirm=args.confirm)
    if args.tool == "forward_message":
        return forward_message.forward_message(
            from_chat_id=args.from_chat_id,
            message_id=args.message_id,
            to_chat_id=args.to_chat_id,
            confirm=args.confirm,
        )
    if args.tool == "download_media":
        return download_media.download_media(
            chat_id=args.chat_id, message_id=args.message_id, out_dir=args.out_dir, confirm=args.confirm
        )
    raise SystemExit(f"Unknown tool: {args.tool}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    result = dispatch(args)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
