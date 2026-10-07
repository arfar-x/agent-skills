"""list_branches: list a project's branches."""

from __future__ import annotations

from typing import Any, Dict, Optional

from lib.glab_client import get_client
from tools._common import resolve_project, run_tool


def list_branches(project: Optional[str] = None, search: Optional[str] = None, max_results: int = 50) -> Dict[str, Any]:
    def _run() -> Dict[str, Any]:
        branches = get_client().list_branches(resolve_project(project), search, max_results)
        return {"count": len(branches), "branches": branches}

    return run_tool("list_branches", _run)
