"""Small stateless helpers shared across the Confluence client and tools.

Keeping these in one place avoids duplicating parsing/formatting logic
across tool modules (each tool should stay a thin wrapper).
"""

from __future__ import annotations

import html
import re
from typing import Any, Dict, Optional

#: Confluence "storage" representation is XHTML-based (e.g. ``<p>...</p>``,
#: ``<ac:structured-macro>...</ac:structured-macro>``) and, unlike Jira's
#: ADF-vs-wiki-markup split, is the one body representation both Confluence
#: Cloud and Server/Data Center accept and return -- so one converter
#: covers both, the same "one shape, two deployments" reasoning
#: `jira/lib/utils.py`'s `adf_to_plain_text` uses for its own split.
_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"[ \t]+")
_BLANK_LINES_RE = re.compile(r"\n\s*\n+")

#: Block-level storage-format tags whose closing tag should force a line
#: break in the plain-text output, so paragraphs/headings/list items don't
#: all run together on one line.
_BLOCK_CLOSE_RE = re.compile(
    r"</(p|h[1-6]|li|div|tr|br|ac:structured-macro)>", re.IGNORECASE
)


def storage_to_plain_text(storage_value: Optional[str]) -> str:
    """Best-effort conversion of Confluence storage-format XHTML into plain
    text for tool output. Not a full HTML/XHTML parser -- a fast, dependency-free
    strip good enough for an LLM to read page/comment content, not for
    re-rendering it. Writing a page always uses the real storage-format
    markup (see each write tool's docstring), never this function's output.
    """
    if not storage_value:
        return ""
    with_breaks = _BLOCK_CLOSE_RE.sub("\n\n", storage_value)
    text = _TAG_RE.sub("", with_breaks)
    text = html.unescape(text)
    text = _WHITESPACE_RE.sub(" ", text)
    text = _BLANK_LINES_RE.sub("\n\n", text)
    return "\n".join(line.strip() for line in text.split("\n")).strip()


def safe_get(mapping: Optional[Dict[str, Any]], *path: str, default: Any = None) -> Any:
    """Safely walk a chain of nested dict keys, returning ``default`` on any miss."""
    current: Any = mapping
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current if current is not None else default
