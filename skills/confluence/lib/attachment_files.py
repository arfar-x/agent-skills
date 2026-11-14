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
* Local files are reachable only inside one directory the operator
  chooses, :data:`ATTACHMENT_DIR_ENV`. The tool's caller -- often a model
  acting on untrusted input -- can't widen it: an upload path or a
  download ``out_dir`` that resolves (symlinks included) outside that
  directory is refused, and so is any hidden or secret-looking file in
  it (``.env``, ``.ssh/``, ``*.pem``, ...). With the variable unset, no
  local path is accepted at all: uploads come from content the caller
  passes (:func:`describe_upload_content`) and downloads go to a scratch
  directory. This is what keeps ``/proc/self/environ``, ``.env`` files
  and the like from ever being attached to a ticket or a page.
"""

from __future__ import annotations

import base64
import binascii
import contextlib
import mimetypes
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

#: Upper bound for one transfer unless the caller raises or lowers it.
DEFAULT_MAX_BYTES = 50 * 1024 * 1024

#: Upper bound for an attachment read straight into a tool result: it ends
#: up in a model's context, so it is far smaller than a download.
DEFAULT_READ_MAX_BYTES = 1024 * 1024

#: No caller-supplied ``max_bytes`` raises an inline read above this: the
#: bytes are held in memory and end up in a model's context.
READ_HARD_MAX_BYTES = 8 * 1024 * 1024


def clamp_read_limit(max_bytes: Any) -> int:
    """The limit an inline read uses: the caller's ``max_bytes`` when it is a
    positive integer, capped at :data:`READ_HARD_MAX_BYTES`; otherwise the
    default."""
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes <= 0:
        return DEFAULT_READ_MAX_BYTES
    return min(max_bytes, READ_HARD_MAX_BYTES)


_TEXT_MEDIA_TYPE = re.compile(
    r"^(text/|application/(json|xml|yaml|x-yaml|javascript|ecmascript|csv|sql|x-sh|x-httpd-php|graphql|toml|x-ndjson)\b|"
    r"application/[\w.+-]+\+(json|xml|yaml)\b)",
    re.IGNORECASE,
)

#: Environment variable naming the only directory local files may be
#: uploaded from or downloaded into. Set by whoever runs the tools, never
#: by a tool argument.
ATTACHMENT_DIR_ENV = "AGENT_SKILLS_ATTACHMENT_DIR"

_MAX_NAME_LENGTH = 200
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")

#: File names refused even inside the attachment directory: environment
#: files, private keys and credential stores. Hidden files and anything
#: under a hidden directory are refused too.
_SECRET_NAME = re.compile(
    r"(\.env|\.pem|\.key|\.p12|\.pfx|\.jks|\.keystore|\.kdbx|\.ovpn)$"
    r"|^(id_rsa|id_dsa|id_ecdsa|id_ed25519)(\.|$)"
    r"|^(credentials|secrets?)(\.[a-z]+)?$",
    re.IGNORECASE,
)


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


def attachment_dir() -> Optional[Path]:
    """The directory set in :data:`ATTACHMENT_DIR_ENV`, resolved, or
    ``None`` when it is unset (local paths then disabled).

    Raises :class:`AttachmentFileError` if it is set but unusable: not an
    existing directory, or the filesystem root.
    """
    raw = os.environ.get(ATTACHMENT_DIR_ENV, "").strip()
    if not raw:
        return None
    try:
        root = Path(raw).expanduser().resolve(strict=True)
    except (OSError, RuntimeError):
        raise AttachmentFileError(f"{ATTACHMENT_DIR_ENV} ({raw}) does not exist.") from None
    if not root.is_dir():
        raise AttachmentFileError(f"{ATTACHMENT_DIR_ENV} ({raw}) is not a directory.")
    if root == Path(root.anchor):
        raise AttachmentFileError(f"{ATTACHMENT_DIR_ENV} must not be the filesystem root.")
    return root


def _inside(root: Path, path: Path) -> Path:
    """``path`` relative to ``root``, or raise if it lies outside it."""
    try:
        return path.relative_to(root)
    except ValueError:
        raise AttachmentFileError(
            f"{path} is outside the attachment directory ({ATTACHMENT_DIR_ENV}); refusing to use it."
        ) from None


def refuse_secret_looking(relative: Path) -> None:
    """Raise if any part of ``relative`` is hidden, or its name looks like a secret."""
    for part in relative.parts:
        if part.startswith("."):
            raise AttachmentFileError(f"Refusing hidden file or directory {part!r}.")
    if _SECRET_NAME.search(relative.name):
        raise AttachmentFileError(f"Refusing {relative.name!r}: it looks like a secret or key file.")


def default_download_dir(toolset: str) -> Path:
    """Scratch directory used when the caller doesn't pass ``out_dir``."""
    return Path(tempfile.gettempdir()) / f"agent-skills-{toolset}-attachments"


