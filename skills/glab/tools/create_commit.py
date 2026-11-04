"""create_commit: commit file changes to a branch, creating the branch from another when it does not exist (write).

Idempotent by ``marker``: when a commit on the branch already carries the marker line in its message, nothing is committed
and that commit is returned, so a run that is resumed after a crash cannot commit twice.
"""

from __future__ import annotations

import base64
import binascii
import json
from typing import Any, Dict, List, Optional, Union

from lib.glab_client import get_client
from tools._common import ToolInputError, require_str, resolve_project, run_tool

_ACTIONS = {"create", "update", "delete", "move", "chmod"}
MAX_ACTIONS = 500


def _actions(raw: Union[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            raise ToolInputError("'actions' must be a JSON list of file actions.") from None
    if not isinstance(raw, list) or not raw or len(raw) > MAX_ACTIONS:
        raise ToolInputError(f"'actions' must be a list of 1 to {MAX_ACTIONS} file actions.")
    out: List[Dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict) or item.get("action") not in _ACTIONS:
            raise ToolInputError("each action needs an 'action' of: " + ", ".join(sorted(_ACTIONS)) + ".")
        path = item.get("file_path")
        if not isinstance(path, str) or not path or path.startswith("/") or ".." in path.split("/"):
            raise ToolInputError("each action needs a relative 'file_path' inside the repository.")
        built: Dict[str, Any] = {"action": item["action"], "file_path": path}
        if item["action"] in ("create", "update"):
            if "content_base64" in item:
                try:
                    base64.b64decode(item["content_base64"], validate=True)
                except (binascii.Error, ValueError):
                    raise ToolInputError(f"'content_base64' of {path} is not valid base64.") from None
                built.update(content=item["content_base64"], encoding="base64")
            elif isinstance(item.get("content"), str):
                built["content"] = item["content"]
            else:
                raise ToolInputError(f"{path}: give 'content' or 'content_base64'.")
        if item["action"] == "move":
            if not isinstance(item.get("previous_path"), str):
                raise ToolInputError(f"{path}: a move needs 'previous_path'.")
            built["previous_path"] = item["previous_path"]
        out.append(built)
    return out


def create_commit(
    branch: str,
    message: str,
    actions: Union[str, List[Dict[str, Any]]],
    project: Optional[str] = None,
    start_branch: Optional[str] = None,
    marker: Optional[str] = None,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Commit ``actions`` (a JSON list of {action, file_path, content|content_base64}) to ``branch``.

    ``start_branch`` is where a new branch starts from. ``marker`` is a unique line added to the message; a commit already
    carrying it is returned instead of making another.
    """

    def _run() -> Dict[str, Any]:
        proj, target = resolve_project(project), require_str(branch, "branch")
        text = require_str(message, "message")
        file_actions = _actions(actions)
        line = marker.strip() if isinstance(marker, str) and marker.strip() else None
        client = get_client()
        full = f"{text}\n\n{line}" if line else text
        if not confirm and not client.config.auto_confirm_writes:
            return {"confirmed": False, "requires_confirmation": True,
                    "pending_action": {"action": "create_commit", "project": proj, "branch": target, "start_branch": start_branch,
                                       "message": full, "files": [a["file_path"] for a in file_actions]}}
        if line:
            existing = client.find_commit_with_marker(proj, target, line)
            if existing is not None:
                return {"confirmed": True, "skipped": "exists",
                        "commit": {"id": existing.get("id"), "short_id": existing.get("short_id"), "title": existing.get("title")}}
        return {"confirmed": True, "commit": client.create_commit(proj, target, start_branch, full, file_actions)}

    return run_tool("create_commit", _run)
