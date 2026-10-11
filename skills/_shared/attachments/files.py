"""Local-file handling for attachment upload and download.

Used identically by any toolset that moves attachments between a remote
service and the local disk (Jira and Confluence today). Pure standard
library, no HTTP: each toolset's client does its own requests and calls
these helpers for everything that touches the filesystem, so the safety
rules below live in one place.

* A downloaded file's name comes from the remote service, so it is
  untrusted: :func:`safe_filename` reduces it to a bare file name, and the
  target is checked to stay inside the chosen directory.
* A download never overwrites an existing file unless asked, and is
  written to a temporary file first, so a failed or oversized transfer
  never leaves a partial file under the real name.
* An upload reads an arbitrary local path, so :func:`describe_upload_file`
  resolves it fully (symlinks included) and reports the resolved path and
  size for the confirmation step to show.
"""

from __future__ import annotations

import mimetypes
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

#: Upper bound for one transfer unless the caller raises or lowers it.
DEFAULT_MAX_BYTES = 50 * 1024 * 1024

_MAX_NAME_LENGTH = 200
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


class AttachmentFileError(ValueError):
    """Raised when a local file or a download target is unusable."""


def safe_filename(name: Any) -> str:
    """Reduce a remote-supplied name to a single, harmless file name.

    Drops any directory part (both ``/`` and ``\\`` separators), control
    characters, and surrounding whitespace/dots-only names.
    """
    if not isinstance(name, str):
        raise AttachmentFileError("Attachment has no usable file name.")
    base = _CONTROL_CHARS.sub("", re.split(r"[\\/]", name)[-1]).strip()
    if not base or set(base) <= {"."}:
        raise AttachmentFileError(f"Attachment file name {name!r} is not usable as a local file name.")
    if len(base) > _MAX_NAME_LENGTH:
        stem, dot, ext = base.rpartition(".")
        if dot and len(ext) <= 16:
            base = stem[: _MAX_NAME_LENGTH - len(ext) - 1] + "." + ext
        else:
            base = base[:_MAX_NAME_LENGTH]
    return base


def default_download_dir(toolset: str) -> Path:
    """Scratch directory used when the caller doesn't pass ``out_dir``."""
    return Path(tempfile.gettempdir()) / f"agent-skills-{toolset}-attachments"


def prepare_download_target(
    filename: Any, out_dir: Optional[str], toolset: str, overwrite: bool = False
) -> Path:
    """Return the path a download will be written to, creating its directory.

    Raises :class:`AttachmentFileError` if the name is unusable, the
    directory can't be created, or the file exists and ``overwrite`` is false.
    """
    directory = Path(out_dir).expanduser() if out_dir else default_download_dir(toolset)
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise AttachmentFileError(f"Cannot use output directory {directory}: {exc.strerror or exc}") from exc
    directory = directory.resolve()
    target = directory / safe_filename(filename)
    if target.parent != directory:  # defence in depth: safe_filename already strips separators
        raise AttachmentFileError(f"Refusing to write outside {directory}.")
    if os.path.lexists(target) and not overwrite:
        raise AttachmentFileError(
            f"{target} already exists. Pass overwrite (CLI: --overwrite) to replace it, "
            "or choose another output directory."
        )
    return target


def stream_to_file(chunks: Iterable[bytes], target: Path, max_bytes: int = DEFAULT_MAX_BYTES) -> int:
    """Write ``chunks`` to ``target`` atomically, enforcing ``max_bytes``.

    Returns the number of bytes written. The data goes to a temporary file
    in the same directory and is renamed into place only once complete, so
    exceeding the cap or losing the connection leaves nothing behind.
    """
    fd, tmp_name = tempfile.mkstemp(prefix=".download-", dir=str(target.parent))
    written = 0
    try:
        with os.fdopen(fd, "wb") as out:
            for chunk in chunks:
                if not chunk:
                    continue
                written += len(chunk)
                if written > max_bytes:
                    raise AttachmentFileError(
                        f"Attachment is larger than the {max_bytes}-byte limit (raise it with max_bytes / --max_bytes)."
                    )
                out.write(chunk)
        os.replace(tmp_name, target)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    return written


def check_size_within_limit(size: Optional[int], max_bytes: int) -> None:
    """Reject early when the remote service already reports a too-large size."""
    if isinstance(size, int) and size > max_bytes:
        raise AttachmentFileError(
            f"Attachment is {size} bytes, over the {max_bytes}-byte limit (raise it with max_bytes / --max_bytes)."
        )


def describe_upload_file(
    file_path: Any, filename: Optional[str] = None, max_bytes: int = DEFAULT_MAX_BYTES
) -> Dict[str, Any]:
    """Validate a local file for upload and describe it.

    Returns ``{"path": <fully resolved path>, "filename": <name it will have
    remotely>, "size_bytes": N, "media_type": ...}``. ``filename`` overrides
    the remote name (still reduced to a bare file name).
    """
    if not isinstance(file_path, str) or not file_path.strip():
        raise AttachmentFileError("'file_path' is required and must be a non-empty string.")
    path = Path(file_path.strip()).expanduser()
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError):
        raise AttachmentFileError(f"File not found: {path}") from None
    if not resolved.is_file():
        raise AttachmentFileError(f"Not a regular file: {resolved}")
    if not os.access(resolved, os.R_OK):
        raise AttachmentFileError(f"File is not readable: {resolved}")
    size = resolved.stat().st_size
    if size == 0:
        raise AttachmentFileError(f"File is empty: {resolved}")
    if size > max_bytes:
        raise AttachmentFileError(
            f"{resolved} is {size} bytes, over the {max_bytes}-byte limit (raise it with max_bytes / --max_bytes)."
        )
    name = safe_filename(filename if filename else resolved.name)
    media_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
    return {"path": str(resolved), "filename": name, "size_bytes": size, "media_type": media_type}
