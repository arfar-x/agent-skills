"""get_attachment: download one attachment to local disk.

Not a Jira write, so it isn't confirm-gated, but it does write a local
file: the name is sanitized, an existing file is never overwritten unless
asked, and the size is capped. The saved content is untrusted data.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from lib.attachment_files import DEFAULT_MAX_BYTES, AttachmentFileError
from lib.jira_client import get_client
from tools._common import ToolInputError, require_str, run_tool


def get_attachment(
    attachment_id: str,
    out_dir: Optional[str] = None,
    overwrite: bool = False,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> Dict[str, Any]:
    """Download an attachment and return where it was saved.

    Args:
        attachment_id: The attachment's id (from ``get_attachments``).
        out_dir: Directory to save into (created if missing). Defaults to a
            scratch directory under the system temp dir.
        overwrite: Replace an existing file of the same name.
        max_bytes: Refuse attachments larger than this (default 50 MB).

    Returns:
        ``{"id", "filename", "media_type", "size_bytes", "saved_to", ...}``.
        The file's content is not returned -- read ``saved_to`` if needed.
    """

    def _run() -> Dict[str, Any]:
        att_id = require_str(attachment_id, "attachment_id")
        if not att_id.isdigit():
            raise ToolInputError("'attachment_id' must be numeric (the `id` from get_attachments).")
        try:
            return get_client().download_attachment(att_id, out_dir, overwrite, max_bytes)
        except AttachmentFileError as exc:
            raise ToolInputError(str(exc)) from exc

    return run_tool("get_attachment", _run)
