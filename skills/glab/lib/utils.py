"""Small helpers shared by the client and tools."""

from __future__ import annotations

from typing import Any, Optional


def safe_get(obj: Any, *keys: Any, default: Optional[Any] = None) -> Any:
    """Walk nested dicts/lists, returning ``default`` on any miss."""
    cur = obj
    for key in keys:
        try:
            cur = cur[key]
        except (KeyError, IndexError, TypeError):
            return default
        if cur is None:
            return default
    return cur
