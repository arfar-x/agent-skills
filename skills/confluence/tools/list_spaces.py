"""list_spaces: enumerate every space visible to the authenticated user."""

from __future__ import annotations

from typing import Any, Dict

from lib.confluence_client import get_client
from tools._common import run_tool


def list_spaces(max_results: int = 100) -> Dict[str, Any]:
    """List spaces.

    Args:
        max_results: Safety cap on the number of spaces returned.

    Returns:
        ``{"count": N, "spaces": [...]}``.
    """

    def _run() -> Dict[str, Any]:
        client = get_client()
        spaces = client.list_spaces(max_results=max_results)
        return {"count": len(spaces), "spaces": [s.to_dict() for s in spaces]}

    return run_tool("list_spaces", _run)
