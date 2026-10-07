"""get_project: fetch a project's identity, default branch, and URL."""

from __future__ import annotations

from typing import Any, Dict, Optional

from lib.glab_client import get_client
from tools._common import resolve_project, run_tool


def get_project(project: Optional[str] = None) -> Dict[str, Any]:
    return run_tool("get_project", lambda: {"project": get_client().get_project(resolve_project(project))})
