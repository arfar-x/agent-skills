"""get_archive: the repository at a ref as a base64 tar.gz (read).

Refused above ``max_mb`` so one call cannot exhaust memory.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from lib.glab_client import get_client
from tools._common import ToolInputError, require_str, resolve_project, run_tool


def get_archive(ref: str, project: Optional[str] = None, max_mb: int = 50) -> Dict[str, Any]:
    """Download the repository at ``ref`` (branch, tag or commit) as a tar.gz, base64 encoded.

    Returns ``{"ref", "sha", "size", "format": "tar.gz", "content_base64"}``.
    """

    def _run() -> Dict[str, Any]:
        proj, name = resolve_project(project), require_str(ref, "ref")
        if not isinstance(max_mb, int) or isinstance(max_mb, bool) or not 1 <= max_mb <= 500:
            raise ToolInputError("'max_mb' must be a whole number from 1 to 500.")
        return get_client().get_archive(proj, name, max_mb * (1 << 20))

    return run_tool("get_archive", _run)
