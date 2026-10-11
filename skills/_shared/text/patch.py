"""Exact text replacement for partial edits of a stored document.

Used identically by any toolset that edits part of a text it reads back
from a remote service (a Jira description, a Confluence page's Markdown
source) instead of resending the whole text. Pure standard library.

A replacement is exact and unambiguous by default: the text to find must
occur exactly once, so an edit can never land somewhere the caller did
not mean. ``replace_all`` is the explicit opt-in for every occurrence.
"""

from __future__ import annotations

from typing import List, Sequence, Tuple


class PatchError(ValueError):
    """Raised when a requested edit cannot be applied exactly."""


def replace_text(text: str, find: str, replace: str, *, replace_all: bool = False) -> Tuple[str, int]:
    """Replace ``find`` with ``replace`` in ``text``.

    Returns the new text and the number of replacements made. Raises
    :class:`PatchError` if ``find`` is empty or missing, or occurs more
    than once without ``replace_all``.
    """
    if not find:
        raise PatchError("The text to find must not be empty.")
    count = text.count(find)
    if count == 0:
        raise PatchError(f"Text not found: {_preview(find)}")
    if count > 1 and not replace_all:
        raise PatchError(
            f"Text occurs {count} times, so the edit is ambiguous: {_preview(find)}. "
            "Include more surrounding text, or replace every occurrence explicitly."
        )
    return text.replace(find, replace), count


def replace_pairs(
    text: str,
    finds: Sequence[str],
    replaces: Sequence[str],
    *,
    replace_all: bool = False,
) -> Tuple[str, List[dict]]:
    """Apply ``(find, replace)`` pairs in order; all or nothing.

    Returns the new text and one ``{"find", "replace", "count"}`` record per
    pair. Raises :class:`PatchError` if the two lists differ in length or
    any single pair fails -- in which case nothing is applied.
    """
    if len(finds) != len(replaces):
        raise PatchError(
            f"Got {len(finds)} text(s) to find but {len(replaces)} replacement(s); pass them in pairs."
        )
    applied: List[dict] = []
    for find, replace in zip(finds, replaces):
        text, count = replace_text(text, find, replace, replace_all=replace_all)
        applied.append({"find": find, "replace": replace, "count": count})
    return text, applied


def _preview(value: str, limit: int = 80) -> str:
    flat = " ".join(value.split())
    return repr(flat if len(flat) <= limit else flat[: limit - 1] + "…")
