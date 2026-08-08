"""download_media: save one message's media attachment to disk. Gated.

The message is fetched (never marking it read -- `get_messages`/`ids=`
never acknowledges) twice: once before confirmation, to inspect size and
filename so the confirmation summary is accurate, and once after
confirmation, to actually download. Only the second fetch writes anything.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from lib import audit, client as client_lib, guard
from lib.auth import load_config
from tools._common import require_int, resolve_peer_record, run_connected, run_tool


def download_media(
    chat_id: object,
    message_id: object,
    out_dir: Optional[object] = None,
    confirm: bool = False,
) -> Dict[str, Any]:
    def _run() -> Dict[str, Any]:
        config = load_config()
        message_id_val = require_int(message_id, "message_id")
        marked_id = guard.authorize_chat(config, chat_id)
        record = resolve_peer_record(config, marked_id)
        title = record.get("title")
        peer = client_lib.input_peer_for(marked_id, record)

        message = run_connected(config, lambda client: client_lib.get_one_message(client, peer, message_id_val))
        if message is None or not getattr(message, "media", None):
            raise ValueError(f"Message {message_id_val} in chat {marked_id} has no downloadable media.")

        file_info = getattr(message, "file", None)
        size = getattr(file_info, "size", None)
        guard.authorize_download_size(size)
        raw_name = getattr(file_info, "name", None) or f"{marked_id}_{message_id_val}"
        safe_name = guard.authorize_filename(raw_name)

        target_dir = guard.authorize_download_dir(out_dir if out_dir is not None else config.download_dir)
        out_path = target_dir / safe_name

        summary = (
            f"Download the media attached to message {message_id_val} in chat "
            f"{marked_id}{f' ({title})' if title else ''} ({size or 'unknown'} bytes) to {out_path}."
        )
        pending = guard.gate(
            config,
            tool="download_media",
            outbound=False,
            confirm=confirm,
            summary=summary,
            pending_action={"chat_id": marked_id, "message_id": message_id_val, "out_path": str(out_path)},
        )
        if pending is not None:
            return pending

        async def _download(client):
            msg = await client_lib.get_one_message(client, peer, message_id_val)
            return await client_lib.download_to(client, msg, out_path)

        saved_path = run_connected(config, _download)
        audit.append_event(
            config.audit_log,
            tool="download_media",
            chat_id=marked_id,
            chat_title=title,
            message_id=message_id_val,
            counts={"bytes": size or 0},
            outcome="executed",
        )
        return {"confirmed": True, "chat_id": marked_id, "path": saved_path, "size_bytes": size}

    return run_tool("download_media", _run)
