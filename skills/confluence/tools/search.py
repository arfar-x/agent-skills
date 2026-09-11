"""search: run an arbitrary CQL query and return structured page data.

Thin tool: validates the CQL is non-empty, delegates to the shared
ConfluenceClient, and returns page JSON. Query construction/interpretation
is the LLM's responsibility; this tool never rewrites or infers CQL.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from lib.confluence_client import get_client
from tools._common import require_str, run_tool


def search(
    cql: str,
    max_results: int = 50,
    include_body: bool = False,
) -> Dict[str, Any]:
    """Run a CQL query and return matching pages.

    Args:
        cql: A valid CQL query string, e.g.
            ``"space = ENG AND type = page AND text ~ 'onboarding'"``.
        max_results: Safety cap on the number of pages returned.
        include_body: When true, also fetch and return each result's
            ``body_plain_text`` -- off by default since page bodies are
            often the single largest field; a bulk search should ask for
            content explicitly, not by default.

    Returns:
        ``{"cql": "...", "count": N, "pages": [...]}``.
    """

    def _run() -> Dict[str, Any]:
        query = require_str(cql, "cql")
        client = get_client()
        expand: Optional[List[str]] = ["body.storage", "space", "version"] if include_body else None
        pages = client.search(query, max_results=max_results, expand=expand)
        return {"cql": query, "count": len(pages), "pages": [p.to_dict() for p in pages]}

    return run_tool("search", _run)
