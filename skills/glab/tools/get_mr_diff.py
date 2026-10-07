"""get_mr_diff: per-file unified diffs of a merge request."""

from __future__ import annotations

from typing import Any, Dict, Optional

from lib.glab_client import get_client
from tools._common import require_iid, resolve_project, run_tool


def get_mr_diff(mr_iid: int, project: Optional[str] = None, file_path: Optional[str] = None) -> Dict[str, Any]:
    def _run() -> Dict[str, Any]:
        files = get_client().get_mr_diff(resolve_project(project), require_iid(mr_iid), file_path)
        return {"count": len(files), "files": files}

    return run_tool("get_mr_diff", _run)
