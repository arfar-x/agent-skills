"""Resolve a file line into the exact `position` GitLab requires for an inline comment.

GitLab rejects an inline discussion unless the position matches the diff:
an added line carries only ``new_line``, a removed line only ``old_line``,
and an unchanged context line both. Callers give a line number (and
optionally which side); this module parses the file's unified diff and
works out the rest, so nobody has to pass SHAs or guess line pairs.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Mapping, Optional

_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")


class PositionError(ValueError):
    """Raised when a requested line is not part of the MR diff."""


def _line_pairs(diff_text: str):
    """Yield ``(old_line, new_line)`` for every line shown in the diff.

    ``old_line`` is None for an added line, ``new_line`` is None for a
    removed one.
    """
    old = new = 0
    in_hunk = False
    for raw in diff_text.splitlines():
        m = _HUNK_RE.match(raw)
        if m:
            old, new = int(m.group(1)), int(m.group(2))
            in_hunk = True
            continue
        if not in_hunk or raw.startswith("\\"):
            continue
        if raw.startswith("+"):
            yield (None, new)
            new += 1
        elif raw.startswith("-"):
            yield (old, None)
            old += 1
        else:
            yield (old, new)
            old += 1
            new += 1


def resolve_position(
    file_diff: Mapping[str, Any],
    diff_refs: Mapping[str, str],
    *,
    new_line: Optional[int] = None,
    old_line: Optional[int] = None,
) -> Dict[str, Any]:
    """Build a GitLab ``position`` hash for one line of one file's diff.

    Args:
        file_diff: One entry of the MR diff: ``old_path``, ``new_path``, ``diff``.
        diff_refs: The MR's ``base_sha``/``start_sha``/``head_sha``.
        new_line: Line number on the new (head) side.
        old_line: Line number on the old (base) side.

    Raises:
        PositionError: If neither line is given, or the line is not in a hunk.
    """
    if new_line is None and old_line is None:
        raise PositionError("Provide new_line (added/unchanged line) or old_line (removed line).")

    match = None
    for old, new in _line_pairs(file_diff.get("diff") or ""):
        if new_line is not None and new == new_line and (old_line is None or old == old_line):
            match = (old, new)
            break
        if new_line is None and old == old_line:
            match = (old, new)
            break

    if match is None:
        wanted = f"new_line={new_line}" if new_line is not None else f"old_line={old_line}"
        raise PositionError(
            f"{wanted} is not part of the MR diff for {file_diff.get('new_path')} -- "
            "an inline comment is impossible there (only changed lines and their "
            "surrounding context are commentable)."
        )

    position: Dict[str, Any] = {
        "position_type": "text",
        "base_sha": diff_refs["base_sha"],
        "start_sha": diff_refs["start_sha"],
        "head_sha": diff_refs["head_sha"],
        "old_path": file_diff.get("old_path"),
        "new_path": file_diff.get("new_path"),
    }
    old, new = match
    if old is not None:
        position["old_line"] = old
    if new is not None:
        position["new_line"] = new
    return position