def prepare_download_target(
    filename: Any, out_dir: Optional[str], toolset: str, overwrite: bool = False
) -> Path:
    """Return the path a download will be written to, creating its directory.

    Without ``out_dir`` the file goes to a scratch directory. ``out_dir``
    must lie inside the attachment directory (relative paths are taken
    from it), and is refused when that directory isn't configured.

    Raises :class:`AttachmentFileError` if the name is unusable, the
    directory is not allowed or can't be created, or the file exists and
    ``overwrite`` is false.
    """
    root = attachment_dir()
    if out_dir:
        if root is None:
            raise AttachmentFileError(
                f"Saving to a chosen directory is disabled: set {ATTACHMENT_DIR_ENV} to allow one, "
                "or leave out_dir unset to use the scratch directory."
            )
        directory = Path(os.path.normpath(root / Path(out_dir).expanduser()))
        refuse_secret_looking(_inside(root, directory) / "x")
    else:
        directory = default_download_dir(toolset)
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise AttachmentFileError(f"Cannot use output directory {directory}: {exc.strerror or exc}") from exc
    directory = directory.resolve()
    if out_dir:
        _inside(root, directory)  # again after resolving, in case of a symlink
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


def read_to_memory(chunks: Iterable[bytes], max_bytes: int = DEFAULT_READ_MAX_BYTES) -> bytes:
    """Collect ``chunks`` in memory, refusing more than ``max_bytes``."""
    data = bytearray()
    for chunk in chunks:
        if not chunk:
            continue
        data += chunk
        if len(data) > max_bytes:
            raise AttachmentFileError(
                f"Attachment is larger than the {max_bytes}-byte limit for reading it inline "
                "(raise max_bytes / --max_bytes, or download it with get_attachment)."
            )
    return bytes(data)


def present_content(data: bytes, media_type: Optional[str], as_base64: bool = False) -> Dict[str, Any]:
    """How a tool result carries an attachment's bytes.

    Text (a text-like media type, or anything that is valid UTF-8 without
    NUL bytes) comes back as ``{"encoding": "text", "content": str}``.
    Binary comes back base64-encoded only when ``as_base64`` is asked for,
    since it is rarely useful in a model's context; otherwise
    ``{"encoding": "binary", "content": None}`` with a note. ``as_base64``
    also forces base64 for text.
    """
    if as_base64:
        return {"encoding": "base64", "content": base64.b64encode(data).decode("ascii")}
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = None
    if text is not None and ("\x00" not in text or _TEXT_MEDIA_TYPE.match(media_type or "")):
        return {"encoding": "text", "content": text.lstrip("\ufeff")}
    return {
        "encoding": "binary",
        "content": None,
        "note": "Binary content is not returned inline; pass as_base64 to get it base64-encoded, "
        "or download it with get_attachment.",
    }


def check_size_within_limit(size: Optional[int], max_bytes: int) -> None:
    """Reject early when the remote service already reports a too-large size."""
    if isinstance(size, int) and size > max_bytes:
        raise AttachmentFileError(
            f"Attachment is {size} bytes, over the {max_bytes}-byte limit (raise it with max_bytes / --max_bytes)."
        )


