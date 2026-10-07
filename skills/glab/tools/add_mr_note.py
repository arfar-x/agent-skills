"""add_mr_note: post a general (non-inline) comment on a merge request.

Write operation, gated the same way every write tool in this repo is.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from lib.glab_client import get_client
from tools._common import require_iid, require_str, resolve_project, run_tool


def add_mr_note(
    mr_iid: int,
    body: str,
    project: Optional[str] = None,
    draft: bool = False,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Post a general MR comment (GitLab Markdown).

    With ``draft=True`` it is saved as a draft note, visible only to the
    token's user until they submit their review in GitLab's UI.
    """

    def _run() -> Dict[str, Any]:
        proj = resolve_project(project)
        iid = require_iid(mr_iid)
        text = require_str(body, "body")
        client = get_client()

        if not confirm and not client.config.auto_confirm_writes:
            return {
                "confirmed": False,
                "requires_confirmation": True,
                "pending_action": {"action": "add_mr_note", "project": proj, "mr_iid": iid, "draft": draft, "body": text},
            }
        return {"confirmed": True, **client.add_mr_note(proj, iid, text, draft)}

    return run_tool("add_mr_note", _run)
