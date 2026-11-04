"""resolve_discussion: mark a merge request discussion thread resolved (write). Resolving twice changes nothing."""

from __future__ import annotations

from typing import Any, Dict, Optional

from lib.glab_client import get_client
from tools._common import require_iid, require_str, resolve_project, run_tool


def resolve_discussion(
    mr_iid: int,
    discussion_id: str,
    project: Optional[str] = None,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Resolve a thread."""

    def _run() -> Dict[str, Any]:
        proj, iid, thread = resolve_project(project), require_iid(mr_iid), require_str(discussion_id, "discussion_id")
        client = get_client()
        if not confirm and not client.config.auto_confirm_writes:
            return {"confirmed": False, "requires_confirmation": True,
                    "pending_action": {"action": "resolve_discussion", "project": proj, "mr_iid": iid, "discussion_id": thread}}
        return {"confirmed": True, "discussion": client.resolve_discussion(proj, iid, thread, True)}

    return run_tool("resolve_discussion", _run)