def resolve_local_file(
    root: Path, file_path: Any, max_bytes: int = DEFAULT_MAX_BYTES
) -> Dict[str, Any]:
    """Validate ``file_path`` against ``root`` and describe it.

    ``root`` must already be resolved. The file must lie inside it (a
    relative path is taken from it) and must not be hidden or look like a
    secret. Returns ``{"path": <fully resolved path>, "filename",
    "size_bytes", "media_type"}``.
    """
    if not isinstance(file_path, str) or not file_path.strip():
        raise AttachmentFileError("'file_path' is required and must be a non-empty string.")
    if "\x00" in file_path:
        raise AttachmentFileError("'file_path' must not contain NUL characters.")
    path = root / Path(file_path.strip()).expanduser()
    refuse_secret_looking(_inside(root, Path(os.path.normpath(path))))
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError):
        raise AttachmentFileError(f"File not found: {file_path.strip()}") from None
    refuse_secret_looking(_inside(root, resolved))
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
    name = safe_filename(resolved.name)
    media_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
    return {"path": str(resolved), "filename": name, "size_bytes": size, "media_type": media_type}


def describe_upload_file(
    file_path: Any, filename: Optional[str] = None, max_bytes: int = DEFAULT_MAX_BYTES
) -> Dict[str, Any]:
    """Validate a local file for upload and describe it.

    Only files inside the attachment directory are accepted (see
    :func:`resolve_local_file`); with the directory unset, none. Returns
    ``{"path", "filename": <name it will have remotely>, "size_bytes",
    "media_type"}``. ``filename`` overrides the remote name (still reduced
    to a bare file name).
    """
    root = attachment_dir()
    if root is None:
        raise AttachmentFileError(
            f"Uploading a local file is disabled: set {ATTACHMENT_DIR_ENV} to the directory files may be "
            "uploaded from, or pass the file's content instead."
        )
    info = resolve_local_file(root, file_path, max_bytes)
    if filename:
        info["filename"] = safe_filename(filename)
        info["media_type"] = mimetypes.guess_type(info["filename"])[0] or "application/octet-stream"
    return info


def describe_upload_content(
    content: Optional[str] = None,
    content_base64: Optional[str] = None,
    filename: Any = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> Dict[str, Any]:
    """Validate content passed by the caller for upload, instead of a file.

    Exactly one of ``content`` (text, uploaded as UTF-8) and
    ``content_base64`` (any bytes) is required, and ``filename``. Returns
    ``{"data": bytes, "filename", "size_bytes", "media_type"}``.
    """
    if (content is None) == (content_base64 is None):
        raise AttachmentFileError("Pass exactly one of 'content' and 'content_base64'.")
    if not filename:
        raise AttachmentFileError("'filename' is required when uploading content.")
    if content is not None:
        data = content.encode("utf-8")
    else:
        try:
            data = base64.b64decode(content_base64 or "", validate=True)
        except (binascii.Error, ValueError):
            raise AttachmentFileError("'content_base64' is not valid base64.") from None
    if not data:
        raise AttachmentFileError("The content is empty.")
    if len(data) > max_bytes:
        raise AttachmentFileError(
            f"The content is {len(data)} bytes, over the {max_bytes}-byte limit (raise it with max_bytes / --max_bytes)."
        )
    name = safe_filename(filename)
    media_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
    return {"data": data, "filename": name, "size_bytes": len(data), "media_type": media_type}


def describe_upload(
    file_path: Optional[str] = None,
    content: Optional[str] = None,
    content_base64: Optional[str] = None,
    filename: Optional[str] = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> Dict[str, Any]:
    """Describe an upload from exactly one source: a local file or content."""
    if file_path and (content is not None or content_base64 is not None):
        raise AttachmentFileError("Pass either 'file_path' or the content, not both.")
    if file_path:
        return describe_upload_file(file_path, filename, max_bytes)
    if content is None and content_base64 is None:
        raise AttachmentFileError("Nothing to upload: pass 'content', 'content_base64' or 'file_path'.")
    return describe_upload_content(content, content_base64, filename, max_bytes)


def upload_body(info: Dict[str, Any]):
    """The bytes to send for a described upload, as a context manager."""
    if "data" in info:
        return contextlib.nullcontext(info["data"])
    return open(info["path"], "rb")
