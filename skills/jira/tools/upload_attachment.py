"""upload_attachment: attach a local file to an issue.

Write operation, gated the same way every write tool in this skill is:
refuses to execute without confirm=True unless JIRA_AUTO_CONFIRM_WRITES
is enabled. The file is validated, and described in the pending action,
before the gate so the user approves the real path and size.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from lib.attachment_files import DEFAULT_MAX_BYTES, AttachmentFileError, describe_upload_file
from lib.jira_client import get_client
from tools._common import ToolInputError, require_str, run_tool


def upload_attachment(
    issue_key: str,
    file_path: str,
    filename: Optional[str] = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Attach a local file to an issue.

    Args:
        issue_key: Issue key, e.g. ``PAY-412``.
        file_path: Path of the file to upload (symlinks are followed and
            the resolved path is what gets reported and uploaded).
        filename: Name to give the attachment (default: the file's name).
        max_bytes: Refuse files larger than this (default 50 MB).
        confirm: Must be ``True`` (or JIRA_AUTO_CONFIRM_WRITES=true) for the
            upload to actually happen.

    Returns:
        On success: ``{"confirmed": true, "issue_key": ..., "attachments": [...]}``.
        When confirmation is required first: ``{"confirmed": false,
        "requires_confirmation": true, "pending_action": {...}}``.
    """

    def _run() -> Dict[str, Any]:
        key = require_str(issue_key, "issue_key")
        try:
            info = describe_upload_file(file_path, filename, max_bytes)
        except AttachmentFileError as exc:
            raise ToolInputError(str(exc)) from exc
        client = get_client()

        if not confirm and not client.config.auto_confirm_writes:
            return {
                "confirmed": False,
                "requires_confirmation": True,
                "pending_action": {
                    "action": "upload_attachment",
                    "issue_key": key,
                    "file_path": info["path"],
                    "filename": info["filename"],
                    "size_bytes": info["size_bytes"],
                    "media_type": info["media_type"],
                },
            }
        attachments = client.upload_attachment(key, info["path"], info["filename"])
        return {"confirmed": True, "issue_key": key, "attachments": attachments}

    return run_tool("upload_attachment", _run)
