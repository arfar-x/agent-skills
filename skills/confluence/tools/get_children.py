"""get_children: list a page's direct child pages."""

from __future__ import annotations

from typing import Any, Dict, Optional

from lib.confluence_client import get_client
from tools._common import require_str, run_tool


def get_children(page_id: str, max_results: Optional[int] = None) -> Dict[str, Any]:
    """List a page's direct children.

    Args:
        page_id: Content id of the parent page.
        max_results: Safety cap on the number of child pages returned.

    Returns:
        ``{"page_id": "...", "count": N, "children": [...]}``.
    """

    def _run() -> Dict[str, Any]:
        key = require_str(str(page_id), "page_id")
        client = get_client()
        children = client.get_children(key, max_results=max_results)
        return {"page_id": key, "count": len(children), "children": [c.to_dict() for c in children]}

    return run_tool("get_children", _run)
