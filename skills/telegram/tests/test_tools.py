import json

import pytest

from lib import client as client_lib

from tests.conftest import CHANNEL_CHAT_ID, USER_CHAT_ID, write_session
from tests.fakes import FakeClientLib, FakeMessage


@pytest.fixture
def fake(monkeypatch):
    f = FakeClientLib()
    monkeypatch.setattr(client_lib, "ensure_live_session", f.ensure_live_session)
    monkeypatch.setattr(client_lib, "whoami", f.whoami)
    monkeypatch.setattr(client_lib, "do_logout", f.do_logout)
    monkeypatch.setattr(client_lib, "fetch_messages", f.fetch_messages)
    monkeypatch.setattr(client_lib, "acknowledge_read", f.acknowledge_read)
    monkeypatch.setattr(client_lib, "send_text", f.send_text)
    monkeypatch.setattr(client_lib, "forward_one", f.forward_one)
    monkeypatch.setattr(client_lib, "get_one_message", f.get_one_message)
    monkeypatch.setattr(client_lib, "download_to", f.download_to)
    monkeypatch.setattr(client_lib, "input_peer_for", lambda marked_id, record: object())
    return f


def _read_audit_lines(config):
    if not config.audit_log.exists():
        return []
    return [json.loads(line) for line in config.audit_log.read_text().splitlines() if line.strip()]


# --------------------------------------------------------------------------
# whoami
# --------------------------------------------------------------------------


def test_whoami_first_call_requires_confirmation(config, with_peers, fake):
    from tools.whoami import whoami

    result = whoami(confirm=False)
    assert result["requires_confirmation"] is True
    assert not any(c["name"] == "ensure_live_session" for c in fake.calls)


def test_whoami_confirmed_call_executes_and_audits(config, with_peers, fake):
    from tools.whoami import whoami

    write_session(config)
    result = whoami(confirm=True)
    assert result["confirmed"] is True
    assert result["whoami"]["user_id"] == fake.me.id
    events = _read_audit_lines(config)
    assert len(events) == 1
    assert events[0]["tool"] == "whoami"
    assert set(events[0]) == {"timestamp", "tool", "chat_id", "chat_title", "message_id", "counts", "outcome"}


def test_whoami_without_session_reports_no_session_error(config, with_peers):
    # Deliberately NOT using the `fake` fixture here: ensure_live_session's
    # real "no session file -> NoSessionError" check happens before any
    # Telethon call is even attempted, so this exercises the real function.
    from tools.whoami import whoami

    result = whoami(confirm=True)
    assert result["error"]["type"] == "no_session"


# --------------------------------------------------------------------------
# read_messages
# --------------------------------------------------------------------------


def test_read_messages_refuses_unauthorized_chat_before_any_confirmation(config, with_peers, fake):
    from tools.read_messages import read_messages

    result = read_messages(chat_id=999999999, confirm=False)
    assert result["error"]["type"] == "guard_not_allowlisted"
    assert fake.calls == []  # never even reached the confirmation step


def test_read_messages_default_no_seen_never_acknowledges(config, with_peers, fake):
    from tools.read_messages import read_messages

    write_session(config)
    fake.messages = [FakeMessage(id=1, text="hi"), FakeMessage(id=2, text="there")]
    result = read_messages(chat_id=USER_CHAT_ID, confirm=True)
    assert result["confirmed"] is True
    assert len(result["messages"]) == 2
    assert fake.ack_calls == []  # no read receipt sent, ever


def test_read_messages_no_seen_false_is_gated_and_acknowledges(config, with_peers, fake):
    from tools.read_messages import read_messages

    write_session(config)
    fake.messages = [FakeMessage(id=5, text="hi")]

    # First call without --confirm must still refuse -- no_seen=False is
    # outbound, so in "flag" mode it's still just the two-step (config
    # fixture uses flag mode).
    pending = read_messages(chat_id=USER_CHAT_ID, no_seen=False, confirm=False)
    assert pending["requires_confirmation"] is True
    assert fake.ack_calls == []

    result = read_messages(chat_id=USER_CHAT_ID, no_seen=False, confirm=True)
    assert result["confirmed"] is True
    assert fake.ack_calls == [{"max_id": 5}]


