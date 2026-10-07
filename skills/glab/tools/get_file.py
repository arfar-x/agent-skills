"""get_file: read one file's content from a project at a ref."""

from __future__ import annotations

from typing import Any, Dict, Optional

from lib.glab_client import get_client
from tools._common import ToolInputError, require_str, resolve_project, run_tool


def get_file(
    file_path: str, ref: str, project: Optional[str] = None, max_bytes: int = 200_000
) -> Dict[str, Any]:
    def _run() -> Dict[str, Any]:
        if max_bytes <= 0:
            raise ToolInputError("'max_bytes' must be positive.")
        return {
            "file": get_client().get_file(
                resolve_project(project), require_str(file_path, "file_path"), require_str(ref, "ref"), max_bytes
            )
        }

    return run_tool("get_file", _run)
