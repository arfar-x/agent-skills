"""patch_page: change part of a page through its Markdown source.

For a page written with ``body_markdown`` and a source block (see
``lib/markdown_storage.py``): reads the page's Markdown back, applies only
the requested edits -- exact text replacements, whole-section replacements
-- renders the page again and writes it, and adds/removes labels in the
same call. The caller sends the change, never the whole page.

Write operation, gated the same way every write tool in this skill is.
The confirmation step shows a unified diff of the Markdown, so what is
approved is exactly what changes. The write is pinned to the version that
was read: if someone edited the page in between, Confluence rejects it
(409) instead of silently overwriting their edit.
"""

from __future__ import annotations

import difflib
from typing import Any, Dict, List, Optional

from lib.confluence_client import get_client
from lib.markdown_patch import PatchError, apply_patch
from lib.markdown_storage import extract_source, render_page
from tools._common import ToolInputError, require_str, run_tool

#: Upper bound on the diff shown for confirmation, so a large section
#: rewrite cannot flood the approval prompt.
_MAX_DIFF_LINES = 200


def patch_page(
    page_id: str,
    find: Optional[List[str]] = None,
    replace: Optional[List[str]] = None,
    replace_all: bool = False,
    section: Optional[List[str]] = None,
    section_markdown: Optional[List[str]] = None,
    add_labels: Optional[List[str]] = None,
    remove_labels: Optional[List[str]] = None,
    title: Optional[str] = None,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Edit part of a page via its Markdown source block.

    Args:
        page_id: Target page id.
        find: Exact texts to find in the page's Markdown, paired in order
            with ``replace``. Each must occur exactly once unless
            ``replace_all``.
        replace: Replacement for each ``find``.
        replace_all: Replace every occurrence of each ``find``.
        section: Headings (text, with or without ``#``s) whose content to
            replace, paired in order with ``section_markdown``. The heading
            line itself is kept.
        section_markdown: New Markdown content for each ``section``.
        add_labels: Labels to add.
        remove_labels: Labels to remove.
        title: New title (omit to leave unchanged).
        confirm: Must be ``True`` (or CONFLUENCE_AUTO_CONFIRM_WRITES=true)
            for the change to actually be written.

    Returns:
        On success: ``{"confirmed": true, "page": {...}, "edits": [...],
        "labels": [...]}``. When confirmation is required first:
        ``{"confirmed": false, "requires_confirmation": true,
        "pending_action": {..., "diff": "..."}}``. A page without a source
        block is an error: write it once with ``update_page --body_markdown``.
    """

    def _run() -> Dict[str, Any]:
        key = require_str(str(page_id), "page_id")
        finds, replaces = list(find or []), list(replace or [])
        headings, bodies = list(section or []), list(section_markdown or [])
        to_add = _clean(add_labels)
        to_remove = _clean(remove_labels)
        if not (finds or headings or to_add or to_remove or title):
            raise ToolInputError(
                "Nothing to change: pass find/replace, section/section_markdown, "
                "add_labels/remove_labels or title."
            )
        if set(to_add) & set(to_remove):
            raise ToolInputError(f"Labels both added and removed: {sorted(set(to_add) & set(to_remove))}")

        client = get_client()
        current = client.get_page_storage(key)

        new_markdown: Optional[str] = None
        edits: List[dict] = []
        diff = ""
        if finds or replaces or headings or bodies:
            source = extract_source(current["body_storage"])
            if source is None:
                raise ToolInputError(
                    "This page has no Markdown source block, so it can't be patched. "
                    "Write it once with update_page --body_markdown (keeping a source block), "
                    "then patch it."
                )
            markdown, source_title = source
            try:
                new_markdown, edits = apply_patch(
                    markdown,
                    finds=finds,
                    replaces=replaces,
                    replace_all=replace_all,
                    section_headings=headings,
                    section_bodies=bodies,
                )
            except PatchError as exc:
                raise ToolInputError(str(exc)) from exc
            diff = _diff(markdown, new_markdown)

        if not confirm and not client.config.auto_confirm_writes:
            return {
                "confirmed": False,
                "requires_confirmation": True,
                "pending_action": {
                    "action": "patch_page",
                    "page_id": key,
                    "page_title": current["title"],
                    "version": current["version"],
                    "title": title,
                    "edits": edits,
                    "diff": diff,
                    "add_labels": to_add,
                    "remove_labels": to_remove,
                },
            }

        page: Dict[str, Any] = {"id": key, "title": current["title"], "version": current["version"], "url": current["url"]}
        if new_markdown is not None or title:
            body = render_page(new_markdown, source_title) if new_markdown is not None else None
            updated = client.update_page(
                key, title=title, body_storage=body, version=current["version"] + 1
            )
            page = updated.to_dict()

        labels = list(current["labels"])
        if to_add:
            labels = client.add_labels(key, to_add)
        for name in to_remove:
            if name in labels or name in current["labels"]:
                client.remove_label(key, name)
            labels = [existing for existing in labels if existing != name]

        return {"confirmed": True, "page": page, "edits": edits, "labels": labels}

    return run_tool("patch_page", _run)


def _clean(labels: Optional[List[str]]) -> List[str]:
    return list(dict.fromkeys(name.strip() for name in labels or [] if name and name.strip()))


def _diff(before: str, after: str) -> str:
    lines = list(
        difflib.unified_diff(
            before.splitlines(), after.splitlines(), "before", "after", lineterm="", n=1
        )
    )
    if len(lines) > _MAX_DIFF_LINES:
        lines = lines[:_MAX_DIFF_LINES] + [f"... ({len(lines) - _MAX_DIFF_LINES} more diff lines)"]
    return "\n".join(lines)
