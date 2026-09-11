"""get_space: fetch one space's identity and description."""

from __future__ import annotations

from typing import Any, Dict

from lib.confluence_client import get_client
from tools._common import require_str, run_tool


def get_space(space_key: str) -> Dict[str, Any]:
    """Fetch a single space.

    Args:
        space_key: Space key, e.g. ``"ENG"``.

    Returns:
        ``{"space": {...}}``.
    """

    def _run() -> Dict[str, Any]:
        key = require_str(space_key, "space_key")
        client = get_client()
        space = client.get_space(key)
        return {"space": space.to_dict()}

    return run_tool("get_space", _run)
