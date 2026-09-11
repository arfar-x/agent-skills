"""get_attachments: list a page's attachments (metadata only).

Read-only listing -- there is no attachment upload/download support in
this toolset (uploading is a multipart-form operation, a different
shape from every other call this client makes, and wasn't judged worth
the added surface for a first version).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from lib.confluence_client import get_client
from tools._common import require_str, run_tool


def get_attachments(page_id: str, max_results: Optional[int] = None) -> Dict[str, Any]:
    """List a page's attachments.

    Args:
        page_id: Content id of the page.
        max_results: Safety cap on the number of attachments returned.

    Returns:
        ``{"page_id": "...", "count": N, "attachments": [...]}``.
    """

    def _run() -> Dict[str, Any]:
        key = require_str(str(page_id), "page_id")
        client = get_client()
        attachments = client.get_attachments(key, max_results=max_results)
        return {"page_id": key, "count": len(attachments), "attachments": [a.to_dict() for a in attachments]}

    return run_tool("get_attachments", _run)
