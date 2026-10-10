#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "requests>=2.31,<3",
#   "urllib3>=1.26,<3",
# ]
# ///
"""Command-line dispatcher for the GitLab (glab) skill's tools.

Exposes every tool in `tools/` as a subcommand and always prints exactly
one JSON document to stdout, so the agent parses success and failure the
same way. Same contract `confluence/scripts/confluence_tool.py` uses.

Usage:
    python scripts/glab_tool.py whoami
    python scripts/glab_tool.py get_project --project group/repo
    python scripts/glab_tool.py search_projects --search repo [--membership]
    python scripts/glab_tool.py list_branches --project group/repo [--search feat]
    python scripts/glab_tool.py get_tree --project group/repo [--path src] [--ref main] [--recursive]
    python scripts/glab_tool.py get_file --project group/repo --file_path src/a.py --ref main
    python scripts/glab_tool.py list_mrs [--project group/repo] [--state opened] [--scope assigned_to_me]
    python scripts/glab_tool.py get_mr --project group/repo --mr_iid 42
    python scripts/glab_tool.py get_mr_diff --project group/repo --mr_iid 42 [--file_path src/a.py]
    python scripts/glab_tool.py get_mr_discussions --project group/repo --mr_iid 42
    python scripts/glab_tool.py add_mr_note --project group/repo --mr_iid 42 --body "..." [--draft] [--confirm]
    python scripts/glab_tool.py add_mr_discussion --project group/repo --mr_iid 42 \\
        --file_path src/a.py --new_line 10 --body "..." [--draft] [--confirm]
    python scripts/glab_tool.py edit_mr_note --project group/repo --mr_iid 42 \\
        --discussion_id abc123 --note_id 7 --body "..." [--confirm]
    python scripts/glab_tool.py delete_mr_note --project group/repo --mr_iid 42 \\
        --discussion_id abc123 --note_id 7 [--confirm]

Every subcommand prints JSON only and exits 0 on a handled error --
failures are `{"error": {...}}` in the body. A non-zero exit means the
invocation itself was malformed.
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
    add_mr_discussion,
    add_mr_note,
    delete_mr_note,
    edit_mr_note,
    get_file,
    get_mr,
    get_mr_diff,
    get_mr_discussions,
    get_project,
    get_tree,
    list_branches,
    list_mrs,
    search_projects,
    whoami,
)

_PROJECT_HELP = "Project numeric id or group/sub/project path (default: GITLAB_DEFAULT_PROJECT)"
_CONFIRM_HELP = "Only pass after the user has explicitly confirmed"


def _add_project(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project", help=_PROJECT_HELP)


def _add_mr(parser: argparse.ArgumentParser) -> None:
    _add_project(parser)
    parser.add_argument("--mr_iid", required=True, type=int, help="Merge request number (the N in .../merge_requests/N)")


def _add_note(parser: argparse.ArgumentParser) -> None:
    _add_mr(parser)
    parser.add_argument("--discussion_id", required=True, help="The note's discussion `id` (from get_mr_discussions)")
    parser.add_argument("--note_id", required=True, type=int, help="The note's `id` within that discussion (from get_mr_discussions)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="glab_tool", description="GitLab (glab) tool dispatcher")
    sub = parser.add_subparsers(dest="tool", required=True)

    sub.add_parser("whoami", help="Show which GitLab user the configured token acts as")

    p = sub.add_parser("get_project", help="Fetch a project's identity, default branch, and URL")
    _add_project(p)

    p = sub.add_parser("search_projects", help="Find projects by name or path fragment")
    p.add_argument("--search", required=True, help="Name or path fragment")
    p.add_argument("--membership", action="store_true", help="Only projects the user is a member of")
    p.add_argument("--max_results", type=int, default=20)

    p = sub.add_parser("list_branches", help="List a project's branches")
    _add_project(p)
    p.add_argument("--search", help="Branch name fragment")
    p.add_argument("--max_results", type=int, default=50)

    p = sub.add_parser("get_tree", help="List files and directories in a repository at a ref")
    _add_project(p)
    p.add_argument("--path", help="Subdirectory to list (default: repository root)")
    p.add_argument("--ref", help="Branch, tag, or commit (default: the default branch)")
    p.add_argument("--recursive", action="store_true", help="Descend into subdirectories")
    p.add_argument("--max_results", type=int, default=200)

    p = sub.add_parser("get_file", help="Read one file's content at a ref")
    _add_project(p)
    p.add_argument("--file_path", required=True, help="Path of the file in the repository")
    p.add_argument("--ref", required=True, help="Branch, tag, or commit SHA")
    p.add_argument("--max_bytes", type=int, default=200_000, help="Truncate content beyond this many bytes")

    p = sub.add_parser("list_mrs", help="List merge requests, in one project or instance-wide")
    _add_project(p)
    p.add_argument("--state", choices=["opened", "closed", "merged", "locked", "all"], default="opened")
    p.add_argument("--scope", choices=["created_by_me", "assigned_to_me", "all"], default="all")
    p.add_argument("--reviewer_me", action="store_true", help="Only MRs where the token's user is a reviewer")
    p.add_argument("--search", help="Match in title or description")
    p.add_argument("--max_results", type=int, default=20)

    p = sub.add_parser("get_mr", help="Fetch one merge request's details, including diff_refs")
    _add_mr(p)

    p = sub.add_parser("get_mr_diff", help="Per-file unified diffs of a merge request")
    _add_mr(p)
    p.add_argument("--file_path", help="Only this file's diff")

    p = sub.add_parser("get_mr_discussions", help="Every discussion thread (inline and general) on a merge request")
    _add_mr(p)

    p = sub.add_parser("add_mr_note", help="Post a general comment on a merge request (write, gated)")
    _add_mr(p)
    p.add_argument("--body", required=True, help="Comment text, GitLab Markdown")
    p.add_argument("--draft", action="store_true", help="Save as a draft note, unpublished until the user submits their review")
    p.add_argument("--confirm", action="store_true", help=_CONFIRM_HELP)

    p = sub.add_parser("add_mr_discussion", help="Post an inline comment on a diff line of a merge request (write, gated)")
    _add_mr(p)
    p.add_argument("--file_path", required=True, help="Path of the changed file")
    p.add_argument("--new_line", type=int, help="Line number on the new side (added or unchanged line)")
    p.add_argument("--old_line", type=int, help="Line number on the old side (removed line)")
    p.add_argument("--body", required=True, help="Comment text, GitLab Markdown")
    p.add_argument("--draft", action="store_true", help="Save as a draft note, unpublished until the user submits their review")
    p.add_argument("--confirm", action="store_true", help=_CONFIRM_HELP)

    p = sub.add_parser("edit_mr_note", help="Replace the body of an existing merge request comment (write, gated)")
    _add_note(p)
    p.add_argument("--body", required=True, help="New comment text, GitLab Markdown")
    p.add_argument("--confirm", action="store_true", help=_CONFIRM_HELP)

    p = sub.add_parser("delete_mr_note", help="Permanently delete a merge request comment (destructive write, gated)")
    _add_note(p)
    p.add_argument("--confirm", action="store_true", help=_CONFIRM_HELP)

    return parser


def dispatch(args: argparse.Namespace):
    t = args.tool
    if t == "whoami":
        return whoami.whoami()
    if t == "get_project":
        return get_project.get_project(args.project)
    if t == "search_projects":
        return search_projects.search_projects(args.search, args.membership, args.max_results)
    if t == "list_branches":
        return list_branches.list_branches(args.project, args.search, args.max_results)
    if t == "get_tree":
        return get_tree.get_tree(args.project, args.path, args.ref, args.recursive, args.max_results)
    if t == "get_file":
        return get_file.get_file(args.file_path, args.ref, args.project, args.max_bytes)
    if t == "list_mrs":
        return list_mrs.list_mrs(args.project, args.state, args.scope, args.reviewer_me, args.search, args.max_results)
    if t == "get_mr":
        return get_mr.get_mr(args.mr_iid, args.project)
    if t == "get_mr_diff":
        return get_mr_diff.get_mr_diff(args.mr_iid, args.project, args.file_path)
    if t == "get_mr_discussions":
        return get_mr_discussions.get_mr_discussions(args.mr_iid, args.project)
    if t == "add_mr_note":
        return add_mr_note.add_mr_note(args.mr_iid, args.body, args.project, args.draft, args.confirm)
    if t == "add_mr_discussion":
        return add_mr_discussion.add_mr_discussion(
            args.mr_iid, args.file_path, args.body, args.project, args.new_line, args.old_line, args.draft, args.confirm
        )
    if t == "edit_mr_note":
        return edit_mr_note.edit_mr_note(args.mr_iid, args.discussion_id, args.note_id, args.body, args.project, args.confirm)
    if t == "delete_mr_note":
        return delete_mr_note.delete_mr_note(args.mr_iid, args.discussion_id, args.note_id, args.project, args.confirm)
    raise AssertionError(f"Unhandled tool: {t}")  # unreachable: argparse enforces choices


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = dispatch(args)
    except ConfigurationError as exc:
        result = {"error": {"type": "configuration_error", "message": str(exc)}}
    except Exception as exc:  # noqa: BLE001 -- keep the one-JSON-document contract even outside run_tool()
        result = {"error": {"type": "internal_error", "message": f"{type(exc).__name__}: {exc}"}}
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
