"""Typed, JSON-serializable data returned by this skill's tools.

Plain dataclasses, mirroring `skills/jira/lib/models.py`'s pattern -- tools
return `to_dict()` output directly, never a raw Telethon TL object, so the
agent never sees (and can't accidentally echo) anything beyond what these
shapes expose.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Peer:
    """A single allowlisted chat, as resolved once by `scripts/login.py`."""

    id: int  # canonical marked id, see lib/utils.py
    kind: str  # "user" | "chat" | "channel"
    access_hash: Optional[int]  # None for basic groups, which need none
    title: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "access_hash": self.access_hash,
            "title": self.title,
        }


@dataclass(frozen=True)
class Message:
    id: int
    chat_id: int
    sender_id: Optional[int]
    date: Optional[str]
    text: str
    redactions: int = 0
    has_media: bool = False
    media_kind: Optional[str] = None
    reply_to_msg_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "chat_id": self.chat_id,
            "sender_id": self.sender_id,
            "date": self.date,
            "text": self.text,
            "redactions": self.redactions,
            "has_media": self.has_media,
            "media_kind": self.media_kind,
            "reply_to_msg_id": self.reply_to_msg_id,
        }


@dataclass(frozen=True)
class SentMessage:
    id: int
    chat_id: int
    date: Optional[str]
    redactions: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "chat_id": self.chat_id,
            "date": self.date,
            "redactions": self.redactions,
        }


@dataclass(frozen=True)
class DownloadedFile:
    chat_id: int
    message_id: int
    path: str
    size_bytes: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chat_id": self.chat_id,
            "message_id": self.message_id,
            "path": self.path,
            "size_bytes": self.size_bytes,
        }


@dataclass(frozen=True)
class Whoami:
    user_id: int
    display_name: Optional[str]
    username: Optional[str]
    phone_last4: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "display_name": self.display_name,
            "username": self.username,
            "phone_last4": self.phone_last4,
        }
