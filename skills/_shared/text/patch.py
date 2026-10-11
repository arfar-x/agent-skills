"""Exact text replacement for partial edits of a stored document.

Used identically by any toolset that edits part of a text it reads back
from a remote service (a Jira description, a Confluence page's Markdown
source) instead of resending the whole text. Pure standard library.

A replacement is exact and unambiguous by default: the text to find must
occur exactly once, so an edit can never land somewhere the caller did
not mean. ``replace_all`` is the explicit opt-in for every occurrence.

When the exact text isn't there, matching falls back to ignoring what a
writer (or a model) cannot see or reliably reproduce: spacing between
words -- spaces, line breaks, and zero-width (non-)joiners, which Persian
text uses interchangeably -- direction marks, and the Arabic and Persian
forms of yeh and kaf. The same uniqueness rule applies, and the
replacement covers the original text span.
"""

from __future__ import annotations

import re
from typing import List, Sequence, Tuple

#: Characters dropped before a lenient match: zero-width (non-)joiners,
#: directional marks, byte-order mark, soft hyphen.
_INVISIBLE = {"\u200c", "\u200d", "\u200e", "\u200f", "\ufeff", "\u00ad"}
#: Letters folded to one form before a lenient match: Arabic yeh/kaf and
#: alef maksura to their Persian forms.
_FOLD = {"\u064a": "\u06cc", "\u0649": "\u06cc", "\u0643": "\u06a9"}


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
    if count:
        _check_count(count, find, replace_all)
        return text.replace(find, replace), count

    spans = _lenient_spans(text, find)
    if not spans:
        raise PatchError(f"Text not found: {_preview(find)}")
    _check_count(len(spans), find, replace_all)
    for start, end in reversed(spans):
        text = text[:start] + replace + text[end:]
    return text, len(spans)


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


def _check_count(count: int, find: str, replace_all: bool) -> None:
    if count > 1 and not replace_all:
        raise PatchError(
            f"Text occurs {count} times, so the edit is ambiguous: {_preview(find)}. "
            "Include more surrounding text, or replace every occurrence explicitly."
        )


def _normalize(text: str) -> Tuple[str, List[int]]:
    """Normalized text plus, for each of its characters, the index of the
    original character it came from."""
    chars: List[str] = []
    origin: List[int] = []
    for index, char in enumerate(text):
        if char in _INVISIBLE or char.isspace():
            continue
        chars.append(_FOLD.get(char, char))
        origin.append(index)
    return "".join(chars), origin


def _lenient_spans(text: str, find: str) -> List[Tuple[int, int]]:
    """Original-text ``(start, end)`` spans of non-overlapping lenient matches."""
    needle, _ = _normalize(find)
    if not needle:
        return []
    haystack, origin = _normalize(text)
    spans: List[Tuple[int, int]] = []
    for match in re.finditer(re.escape(needle), haystack):
        start = origin[match.start()]
        end = origin[match.end() - 1] + 1
        spans.append((start, end))
    return spans
