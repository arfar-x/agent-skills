"""Fake stand-ins for Telethon objects/coroutines, used by tests/test_tools.py
and tests/test_adversarial.py to exercise the tool layer without a real
Telegram connection. Nothing here imports telethon.
"""

from __future__ import annotations

import datetime as dt
from types import SimpleNamespace
from typing import Any, Dict, List, Optional


class FakeConn:
    """Stands in for a connected TelegramClient. Records disconnect() calls."""

    def __init__(self):
        self.disconnect_calls = 0

    async def disconnect(self):
        self.disconnect_calls += 1


class FakeFile(SimpleNamespace):
    pass


class FakeMessage(SimpleNamespace):
    """Mimics the subset of telethon.tl.custom.Message this skill reads."""

    def __init__(
        self,
        id: int,
        text: str = "",
        sender_id: Optional[int] = None,
        date: Optional[dt.datetime] = None,
        media=None,
        file=None,
        reply_to=None,
    ):
        super().__init__(
            id=id,
            message=text,
            sender_id=sender_id,
            date=date or dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc),
            media=media,
            file=file,
            reply_to=reply_to,
        )


class FakeSent(SimpleNamespace):
    def __init__(self, id: int, date: Optional[dt.datetime] = None):
        super().__init__(id=id, date=date or dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc))


class FakeMe(SimpleNamespace):
    def __init__(self, id=555, first_name="Test", last_name="", username="testuser", phone="15551234567"):
        super().__init__(id=id, first_name=first_name, last_name=last_name, username=username, phone=phone)


class FakeClientLib:
    """Records every call made through it, for assertion in tests."""

    def __init__(self):
        self.calls: List[Dict[str, Any]] = []
        self.messages: List[FakeMessage] = []
        self.sent = FakeSent(id=9001)
        self.forwarded = FakeSent(id=9002)
        self.single_message: Optional[FakeMessage] = None
        self.downloaded_path = "/tmp/fake-downloaded-file"
        self.me = FakeMe()
        self.ack_calls: List[Dict[str, Any]] = []

    def record(self, name, **kwargs):
        self.calls.append({"name": name, **kwargs})

    async def ensure_live_session(self, config):
        self.record("ensure_live_session")
        return FakeConn()

    async def whoami(self, client):
        self.record("whoami")
        return self.me

    async def do_logout(self, client):
        self.record("do_logout")

    async def fetch_messages(self, client, peer, *, limit, search_text=None):
        self.record("fetch_messages", limit=limit, search_text=search_text)
        return list(self.messages)

    async def acknowledge_read(self, client, peer, *, max_id):
        self.ack_calls.append({"max_id": max_id})
        self.record("acknowledge_read", max_id=max_id)

    async def send_text(self, client, peer, text):
        self.record("send_text", text=text)
        return self.sent

    async def forward_one(self, client, *, from_peer, to_peer, message_id):
        self.record("forward_one", message_id=message_id)
        return self.forwarded

    async def get_one_message(self, client, peer, message_id):
        self.record("get_one_message", message_id=message_id)
        return self.single_message

    async def download_to(self, client, message, out_path):
        self.record("download_to", out_path=str(out_path))
        return str(out_path)
