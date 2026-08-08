import os
import sys
import time

import pytest

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SKILL_ROOT not in sys.path:
    sys.path.insert(0, SKILL_ROOT)

from lib import auth  # noqa: E402
from lib.auth import TelegramConfig  # noqa: E402

USER_CHAT_ID = 111222333
CHANNEL_CHAT_ID = -1000000000000 - 444555  # marked-id form of channel 444555
OTP_CHAT_ID = 777000


@pytest.fixture
def env(tmp_path):
    """A minimal valid environment. tmp_path is outside any git work tree."""
    session_dir = tmp_path / "runtime"
    return {
        "TELEGRAM_API_ID": "12345",
        "TELEGRAM_API_HASH": "deadbeefdeadbeefdeadbeefdeadbeef",
        "TELEGRAM_ALLOWED_CHATS": f"{USER_CHAT_ID},{CHANNEL_CHAT_ID}",
        "TELEGRAM_SESSION_FILE": str(session_dir / "session.json"),
        "TELEGRAM_CONFIRM_MODE": "flag",  # most tests use the agent-satisfiable two-step
    }


@pytest.fixture
def config(env, monkeypatch) -> TelegramConfig:
    """Loaded config, AND `env` is applied to the real process environment
    (via monkeypatch.setenv, auto-reverted after the test) -- tool modules
    call `load_config()` with no arguments and read `os.environ` directly,
    so depending on this fixture (even transitively, e.g. through
    `with_peers`) is what makes a tool-level test see the same environment
    a unit-level `auth.load_config(env)` call sees.
    """
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return auth.load_config(env)


@pytest.fixture
def with_peers(config):
    """Write a peers.json resolving both allowlisted test chats."""
    peers = {
        USER_CHAT_ID: {"kind": "user", "access_hash": 999888777, "title": "Alice"},
        CHANNEL_CHAT_ID: {"kind": "channel", "access_hash": 111222, "title": "Announcements"},
    }
    auth.write_peers(config.peers_file, peers)
    return peers


def write_session(config, *, created_at=None, ttl_sec=None, mode=0o600):
    """Write a session blob directly (bypassing login.py) for test setup."""
    state = auth.write_session_state(
        config.session_file, "FAKE_SESSION_STRING", ttl_sec if ttl_sec is not None else config.session_ttl_sec
    )
    if created_at is not None:
        import json

        payload = json.loads(config.session_file.read_text())
        payload["created_at"] = created_at
        config.session_file.write_text(json.dumps(payload))
    os.chmod(config.session_file, mode)
    return state


class FakeTTY:
    """Stands in for /dev/tty: write() records prompts, readline() returns a
    scripted answer. Used to test the tty confirmation path without a real
    terminal, and to prove a piped answer never reaches it (readline() is
    the only thing that can supply 'yes' -- there is no stdin path here).
    """

    def __init__(self, answer: str = "yes"):
        self.answer = answer
        self.written = []
        self.closed = False

    def write(self, text):
        self.written.append(text)

    def flush(self):
        pass

    def readline(self):
        return self.answer + "\n"

    def close(self):
        self.closed = True
