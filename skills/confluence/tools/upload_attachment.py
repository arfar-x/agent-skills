"""upload_attachment: attach a local file to a page.

Write operation, gated the same way every write tool in this skill is:
refuses to execute without confirm=True unless CONFLUENCE_AUTO_CONFIRM_WRITES
is enabled. The file is validated, and described in the pending action,
before the gate so the user approves the real path and size. If the page
already has an attachment with that name, a new version replaces it, and
the pending action says so.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from lib.attachment_files import DEFAULT_MAX_BYTES, AttachmentFileError, describe_upload_file
from lib.confluence_client import get_client
from tools._common import ToolInputError, require_str, run_tool


def upload_attachment(
    page_id: str,
    file_path: str,
    filename: Optional[str] = None,
    comment: Optional[str] = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Attach a local file to a page.

    Args:
        page_id: Numeric page id.
        file_path: Path of the file to upload (symlinks are followed and
            the resolved path is what gets reported and uploaded).
        filename: Name to give the attachment (default: the file's name).
        comment: Optional version comment shown in the attachment history.
        max_bytes: Refuse files larger than this (default 50 MB).
        confirm: Must be ``True`` (or CONFLUENCE_AUTO_CONFIRM_WRITES=true)
            for the upload to actually happen.

    Returns:
        On success: ``{"confirmed": true, "page_id": ..., "attachment": {...},
        "replaced_existing": bool}``. When confirmation is required first:
        ``{"confirmed": false, "requires_confirmation": true,
        "pending_action": {...}}``.
    """

    def _run() -> Dict[str, Any]:
        pid = require_str(page_id, "page_id")
        try:
            info = describe_upload_file(file_path, filename, max_bytes)
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
                    "file_path": info["path"],
                    "filename": info["filename"],
                    "size_bytes": info["size_bytes"],
                    "media_type": info["media_type"],
                    "replaces_existing_attachment": existing is not None,
                    **({"comment": comment} if comment else {}),
                },
            }
        result = client.upload_attachment(pid, info["path"], info["filename"], comment)
        return {"confirmed": True, "page_id": pid, **result}

    return run_tool("upload_attachment", _run)
