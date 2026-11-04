"""reply_discussion: add a reply to a merge request discussion thread (write).

Idempotent by ``marker``: when a note in the thread already carries it, nothing is posted.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from lib.glab_client import get_client
from tools._common import require_iid, require_str, resolve_project, run_tool


def reply_discussion(
    mr_iid: int,
    discussion_id: str,
    body: str,
    project: Optional[str] = None,
    marker: Optional[str] = None,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Reply in a thread. ``marker`` (a unique line appended to the body) makes a repeat a no-op."""

    def _run() -> Dict[str, Any]:
        proj, iid = resolve_project(project), require_iid(mr_iid)
        thread, text = require_str(discussion_id, "discussion_id"), require_str(body, "body")
        line = marker.strip() if isinstance(marker, str) and marker.strip() else None
        client = get_client()
        full = f"{text}\n\n{line}" if line else text
        if not confirm and not client.config.auto_confirm_writes:
            return {"confirmed": False, "requires_confirmation": True,
                    "pending_action": {"action": "reply_discussion", "project": proj, "mr_iid": iid,
                                       "discussion_id": thread, "body": full}}
        if line:
            found = client.get_mr_discussion(proj, iid, thread)
            if any(line in (n.get("body") or "") for n in found.get("notes", [])):
                return {"confirmed": True, "skipped": "exists"}
        return {"confirmed": True, "note": client.reply_discussion(proj, iid, thread, full)}

    return run_tool("reply_discussion", _run)
