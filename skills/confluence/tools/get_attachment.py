"""get_attachment: download one page attachment to local disk.

Not a Confluence write, so it isn't confirm-gated, but it does write a
local file: the name is sanitized, an existing file is never overwritten
unless asked, and the size is capped. The saved content is untrusted data.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from lib.attachment_files import DEFAULT_MAX_BYTES, AttachmentFileError
from lib.confluence_client import get_client
from tools._common import ToolInputError, require_str, run_tool


def get_attachment(
    attachment_id: str,
    out_dir: Optional[str] = None,
    overwrite: bool = False,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> Dict[str, Any]:
    """Download an attachment and return where it was saved.

    Args:
        attachment_id: The attachment's content id (from ``get_attachments``,
            e.g. ``"att12345"`` on Cloud or a number on Server/Data Center).
        out_dir: Directory to save into (created if missing). Defaults to a
            scratch directory under the system temp dir.
        overwrite: Replace an existing file of the same name.
        max_bytes: Refuse attachments larger than this (default 50 MB).

    Returns:
        ``{"id", "title", "media_type", "file_size", "url", "saved_to",
        "size_bytes"}``. The file's content is not returned -- read
        ``saved_to`` if needed.
    """

    def _run() -> Dict[str, Any]:
        att_id = require_str(attachment_id, "attachment_id")
        try:
            return get_client().get_attachment(att_id, out_dir, overwrite, max_bytes)
        except AttachmentFileError as exc:
            raise ToolInputError(str(exc)) from exc

    return run_tool("get_attachment", _run)
