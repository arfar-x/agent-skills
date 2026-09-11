"""get_comments: fetch every comment on a page."""

from __future__ import annotations

from typing import Any, Dict, Optional

from lib.confluence_client import get_client
from tools._common import require_str, run_tool


def get_comments(page_id: str, max_results: Optional[int] = None) -> Dict[str, Any]:
    """Fetch a page's comments.

    Args:
        page_id: Content id of the page.
        max_results: Safety cap on the number of comments returned.

    Returns:
        ``{"page_id": "...", "count": N, "comments": [...]}``.
    """

    def _run() -> Dict[str, Any]:
        key = require_str(str(page_id), "page_id")
        client = get_client()
        comments = client.get_comments(key, max_results=max_results)
        return {"page_id": key, "count": len(comments), "comments": [c.to_dict() for c in comments]}

    return run_tool("get_comments", _run)
