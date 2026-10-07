"""add_mr_discussion: post an inline comment on a specific line of an MR's diff.

Write operation, gated. The exact GitLab ``position`` (SHAs, old/new
line pair) is resolved from the MR's own diff, and is resolved *before*
the confirm gate, so an impossible line fails fast instead of after the
user has already approved.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from lib.glab_client import get_client
from tools._common import ToolInputError, require_iid, require_str, resolve_project, run_tool


def add_mr_discussion(
    mr_iid: int,
    file_path: str,
    body: str,
    project: Optional[str] = None,
    new_line: Optional[int] = None,
    old_line: Optional[int] = None,
    draft: bool = False,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Post an inline comment at ``file_path`` + ``new_line`` (added or
    unchanged line) or ``old_line`` (removed line)."""

    def _run() -> Dict[str, Any]:
        proj = resolve_project(project)
        iid = require_iid(mr_iid)
        path = require_str(file_path, "file_path")
        text = require_str(body, "body")
        if new_line is None and old_line is None:
            raise ToolInputError("Provide --new_line (added/unchanged line) or --old_line (removed line).")
        client = get_client()

        position = client.resolve_inline_position(proj, iid, path, new_line=new_line, old_line=old_line)

        if not confirm and not client.config.auto_confirm_writes:
            return {
                "confirmed": False,
                "requires_confirmation": True,
                "pending_action": {
                    "action": "add_mr_discussion",
                    "project": proj,
                    "mr_iid": iid,
                    "file_path": path,
                    "new_line": position.get("new_line"),
                    "old_line": position.get("old_line"),
                    "draft": draft,
                    "body": text,
                },
            }
        return {"confirmed": True, **client.add_mr_discussion(proj, iid, text, position, draft)}

    return run_tool("add_mr_discussion", _run)
