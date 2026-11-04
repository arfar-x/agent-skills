#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.31,<3", "urllib3>=1.26,<3"]
# ///
"""Command-line dispatcher for the Sentry skill: prints exactly one JSON document, like every skill here.

Usage:
    python scripts/sentry_tool.py get_issue --issue_id 1234
"""

from __future__ import annotations

import argparse
import json
import os
import sys

_SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SKILL_ROOT not in sys.path:
    sys.path.insert(0, _SKILL_ROOT)

from tools import get_issue  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sentry_tool")
    sub = parser.add_subparsers(dest="tool", required=True)
    p = sub.add_parser("get_issue", help="An error report's details: culprit, counts, tags, breadcrumbs, stack frames (read-only, redacted)")
    p.add_argument("--issue_id", required=True, help="The Sentry issue id (digits or short id)")
    return parser


def dispatch(args: argparse.Namespace):
    if args.tool == "get_issue":
        return get_issue.get_issue(args.issue_id)
    raise AssertionError(f"Unhandled tool: {args.tool}")


def main() -> int:
    try:
        result = dispatch(build_parser().parse_args())
    except Exception as exc:  # noqa: BLE001 -- keep the one-JSON-document contract
        result = {"error": {"type": "internal_error", "message": f"{type(exc).__name__}: {exc}"}}
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