def test_read_messages_clamps_limit_to_ceiling(config, with_peers, fake):
    from tools.read_messages import read_messages

    write_session(config)
    fake.messages = []
    read_messages(chat_id=USER_CHAT_ID, limit=999999, confirm=True)
    fetch_call = next(c for c in fake.calls if c["name"] == "fetch_messages")
    assert fetch_call["limit"] == config.max_read_limit


def test_read_messages_redacts_message_text(config, with_peers, fake):
    from tools.read_messages import read_messages

    write_session(config)
    fake.messages = [FakeMessage(id=1, text="your login code is 483920, hurry")]
    result = read_messages(chat_id=USER_CHAT_ID, confirm=True)
    assert "483920" not in result["messages"][0]["text"]
    assert result["redactions"] == 1


# --------------------------------------------------------------------------
# send_message
# --------------------------------------------------------------------------


def test_send_message_first_call_requires_confirmation_with_summary(config, with_peers, fake):
    from tools.send_message import send_message

    result = send_message(chat_id=USER_CHAT_ID, text="hello", confirm=False)
    assert result["requires_confirmation"] is True
    assert "hello" in result["pending_action"]["summary"]
    assert fake.calls == []


def test_send_message_confirmed_executes_and_audits(config, with_peers, fake):
    from tools.send_message import send_message

    write_session(config)
    result = send_message(chat_id=USER_CHAT_ID, text="hello", confirm=True)
    assert result["confirmed"] is True
    assert result["message_id"] == fake.sent.id
    events = _read_audit_lines(config)
    assert events[0]["chat_id"] == USER_CHAT_ID
    assert events[0]["message_id"] == fake.sent.id
    assert "hello" not in json.dumps(events[0])  # audit log never carries the body


def test_send_message_redacts_before_sending_and_before_summary(config, with_peers, fake):
    # 445566 is chosen to share no digits with USER_CHAT_ID (111222333) or
    # CHANNEL_CHAT_ID, so a false pass/fail can't come from the chat_id
    # itself incidentally containing the "secret".
    from tools.send_message import send_message

    pending = send_message(chat_id=USER_CHAT_ID, text="code is 445566, ok?", confirm=False)
    assert "445566" not in pending["pending_action"]["summary"]

    write_session(config)
    send_message(chat_id=USER_CHAT_ID, text="code is 445566, ok?", confirm=True)
    sent_call = next(c for c in fake.calls if c["name"] == "send_text")
    assert "445566" not in sent_call["text"]


def test_send_message_refuses_otp_chat(config, with_peers, fake):
    from tools.send_message import send_message

    result = send_message(chat_id=777000, text="hi", confirm=True)
    assert result["error"]["type"] == "guard_otp_chat_denied"
    assert fake.calls == []


def test_send_message_rejects_empty_text(config, with_peers, fake):
    from tools.send_message import send_message

    result = send_message(chat_id=USER_CHAT_ID, text="   ", confirm=True)
    assert result["error"]["type"] == "invalid_input"


# --------------------------------------------------------------------------
# send_bulk
# --------------------------------------------------------------------------


def test_send_bulk_confirmed_sends_to_each_recipient_and_audits_each(config, with_peers, fake):
    from tools.send_bulk import send_bulk

    write_session(config)
    result = send_bulk(to=[USER_CHAT_ID, CHANNEL_CHAT_ID], text="hi all", confirm=True)
    assert result["confirmed"] is True
    assert len(result["sent"]) == 2
    send_calls = [c for c in fake.calls if c["name"] == "send_text"]
    assert len(send_calls) == 2
    events = _read_audit_lines(config)
    assert {e["chat_id"] for e in events} == {USER_CHAT_ID, CHANNEL_CHAT_ID}


def test_send_bulk_refuses_over_cap_before_any_send(config, with_peers, fake):
    from tools.send_bulk import send_bulk

    result = send_bulk(to=[USER_CHAT_ID] * 11, text="spam", confirm=True)
    assert result["error"]["type"] == "guard_too_many_targets"
    assert fake.calls == []


