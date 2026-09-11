"""get_labels: list the labels currently on a page."""

from __future__ import annotations

from typing import Any, Dict

from lib.confluence_client import get_client
from tools._common import require_str, run_tool


def get_labels(page_id: str) -> Dict[str, Any]:
    """List a page's labels.

    Args:
        page_id: Content id of the page.

    Returns:
        ``{"page_id": "...", "labels": [...]}``.
    """

    def _run() -> Dict[str, Any]:
        key = require_str(str(page_id), "page_id")
        client = get_client()
        labels = client.get_labels(key)
        return {"page_id": key, "labels": labels}

    return run_tool("get_labels", _run)
