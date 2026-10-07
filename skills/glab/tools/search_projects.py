"""search_projects: find projects by name/path fragment."""

from __future__ import annotations

from typing import Any, Dict

from lib.glab_client import get_client
from tools._common import require_str, run_tool


def search_projects(search: str, membership: bool = False, max_results: int = 20) -> Dict[str, Any]:
    def _run() -> Dict[str, Any]:
        projects = get_client().search_projects(require_str(search, "search"), membership, max_results)
        return {"count": len(projects), "projects": projects}

    return run_tool("search_projects", _run)
