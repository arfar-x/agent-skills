"""Typed data models returned by the Confluence client.

These are intentionally plain, JSON-serializable dataclasses. Tools
return ``to_dict()`` output directly -- the LLM never sees Confluence's
raw REST payloads, only these normalized structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Space:
    key: str
    name: str
    url: Optional[str] = None
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "url": self.url,
            "description": self.description,
        }


@dataclass(frozen=True)
class Ancestor:
    id: str
    title: str

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "title": self.title}


@dataclass(frozen=True)
class Page:
    id: str
    title: str
    space_key: str
    version: int
    url: Optional[str] = None
    body_plain_text: Optional[str] = None
    parent_id: Optional[str] = None
    ancestors: List[Ancestor] = field(default_factory=list)
    created: Optional[str] = None
    updated: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "space_key": self.space_key,
            "version": self.version,
            "url": self.url,
            "body_plain_text": self.body_plain_text,
            "parent_id": self.parent_id,
            "ancestors": [a.to_dict() for a in self.ancestors],
            "created": self.created,
            "updated": self.updated,
        }


@dataclass(frozen=True)
class Comment:
    id: str
    author: Optional[str]
    body_plain_text: str
    created: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "author": self.author,
            "body_plain_text": self.body_plain_text,
            "created": self.created,
        }


@dataclass(frozen=True)
class Attachment:
    id: str
    title: str
    media_type: Optional[str]
    file_size: Optional[int]
    url: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "media_type": self.media_type,
            "file_size": self.file_size,
            "url": self.url,
        }
