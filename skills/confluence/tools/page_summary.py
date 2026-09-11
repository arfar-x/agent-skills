"""page_summary: retrieve everything about a page as one JSON document.

Thin tool: fans out to the shared ConfluenceClient for the page, its
comments, attachments, labels, and child pages, and returns them
combined. No prose summarization happens here -- the LLM produces the
human summary from this JSON. The direct analog of
``jira/tools/issue_summary.py``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from lib.confluence_client import get_client
from tools._common import ToolInputError, require_str, run_tool

_VALID_SECTIONS = {"page", "comments", "attachments", "labels", "children"}


def page_summary(page_id: str, sections: Optional[List[str]] = None) -> Dict[str, Any]:
    """Return a single JSON document combining a page's full context.

    Args:
        page_id: Content id of the page.
        sections: Which parts to fetch and return, a subset of
            ``{"page", "comments", "attachments", "labels", "children"}``.
            Defaults to all -- pass a subset (e.g. ``["page"]``) to skip
            fetching and returning the rest when you only need current
            content.

    Returns:
        ``{"page": {...}, "comments": [...], "attachments": [...],
           "labels": [...], "children": [...]}``, containing only the
        requested ``sections``.
    """

    def _run() -> Dict[str, Any]:
        key = require_str(str(page_id), "page_id")
        wanted = set(sections) if sections is not None else set(_VALID_SECTIONS)
        unknown = wanted - _VALID_SECTIONS
        if unknown:
            raise ToolInputError(
                f"Unknown section(s) {sorted(unknown)}. Valid sections: {sorted(_VALID_SECTIONS)}."
            )

        client = get_client()
        result: Dict[str, Any] = {}
        if "page" in wanted:
            result["page"] = client.get_page(key).to_dict()
        if "comments" in wanted:
            result["comments"] = [c.to_dict() for c in client.get_comments(key)]
        if "attachments" in wanted:
            result["attachments"] = [a.to_dict() for a in client.get_attachments(key)]
        if "labels" in wanted:
            result["labels"] = client.get_labels(key)
        if "children" in wanted:
            result["children"] = [c.to_dict() for c in client.get_children(key)]
        return result

    return run_tool("page_summary", _run)
