"""list_mrs: list merge requests, in one project or instance-wide."""

from __future__ import annotations

from typing import Any, Dict, Optional

from lib.glab_client import get_client
from tools._common import run_tool


def list_mrs(
    project: Optional[str] = None,
    state: str = "opened",
    scope: str = "all",
    reviewer_me: bool = False,
    search: Optional[str] = None,
    max_results: int = 20,
) -> Dict[str, Any]:
    """``project`` is optional here on purpose: omitted (and no
    GITLAB_DEFAULT_PROJECT), the listing is instance-wide."""

    def _run() -> Dict[str, Any]:
        client = get_client()
        proj = (project or "").strip() or client.config.default_project
        mrs = client.list_mrs(proj, state, scope, reviewer_me, search, max_results)
        return {"count": len(mrs), "merge_requests": mrs}

    return run_tool("list_mrs", _run)
