"""get_mr_discussions: every discussion thread (inline and general) on an MR."""

from __future__ import annotations

from typing import Any, Dict, Optional

from lib.glab_client import get_client
from tools._common import require_iid, resolve_project, run_tool


def get_mr_discussions(mr_iid: int, project: Optional[str] = None) -> Dict[str, Any]:
    def _run() -> Dict[str, Any]:
        discussions = get_client().get_mr_discussions(resolve_project(project), require_iid(mr_iid))
        return {"count": len(discussions), "discussions": discussions}

    return run_tool("get_mr_discussions", _run)
