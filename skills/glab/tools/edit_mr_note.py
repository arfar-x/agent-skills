"""edit_mr_note: replace the body of an existing note in a merge request discussion.

Write operation, gated the same way every write tool in this repo is.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from lib.glab_client import get_client
from tools._common import require_iid, require_note_id, require_str, resolve_project, run_tool


def edit_mr_note(
    mr_iid: int,
    discussion_id: str,
    note_id: int,
    body: str,
    project: Optional[str] = None,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Replace a note's body (GitLab Markdown) with ``body``.

    Works for a general note and an inline comment alike -- both live in a
    discussion (a general note is a single-note discussion). Take both ids
    from ``get_mr_discussions``. The note is fetched first, so the pending
    action shows its current body and author, and a wrong id fails before
    the gate.
    """

    def _run() -> Dict[str, Any]:
        proj = resolve_project(project)
        iid = require_iid(mr_iid)
        disc = require_str(discussion_id, "discussion_id")
        nid = require_note_id(note_id)
        text = require_str(body, "body")
        client = get_client()
        current = client.get_mr_discussion_note(proj, iid, disc, nid)

        if not confirm and not client.config.auto_confirm_writes:
            return {
                "confirmed": False,
                "requires_confirmation": True,
                "pending_action": {
                    "action": "edit_mr_note",
                    "project": proj,
                    "mr_iid": iid,
                    "discussion_id": disc,
                    "note_id": nid,
                    "author": current["author"],
                    "current_body": current["body"],
                    "new_body": text,
                },
            }
        return {"confirmed": True, "note": client.edit_mr_note(proj, iid, disc, nid, text)}

    return run_tool("edit_mr_note", _run)
