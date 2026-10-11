"""upload_attachment: attach a file to a page -- content passed in, or a local file.

Write operation, gated the same way every write tool in this skill is:
refuses to execute without confirm=True unless CONFLUENCE_AUTO_CONFIRM_WRITES
is enabled. The file is validated, and described in the pending action,
before the gate so the user approves the real source and size.

A local file is accepted only from the directory the operator set in
AGENT_SKILLS_ATTACHMENT_DIR, never a hidden or secret-looking one (see
lib/attachment_files.py); otherwise the caller passes the content itself. If the page
already has an attachment with that name, a new version replaces it, and
the pending action says so.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from lib.attachment_files import DEFAULT_MAX_BYTES, AttachmentFileError, describe_upload
from lib.confluence_client import get_client
from tools._common import ToolInputError, require_str, run_tool


def upload_attachment(
    page_id: str,
    file_path: Optional[str] = None,
    filename: Optional[str] = None,
    comment: Optional[str] = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
    confirm: bool = False,
    content: Optional[str] = None,
    content_base64: Optional[str] = None,
) -> Dict[str, Any]:
    """Attach a file to a page: ``content``, ``content_base64`` or ``file_path``.

    Args:
        page_id: Numeric page id.
        file_path: Path of a local file to upload, inside
            AGENT_SKILLS_ATTACHMENT_DIR (relative paths are taken from it);
            refused when that is unset. Symlinks are followed and the
            resolved path is what gets reported and uploaded.
        filename: Name to give the attachment (default: the file's name;
            required with ``content``/``content_base64``).
        comment: Optional version comment shown in the attachment history.
        max_bytes: Refuse files larger than this (default 50 MB).
        confirm: Must be ``True`` (or CONFLUENCE_AUTO_CONFIRM_WRITES=true)
            for the upload to actually happen.
        content: Text to upload as the file (UTF-8), instead of a path.
        content_base64: Bytes to upload as the file, base64-encoded.

    Returns:
        On success: ``{"confirmed": true, "page_id": ..., "attachment": {...},
        "replaced_existing": bool}``. When confirmation is required first:
        ``{"confirmed": false, "requires_confirmation": true,
        "pending_action": {...}}``.
    """

    def _run() -> Dict[str, Any]:
        pid = require_str(page_id, "page_id")
        try:
            info = describe_upload(file_path, content, content_base64, filename, max_bytes)
        except AttachmentFileError as exc:
            raise ToolInputError(str(exc)) from exc
        client = get_client()

        if not confirm and not client.config.auto_confirm_writes:
            existing = client.find_attachment_by_name(pid, info["filename"])
            return {
                "confirmed": False,
                "requires_confirmation": True,
                "pending_action": {
                    "action": "upload_attachment",
                    "page_id": pid,
                    **({"file_path": info["path"]} if "path" in info else {"source": "content"}),
                    "filename": info["filename"],
                    "size_bytes": info["size_bytes"],
                    "media_type": info["media_type"],
                    "replaces_existing_attachment": existing is not None,
                    **({"comment": comment} if comment else {}),
                },
            }
        result = client.upload_attachment(
            pid, info.get("path"), info["filename"], comment, content=content, content_base64=content_base64
        )
        return {"confirmed": True, "page_id": pid, **result}

    return run_tool("upload_attachment", _run)
