"""my_pages: pages authored by the current user, most recently modified first."""

from __future__ import annotations

from typing import Any, Dict, Optional

from lib.confluence_client import get_client
from tools._common import run_tool


def my_pages(max_results: Optional[int] = 50) -> Dict[str, Any]:
    """List pages the current user created, most recently modified first.

    Args:
        max_results: Safety cap on the number of pages returned.

    Returns:
        ``{"count": N, "pages": [...]}``.
    """

    def _run() -> Dict[str, Any]:
        client = get_client()
        pages = client.my_pages(max_results=max_results)
        return {"count": len(pages), "pages": [p.to_dict() for p in pages]}

    return run_tool("my_pages", _run)
