"""get_page_by_title: resolve a page by its space + exact title.

Confluence pages are commonly referred to by "the X page in the Y
space" rather than by their numeric content id -- this is the lookup
that turns that into a page (and its id) without the caller needing to
already know it.
"""

from __future__ import annotations

from typing import Any, Dict

from lib.confluence_client import get_client
from tools._common import require_str, run_tool


def get_page_by_title(space_key: str, title: str) -> Dict[str, Any]:
    """Look up a page by its space key and exact title.

    Args:
        space_key: Space key, e.g. ``"ENG"``.
        title: Exact page title (case-sensitive match against Confluence's
            own title index).

    Returns:
        ``{"page": {...}}`` if found, ``{"page": None}`` if no page in
        that space has that exact title.
    """

    def _run() -> Dict[str, Any]:
        key = require_str(space_key, "space_key")
        page_title = require_str(title, "title")
        client = get_client()
        page = client.get_page_by_title(key, page_title)
        return {"page": page.to_dict() if page else None}

    return run_tool("get_page_by_title", _run)
