"""Partial edits of a Markdown document: exact text and whole sections.

Pure functions over a page's Markdown source (see
:mod:`lib.markdown_storage`). Every edit is exact or it fails -- nothing is
guessed -- and a sequence of edits is all or nothing.
"""

from __future__ import annotations

import re
from typing import List, Optional, Sequence, Tuple

from lib.text_patch import PatchError, replace_pairs

__all__ = ["PatchError", "apply_patch", "replace_section"]

_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")


def replace_section(markdown: str, heading: str, body: str) -> str:
    """Replace the content under ``heading``, keeping the heading line.

    ``heading`` is the heading's text, with or without its leading ``#``s.
    The section runs to the next heading of the same or a higher level.
    Headings inside fenced code blocks are ignored. Raises
    :class:`PatchError` if the heading is missing or occurs more than once.
    """
    wanted = _normalize(heading)
    if not wanted:
        raise PatchError("The section heading must not be empty.")
    lines = markdown.split("\n")
    headings = _headings(lines)
    matches = [(index, level) for index, level, text in headings if _normalize(text) == wanted]
    if not matches:
        raise PatchError(f"Section heading not found: {heading!r}")
    if len(matches) > 1:
        raise PatchError(f"Section heading occurs {len(matches)} times, so the edit is ambiguous: {heading!r}")

    start, level = matches[0]
    end = len(lines)
    for index, other_level, _ in headings:
        if index > start and other_level <= level:
            end = index
            break

    new_body = body.strip("\n")
    replacement = [lines[start], ""] + (new_body.split("\n") + [""] if new_body else [])
    return "\n".join(lines[:start] + replacement + lines[end:])


def apply_patch(
    markdown: str,
    *,
    finds: Sequence[str] = (),
    replaces: Sequence[str] = (),
    replace_all: bool = False,
    section_headings: Sequence[str] = (),
    section_bodies: Sequence[str] = (),
) -> Tuple[str, List[dict]]:
    """Apply text replacements, then section replacements, in order.

    Returns the new Markdown and one record per edit. Raises
    :class:`PatchError` if any edit fails, before anything is applied.
    """
    if len(section_headings) != len(section_bodies):
        raise PatchError(
            f"Got {len(section_headings)} section heading(s) but {len(section_bodies)} "
            "section body/bodies; pass them in pairs."
        )
    text, applied = replace_pairs(markdown, list(finds), list(replaces), replace_all=replace_all)
    records: List[dict] = [{"edit": "replace_text", **record} for record in applied]
    for heading, body in zip(section_headings, section_bodies):
        text = replace_section(text, heading, body)
        records.append({"edit": "replace_section", "heading": heading})
    return text, records


def _normalize(heading: Optional[str]) -> str:
    return " ".join((heading or "").strip().lstrip("#").split()).strip()


def _headings(lines: List[str]) -> List[Tuple[int, int, str]]:
    found: List[Tuple[int, int, str]] = []
    fence: Optional[str] = None
    for index, line in enumerate(lines):
        marker = _FENCE.match(line)
        if marker:
            token = marker.group(1)[0] * 3
            if fence is None:
                fence = token
            elif token == fence:
                fence = None
            continue
        if fence is not None:
            continue
        match = _HEADING.match(line)
        if match:
            found.append((index, len(match.group(1)), match.group(2)))
    return found
