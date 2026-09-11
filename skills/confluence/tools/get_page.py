"""get_page: fetch a single page by its content id."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from lib.confluence_client import get_client
from tools._common import require_str, run_tool


def get_page(page_id: str, expand: Optional[List[str]] = None) -> Dict[str, Any]:
    """Fetch a page's current content and metadata.

    Args:
        page_id: Content id of the page, e.g. ``"12345678"``.
        expand: Optional list of raw Confluence expand parameters. Omit
            for the default set (body, version, space, ancestors, history).

    Returns:
        ``{"page": {...}}``.
    """

    def _run() -> Dict[str, Any]:
        page_id_str = require_str(str(page_id), "page_id")
        client = get_client()
        page = client.get_page(page_id_str, expand=expand)
        return {"page": page.to_dict()}

    return run_tool("get_page", _run)
