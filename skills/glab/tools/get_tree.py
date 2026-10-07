"""get_tree: list files/directories in a project's repository at a ref."""

from __future__ import annotations

from typing import Any, Dict, Optional

from lib.glab_client import get_client
from tools._common import resolve_project, run_tool


def get_tree(
    project: Optional[str] = None,
    path: Optional[str] = None,
    ref: Optional[str] = None,
    recursive: bool = False,
    max_results: int = 200,
) -> Dict[str, Any]:
    def _run() -> Dict[str, Any]:
        entries = get_client().get_tree(resolve_project(project), path, ref, recursive, max_results)
        return {"count": len(entries), "entries": entries}

    return run_tool("get_tree", _run)
