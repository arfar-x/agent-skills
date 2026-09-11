#!/usr/bin/env python3
"""Command-line dispatcher for the Confluence Assistant skill's tools.

Hermes invokes skills by running shell commands (via its `terminal` /
`execute_code` sandbox), not by calling Python functions directly. This
script is the bridge: it exposes every tool in `tools/` as a subcommand
and always prints exactly one JSON document to stdout, so the agent can
parse the result the same way regardless of success or failure. Same
contract `jira/scripts/jira_tool.py` uses.

Usage:
    python scripts/confluence_tool.py get_page --page_id 12345678
    python scripts/confluence_tool.py get_page_by_title --space_key ENG --title "Onboarding"
    python scripts/confluence_tool.py search --cql "space = ENG AND type = page" [--include_body]
    python scripts/confluence_tool.py list_spaces
    python scripts/confluence_tool.py get_space --space_key ENG
    python scripts/confluence_tool.py get_comments --page_id 12345678
    python scripts/confluence_tool.py get_attachments --page_id 12345678
    python scripts/confluence_tool.py get_children --page_id 12345678
    python scripts/confluence_tool.py get_labels --page_id 12345678
    python scripts/confluence_tool.py page_summary --page_id 12345678 [--sections page,comments]
    python scripts/confluence_tool.py my_pages
    python scripts/confluence_tool.py create_page --space_key ENG --title "..." \\
        --body_storage "<p>...</p>" [--parent_id 12345678] [--confirm]
    python scripts/confluence_tool.py update_page --page_id 12345678 \\
        [--title "..."] [--body_storage "<p>...</p>"] [--confirm]
    python scripts/confluence_tool.py delete_page --page_id 12345678 [--confirm]
    python scripts/confluence_tool.py add_comment --page_id 12345678 --body_storage "<p>...</p>" [--confirm]
    python scripts/confluence_tool.py add_label --page_id 12345678 --label onboarding [--confirm]
    python scripts/confluence_tool.py remove_label --page_id 12345678 --label onboarding [--confirm]

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

from lib.auth import ConfigurationError  # noqa: E402
from tools import (  # noqa: E402
    add_comment,
    add_label,
    create_page,
    delete_page,
    get_attachments,
    get_children,
    get_comments,
    get_labels,
    get_page,
    get_page_by_title,
    get_space,
    list_spaces,
    my_pages,
    page_summary,
    remove_label,
    search,
    update_page,
)


def _add_page_id(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--page_id", required=True, help="Content id of the page, e.g. 12345678")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="confluence_tool", description="Confluence Assistant tool dispatcher")
    subparsers = parser.add_subparsers(dest="tool", required=True)

    p = subparsers.add_parser("get_page", help="Fetch a single page by its content id")
    _add_page_id(p)
    p.add_argument(
        "--expand",
        default=None,
        help="Comma-separated raw Confluence expand parameters. Omit for the default set "
        "(body.storage,version,space,ancestors,history).",
    )

    p = subparsers.add_parser("get_page_by_title", help="Resolve a page by its space + exact title")
    p.add_argument("--space_key", required=True, help="Space key, e.g. ENG")
    p.add_argument("--title", required=True, help="Exact page title")

    p = subparsers.add_parser("search", help="Run arbitrary CQL")
    p.add_argument("--cql", required=True)
    p.add_argument("--max_results", type=int, default=50)
    p.add_argument(
        "--include_body",
        action="store_true",
        help="Also fetch and return each result's body_plain_text (off by default -- "
        "page bodies are often the largest single field).",
    )

    subparsers.add_parser("list_spaces", help="Enumerate every space visible to the authenticated user")

    p = subparsers.add_parser("get_space", help="Fetch one space's identity and description")
    p.add_argument("--space_key", required=True, help="Space key, e.g. ENG")

    p = subparsers.add_parser("get_comments", help="Fetch every comment on a page")
    _add_page_id(p)
    p.add_argument("--max_results", type=int, default=None)

    p = subparsers.add_parser("get_attachments", help="List a page's attachments (metadata only)")
    _add_page_id(p)
    p.add_argument("--max_results", type=int, default=None)

    p = subparsers.add_parser("get_children", help="List a page's direct child pages")
    _add_page_id(p)
    p.add_argument("--max_results", type=int, default=None)

    p = subparsers.add_parser("get_labels", help="List the labels currently on a page")
    _add_page_id(p)

    p = subparsers.add_parser("page_summary", help="Full context for one page: content, comments, attachments, labels, children")
    _add_page_id(p)
    p.add_argument(
        "--sections",
        default=None,
        help="Comma-separated subset of page,comments,attachments,labels,children to "
        "fetch and return. Omit for all.",
    )

    p = subparsers.add_parser("my_pages", help="Pages authored by the current user, most recently modified first")
    p.add_argument("--max_results", type=int, default=50)

    p = subparsers.add_parser("create_page", help="Create a new page (write, gated)")
    p.add_argument("--space_key", required=True, help="Destination space key, e.g. ENG")
    p.add_argument("--title", required=True)
    p.add_argument(
        "--body_storage",
        required=True,
        help="Page content as Confluence storage-format XHTML, e.g. '<p>Hello</p>' -- not Markdown.",
    )
    p.add_argument("--parent_id", default=None, help="Optional parent page id, to create as a child page")
    p.add_argument("--confirm", action="store_true", help="Only pass after the user has explicitly confirmed")

    p = subparsers.add_parser("update_page", help="Update a page's title and/or content (write, gated)")
    _add_page_id(p)
    p.add_argument("--title", default=None, help="New title (omit to leave unchanged)")
    p.add_argument(
        "--body_storage",
        default=None,
        help="New content, Confluence storage-format XHTML (omit to leave unchanged). "
        "Replaces the entire body.",
    )
    p.add_argument("--confirm", action="store_true", help="Only pass after the user has explicitly confirmed")

    p = subparsers.add_parser("delete_page", help="Permanently delete a page (write, gated, destructive)")
    _add_page_id(p)
    p.add_argument("--confirm", action="store_true", help="Only pass after the user has explicitly confirmed")

    p = subparsers.add_parser("add_comment", help="Add a comment to a page (write, gated)")
    _add_page_id(p)
    p.add_argument("--body_storage", required=True, help="Comment content, Confluence storage-format XHTML")
    p.add_argument("--confirm", action="store_true", help="Only pass after the user has explicitly confirmed")

    p = subparsers.add_parser("add_label", help="Add a label to a page (write, gated)")
    _add_page_id(p)
    p.add_argument("--label", required=True, help='Label name to add, e.g. "onboarding"')
    p.add_argument("--confirm", action="store_true", help="Only pass after the user has explicitly confirmed")

    p = subparsers.add_parser("remove_label", help="Remove a label from a page (write, gated)")
    _add_page_id(p)
    p.add_argument("--label", required=True, help="Label name to remove")
    p.add_argument("--confirm", action="store_true", help="Only pass after the user has explicitly confirmed")

    return parser


def dispatch(args: argparse.Namespace):
    if args.tool == "get_page":
        expand = args.expand.split(",") if args.expand else None
        return get_page.get_page(args.page_id, expand=expand)
    if args.tool == "get_page_by_title":
        return get_page_by_title.get_page_by_title(args.space_key, args.title)
    if args.tool == "search":
        return search.search(args.cql, max_results=args.max_results, include_body=args.include_body)
    if args.tool == "list_spaces":
        return list_spaces.list_spaces()
    if args.tool == "get_space":
        return get_space.get_space(args.space_key)
    if args.tool == "get_comments":
        return get_comments.get_comments(args.page_id, max_results=args.max_results)
    if args.tool == "get_attachments":
        return get_attachments.get_attachments(args.page_id, max_results=args.max_results)
    if args.tool == "get_children":
        return get_children.get_children(args.page_id, max_results=args.max_results)
    if args.tool == "get_labels":
        return get_labels.get_labels(args.page_id)
    if args.tool == "page_summary":
        sections = args.sections.split(",") if args.sections else None
        return page_summary.page_summary(args.page_id, sections=sections)
    if args.tool == "my_pages":
        return my_pages.my_pages(max_results=args.max_results)
    if args.tool == "create_page":
        return create_page.create_page(
            args.space_key, args.title, args.body_storage, parent_id=args.parent_id, confirm=args.confirm
        )
    if args.tool == "update_page":
        return update_page.update_page(
            args.page_id, title=args.title, body_storage=args.body_storage, confirm=args.confirm
        )
    if args.tool == "delete_page":
        return delete_page.delete_page(args.page_id, confirm=args.confirm)
    if args.tool == "add_comment":
        return add_comment.add_comment(args.page_id, args.body_storage, confirm=args.confirm)
    if args.tool == "add_label":
        return add_label.add_label(args.page_id, args.label, confirm=args.confirm)
    if args.tool == "remove_label":
        return remove_label.remove_label(args.page_id, args.label, confirm=args.confirm)
    raise AssertionError(f"Unhandled tool: {args.tool}")  # unreachable: argparse enforces choices


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    # Every actual tool body already runs inside tools/_common.py's
    # run_tool(), which catches everything (including ConfigurationError,
    # e.g. from lib.auth.load_credential()) and returns a clean
    # {"error": {...}} dict -- this call practically never sees an
    # exception in normal operation. This try/except exists for whatever
    # is NOT inside a tool's own run_tool()-wrapped closure -- e.g.
    # dispatch()'s final `raise AssertionError("Unhandled tool: ...")`,
    # marked unreachable but still worth catching rather than trusting --
    # so this script's documented contract (see module docstring: one
    # JSON document, always, never a raw traceback) holds even outside
    # run_tool()'s coverage, not just within it.
    try:
        result = dispatch(args)
    except ConfigurationError as exc:
        result = {"error": {"type": "configuration_error", "message": str(exc)}}
    except Exception as exc:  # noqa: BLE001 -- last-resort safety net, see comment above
        result = {"error": {"type": "internal_error", "message": f"{type(exc).__name__}: {exc}"}}
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