# --------------------------------------------------------------------------
# forward_message
# --------------------------------------------------------------------------


def test_forward_message_confirmed_executes(config, with_peers, fake):
    from tools.forward_message import forward_message

    write_session(config)
    result = forward_message(from_chat_id=USER_CHAT_ID, message_id=42, to_chat_id=CHANNEL_CHAT_ID, confirm=True)
    assert result["confirmed"] is True
    assert result["forwarded_message_id"] == fake.forwarded.id


def test_forward_message_refuses_when_either_side_not_allowlisted(config, with_peers, fake):
    from tools.forward_message import forward_message

    result = forward_message(from_chat_id=USER_CHAT_ID, message_id=1, to_chat_id=42424242, confirm=True)
    assert result["error"]["type"] == "guard_not_allowlisted"
    assert fake.calls == []


# --------------------------------------------------------------------------
# mark_read
# --------------------------------------------------------------------------


def test_mark_read_confirmed_acknowledges_whole_chat(config, with_peers, fake):
    from tools.mark_read import mark_read

    write_session(config)
    result = mark_read(chat_id=USER_CHAT_ID, confirm=True)
    assert result["confirmed"] is True
    assert fake.ack_calls == [{"max_id": 0}]


# --------------------------------------------------------------------------
# download_media
# --------------------------------------------------------------------------


def test_download_media_confirmed_writes_under_out_dir(config, with_peers, fake, tmp_path):
    from tools.download_media import download_media

    write_session(config)
    out_dir = tmp_path / "downloads"
    out_dir.mkdir()
    fake.single_message = FakeMessage(id=7, media=object(), file=None)
    result = download_media(chat_id=USER_CHAT_ID, message_id=7, out_dir=str(out_dir), confirm=True)
    assert result["confirmed"] is True
    dl_call = next(c for c in fake.calls if c["name"] == "download_to")
    assert dl_call["out_path"].startswith(str(out_dir))


def test_download_media_refuses_message_without_media(config, with_peers, fake, tmp_path):
    from tools.download_media import download_media

    write_session(config)
    out_dir = tmp_path / "downloads"
    out_dir.mkdir()
    fake.single_message = FakeMessage(id=7, media=None)
    result = download_media(chat_id=USER_CHAT_ID, message_id=7, out_dir=str(out_dir), confirm=True)
    assert "error" in result


def test_download_media_requires_out_dir(config, with_peers, fake):
    from tools.download_media import download_media

    write_session(config)
    fake.single_message = FakeMessage(id=7, media=object(), file=None)
    result = download_media(chat_id=USER_CHAT_ID, message_id=7, out_dir=None, confirm=True)
    assert result["error"]["type"] == "guard_missing_out_dir"


# --------------------------------------------------------------------------
# logout
# --------------------------------------------------------------------------


def test_logout_confirmed_revokes_and_deletes_local_blob(config, with_peers, fake):
    from tools.logout import logout

    write_session(config)
    assert config.session_file.exists()
    result = logout(confirm=True)
    assert result["confirmed"] is True
    assert not config.session_file.exists()
    assert any(c["name"] == "do_logout" for c in fake.calls)


# --------------------------------------------------------------------------
# allowed_chats
# --------------------------------------------------------------------------


def test_allowed_chats_lists_only_allowlisted_non_otp_ids(config, with_peers, monkeypatch):
    from tools.allowed_chats import allowed_chats

    # config/with_peers already ran with the base env; widen the allowlist
    # to include the OTP id for this one test and confirm it's filtered out
    # of the listing even though it's technically present.
    monkeypatch.setenv("TELEGRAM_ALLOWED_CHATS", f"{USER_CHAT_ID},{CHANNEL_CHAT_ID},777000")

    result = allowed_chats(confirm=True)

    ids = {c["chat_id"] for c in result["allowed_chats"]}
    assert 777000 not in ids
    assert USER_CHAT_ID in ids
    assert CHANNEL_CHAT_ID in ids
