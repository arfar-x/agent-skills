"""upload_attachment: attach a file to an issue -- content passed in, or a local file.

Write operation, gated the same way every write tool in this skill is:
refuses to execute without confirm=True unless JIRA_AUTO_CONFIRM_WRITES
is enabled. The file is validated, and described in the pending action,
before the gate so the user approves the real source and size.

A local file is accepted only from the directory the operator set in
AGENT_SKILLS_ATTACHMENT_DIR, never a hidden or secret-looking one (see
lib/attachment_files.py); otherwise the caller passes the content itself.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from lib.attachment_files import DEFAULT_MAX_BYTES, AttachmentFileError, describe_upload
from lib.jira_client import get_client
from tools._common import ToolInputError, require_str, run_tool


def upload_attachment(
    issue_key: str,
    file_path: Optional[str] = None,
    filename: Optional[str] = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
    confirm: bool = False,
    content: Optional[str] = None,
    content_base64: Optional[str] = None,
) -> Dict[str, Any]:
    """Attach a file to an issue: ``content``, ``content_base64`` or ``file_path``.

    Args:
        issue_key: Issue key, e.g. ``PAY-412``.
        file_path: Path of a local file to upload, inside
            AGENT_SKILLS_ATTACHMENT_DIR (relative paths are taken from it);
            refused when that is unset. Symlinks are followed and the
            resolved path is what gets reported and uploaded.
        filename: Name to give the attachment (default: the file's name;
            required with ``content``/``content_base64``).
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
            info = describe_upload(file_path, content, content_base64, filename, max_bytes)
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
                    **({"file_path": info["path"]} if "path" in info else {"source": "content"}),
                    "filename": info["filename"],
                    "size_bytes": info["size_bytes"],
                    "media_type": info["media_type"],
                },
            }
        attachments = client.upload_attachment(
            key, info.get("path"), info["filename"], content=content, content_base64=content_base64
        )
        return {"confirmed": True, "issue_key": key, "attachments": attachments}

    return run_tool("upload_attachment", _run)
