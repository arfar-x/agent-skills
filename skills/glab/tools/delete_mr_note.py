"""delete_mr_note: permanently delete a note from a merge request discussion.

Destructive write operation, gated the same way every write tool in this
repo is.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from lib.glab_client import get_client
from tools._common import require_iid, require_note_id, require_str, resolve_project, run_tool


def delete_mr_note(
    mr_iid: int,
    discussion_id: str,
    note_id: int,
    project: Optional[str] = None,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Permanently delete one note. Cannot be undone.

    Take both ids from ``get_mr_discussions``. Deleting a thread's first
    note leaves its replies in place. The note is fetched first, so the
    pending action shows exactly what will be deleted, and a wrong id
    fails before the gate.
    """

    def _run() -> Dict[str, Any]:
        proj = resolve_project(project)
        iid = require_iid(mr_iid)
        disc = require_str(discussion_id, "discussion_id")
        nid = require_note_id(note_id)
        client = get_client()
        current = client.get_mr_discussion_note(proj, iid, disc, nid)

        if not confirm and not client.config.auto_confirm_writes:
            return {
                "confirmed": False,
                "requires_confirmation": True,
                "pending_action": {
                    "action": "delete_mr_note",
                    "project": proj,
                    "mr_iid": iid,
                    "discussion_id": disc,
                    "note_id": nid,
                    "author": current["author"],
                    "body": current["body"],
                },
            }
        client.delete_mr_note(proj, iid, disc, nid)
        return {"confirmed": True, "deleted": True, "discussion_id": disc, "note_id": nid, "deleted_body": current["body"]}

    return run_tool("delete_mr_note", _run)
