#!/usr/bin/env python3
"""Command-line dispatcher for the Jira Assistant skill's tools.

Hermes invokes skills by running shell commands (via its `terminal` /
`execute_code` sandbox), not by calling Python functions directly. This
script is the bridge: it exposes every tool in `tools/` as a subcommand
and always prints exactly one JSON document to stdout, so the agent can
parse the result the same way regardless of success or failure.

Usage:
    python scripts/jira_tool.py my_work
    python scripts/jira_tool.py issue_summary --issue_key PAY-123
    python scripts/jira_tool.py blockers --issue_key PAY-123
    python scripts/jira_tool.py search --jql "assignee = currentUser()"
    python scripts/jira_tool.py worklog --issue_key PAY-123 --duration 2h \\
        --description "implementing validation" [--confirm]
    python scripts/jira_tool.py transition --issue_key PAY-123 --status Review [--confirm]
    python scripts/jira_tool.py sprint [--board_id 3]
    python scripts/jira_tool.py worklog_report [--since -14d] [--until ...] [--max_issues 50]
    python scripts/jira_tool.py list_fields

Every subcommand prints JSON only (never prose) and always exits 0 on a
handled error -- failures are reported as {"error": {...}} in the JSON
body, per this skill's "thin tools" design. A non-zero exit code means
the CLI invocation itself was malformed (e.g. unknown subcommand).
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
    blockers,
    issue_summary,
    list_fields,
    my_work,
    search,
    sprint,
    transition,
    worklog,
    worklog_report,
)


def _add_common(parser: argparse.ArgumentParser, *, issue_key: bool = False) -> None:
    if issue_key:
        parser.add_argument("--issue_key", required=True, help="Issue key, e.g. PAY-123")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jira_tool", description="Jira Assistant tool dispatcher")
    subparsers = parser.add_subparsers(dest="tool", required=True)

    p = subparsers.add_parser("my_work", help="List unresolved issues assigned to the current user")
    p.add_argument("--order_by", default="priority DESC, updated DESC")
    p.add_argument("--max_results", type=int, default=100)

    p = subparsers.add_parser("issue_summary", help="Full context for one issue")
    _add_common(p, issue_key=True)

    p = subparsers.add_parser("blockers", help="Blocking status and reasons for one issue")
    _add_common(p, issue_key=True)

    p = subparsers.add_parser("search", help="Run arbitrary JQL")
    p.add_argument("--jql", required=True)
    p.add_argument("--max_results", type=int, default=100)
    p.add_argument(
        "--fields",
        default=None,
        help="Comma-separated extra field IDs to request (e.g. from list_fields), "
        "in addition to the default set",
    )

    p = subparsers.add_parser("transition", help="Move an issue to a new status (write, gated)")
    _add_common(p, issue_key=True)
    p.add_argument("--status", required=True, help="Target status or transition name, e.g. Review")
    p.add_argument("--confirm", action="store_true", help="Only pass after the user has explicitly confirmed")

    p = subparsers.add_parser("worklog", help="Log time against an issue (write, gated)")
    _add_common(p, issue_key=True)
    p.add_argument("--duration", required=True, help='Jira-style duration, e.g. "2h", "1d 30m"')
    p.add_argument("--description", required=True)
    p.add_argument("--confirm", action="store_true", help="Only pass after the user has explicitly confirmed")

    p = subparsers.add_parser("sprint", help="Active sprint, board, dates, and goal")
    p.add_argument("--board_id", type=int, default=None)

    p = subparsers.add_parser(
        "worklog_report", help="Aggregate the current user's logged time over a date range"
    )
    p.add_argument("--since", default="-14d", help='Relative ("-14d") or ISO date/datetime. Default: -14d')
    p.add_argument("--until", default=None, help="Relative or ISO date/datetime. Default: now")
    p.add_argument("--max_issues", type=int, default=50)

    subparsers.add_parser("list_fields", help="Enumerate every field this Jira instance knows about")

    return parser


def dispatch(args: argparse.Namespace):
    if args.tool == "my_work":
        return my_work.my_work(order_by=args.order_by, max_results=args.max_results)
    if args.tool == "issue_summary":
        return issue_summary.issue_summary(args.issue_key)
    if args.tool == "blockers":
        return blockers.blockers(args.issue_key)
    if args.tool == "search":
        extra_fields = args.fields.split(",") if args.fields else None
        return search.search(args.jql, max_results=args.max_results, fields=extra_fields)
    if args.tool == "transition":
        return transition.transition(args.issue_key, args.status, confirm=args.confirm)
    if args.tool == "worklog":
        return worklog.worklog(args.issue_key, args.duration, args.description, confirm=args.confirm)
    if args.tool == "sprint":
        return sprint.sprint(board_id=args.board_id)
    if args.tool == "worklog_report":
        return worklog_report.worklog_report(since=args.since, until=args.until, max_issues=args.max_issues)
    if args.tool == "list_fields":
        return list_fields.list_fields()
    raise AssertionError(f"Unhandled tool: {args.tool}")  # unreachable: argparse enforces choices


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    result = dispatch(args)
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
