"""get_mr: fetch one merge request's details."""

from __future__ import annotations

from typing import Any, Dict, Optional

from lib.glab_client import get_client
from tools._common import require_iid, resolve_project, run_tool


def get_mr(mr_iid: int, project: Optional[str] = None) -> Dict[str, Any]:
    return run_tool(
        "get_mr",
        lambda: {"merge_request": get_client().get_mr(resolve_project(project), require_iid(mr_iid))},
    )
