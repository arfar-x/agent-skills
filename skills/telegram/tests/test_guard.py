from pathlib import Path

import pytest

from lib import guard
from lib.guard import GuardError

from tests.conftest import CHANNEL_CHAT_ID, FakeTTY, OTP_CHAT_ID, USER_CHAT_ID


# --------------------------------------------------------------------------
# authorize_chat: allowlist + OTP denylist
# --------------------------------------------------------------------------


def test_authorize_chat_accepts_an_allowlisted_id(config):
    assert guard.authorize_chat(config, USER_CHAT_ID) == USER_CHAT_ID


def test_authorize_chat_refuses_when_allowlist_unset(config):
    empty_config = config.__class__(**{**config.__dict__, "allowed_chats": frozenset()})
    with pytest.raises(GuardError) as exc:
        guard.authorize_chat(empty_config, USER_CHAT_ID)
    assert exc.value.kind == "no_allowlist_configured"


def test_authorize_chat_refuses_id_not_in_allowlist(config):
    with pytest.raises(GuardError) as exc:
        guard.authorize_chat(config, 999999999)
    assert exc.value.kind == "not_allowlisted"


@pytest.mark.parametrize("spelling", [OTP_CHAT_ID, "777000", " 777000 ", "+777000", "0777000", -777000, "-777000"])
def test_authorize_chat_refuses_otp_chat_every_spelling(config, spelling):
    with pytest.raises(GuardError) as exc:
        guard.authorize_chat(config, spelling)
    assert exc.value.kind == "otp_chat_denied"


def test_authorize_chat_refuses_otp_chat_even_when_allowlisted(env):
    from lib import auth

    env["TELEGRAM_ALLOWED_CHATS"] = f"{USER_CHAT_ID},{OTP_CHAT_ID}"
    config = auth.load_config(env)
    assert OTP_CHAT_ID in config.allowed_chats  # sanity: it really is allowlisted
    with pytest.raises(GuardError) as exc:
        guard.authorize_chat(config, OTP_CHAT_ID)
    assert exc.value.kind == "otp_chat_denied"


@pytest.mark.parametrize("target", ["@alice", "t.me/alice", "+1 555 123 4567", "Alice Smith"])
def test_authorize_chat_refuses_non_numeric_targets(config, target):
    with pytest.raises(GuardError) as exc:
        guard.authorize_chat(config, target)
    assert exc.value.kind == "invalid_chat_id"


def test_authorize_chat_accepts_an_unpunctuated_digit_run_with_a_plus_sign(config):
    # A caveat, not a bug: "+<digits>" is accepted by design (the plan
    # requires "+777000" to parse as a spelling of chat_id 777000), which
    # means an unpunctuated phone-number-shaped string is indistinguishable
    # from a chat_id and is therefore treated as one -- there is no way to
    # tell them apart from the string alone. A phone number written with
    # any punctuation (spaces, dashes) is still refused, per the test above.
    assert guard.authorize_chat(config, "+111222333") == USER_CHAT_ID


# --------------------------------------------------------------------------
# authorize_targets: send_bulk cap, no dedup, no wildcard
# --------------------------------------------------------------------------


def test_authorize_targets_accepts_up_to_the_cap(config):
    targets = [USER_CHAT_ID] * 1 + [CHANNEL_CHAT_ID] * 1
    assert guard.authorize_targets(config, targets) == [USER_CHAT_ID, CHANNEL_CHAT_ID]


def test_authorize_targets_refuses_over_the_cap(config):
    targets = [USER_CHAT_ID] * 11
    with pytest.raises(GuardError) as exc:
        guard.authorize_targets(config, targets)
    assert exc.value.kind == "too_many_targets"


def test_authorize_targets_does_not_dedupe_before_the_cap_check(config):
    # 11 copies of the SAME recipient must still refuse -- deduping first
    # would silently let this pass.
    targets = [USER_CHAT_ID] * 11
    with pytest.raises(GuardError) as exc:
        guard.authorize_targets(config, targets)
    assert exc.value.kind == "too_many_targets"


def test_authorize_targets_refuses_empty_list(config):
    with pytest.raises(GuardError) as exc:
        guard.authorize_targets(config, [])
    assert exc.value.kind == "invalid_targets"


def test_authorize_targets_refuses_wildcard_style_strings(config):
    with pytest.raises(GuardError):
        guard.authorize_targets(config, ["all"])


# --------------------------------------------------------------------------
# gate(): confirmation modes
# --------------------------------------------------------------------------


def test_gate_flag_mode_first_call_requires_confirmation(config):
    result = guard.gate(config, tool="read_messages", outbound=False, confirm=False, summary="s", pending_action={})
    assert result == {
        "confirmed": False,
        "requires_confirmation": True,
        "pending_action": {"action": "read_messages", "summary": "s"},
    }


def test_gate_flag_mode_second_call_with_confirm_proceeds(config):
    result = guard.gate(config, tool="read_messages", outbound=False, confirm=True, summary="s", pending_action={})
    assert result is None


def test_gate_flag_mode_outbound_also_uses_two_step(config):
    # confirm_mode="flag" in the `config` fixture -- outbound actions use
    # the two-step here too, not the tty prompt.
    result = guard.gate(config, tool="send_message", outbound=True, confirm=False, summary="s", pending_action={})
    assert result["requires_confirmation"] is True


def test_gate_tty_mode_outbound_ignores_confirm_flag_and_prompts(env, monkeypatch):
    from lib import auth

    env["TELEGRAM_CONFIRM_MODE"] = "tty"
    config = auth.load_config(env)
    fake_tty = FakeTTY(answer="yes")
    monkeypatch.setattr(guard, "_open_tty", lambda: fake_tty)

    # --confirm=True on the very FIRST call must still demand the terminal.
    result = guard.gate(config, tool="send_message", outbound=True, confirm=True, summary="send this", pending_action={})
    assert result is None
    assert any("send this" in w for w in fake_tty.written)


def test_gate_tty_mode_outbound_refuses_when_answer_is_not_yes(env, monkeypatch):
    from lib import auth

    env["TELEGRAM_CONFIRM_MODE"] = "tty"
    config = auth.load_config(env)
    fake_tty = FakeTTY(answer="sure")
    monkeypatch.setattr(guard, "_open_tty", lambda: fake_tty)

    with pytest.raises(GuardError) as exc:
        guard.gate(config, tool="send_message", outbound=True, confirm=False, summary="s", pending_action={})
    assert exc.value.kind == "tty_declined"


def test_gate_tty_mode_outbound_refuses_when_no_terminal_available(env, monkeypatch):
    from lib import auth

    env["TELEGRAM_CONFIRM_MODE"] = "tty"
    config = auth.load_config(env)

    def _no_tty():
        raise OSError("no such device")

    monkeypatch.setattr(guard, "_open_tty", _no_tty)
    with pytest.raises(GuardError) as exc:
        guard.gate(config, tool="send_message", outbound=True, confirm=False, summary="s", pending_action={})
    assert exc.value.kind == "tty_unavailable"


def test_gate_tty_mode_outbound_ignores_piped_stdin_it_never_reads_stdin(env, monkeypatch):
    """The prompt reads only /dev/tty (FakeTTY here); it never touches
    sys.stdin at all, so a piped 'yes\\n' on stdin cannot answer it. Proven
    by leaving sys.stdin patched to something that would raise if read.
    """
    from lib import auth

    env["TELEGRAM_CONFIRM_MODE"] = "tty"
    config = auth.load_config(env)
    fake_tty = FakeTTY(answer="yes")
    monkeypatch.setattr(guard, "_open_tty", lambda: fake_tty)

    class ExplodingStdin:
        def readline(self):
            raise AssertionError("guard.gate must never read sys.stdin")

    monkeypatch.setattr("sys.stdin", ExplodingStdin())
    result = guard.gate(config, tool="send_message", outbound=True, confirm=False, summary="s", pending_action={})
    assert result is None  # proceeded via /dev/tty, never touched sys.stdin


def test_gate_tty_mode_non_outbound_still_uses_two_step(env, monkeypatch):
    from lib import auth

    env["TELEGRAM_CONFIRM_MODE"] = "tty"
    config = auth.load_config(env)
    monkeypatch.setattr(guard, "_open_tty", lambda: (_ for _ in ()).throw(AssertionError("must not prompt")))

    result = guard.gate(config, tool="read_messages", outbound=False, confirm=False, summary="s", pending_action={})
    assert result["requires_confirmation"] is True  # never touched _open_tty


# --------------------------------------------------------------------------
# clamp_read_limit
# --------------------------------------------------------------------------


def test_clamp_read_limit_default(config):
    assert guard.clamp_read_limit(config, None) == guard.DEFAULT_READ_LIMIT


@pytest.mark.parametrize("bad", [-1, 0, "abc", 1e9])
def test_clamp_read_limit_rejects_invalid_values(config, bad):
    if bad == 1e9:
        assert guard.clamp_read_limit(config, bad) == config.max_read_limit
        return
    with pytest.raises(GuardError):
        guard.clamp_read_limit(config, bad)


def test_clamp_read_limit_clamps_to_ceiling(config):
    assert guard.clamp_read_limit(config, 99999) == config.max_read_limit


def test_clamp_read_limit_below_ceiling_passes_through(config):
    assert guard.clamp_read_limit(config, 5) == 5


# --------------------------------------------------------------------------
# download sandbox
# --------------------------------------------------------------------------


def test_authorize_download_dir_requires_explicit_dir():
    with pytest.raises(GuardError) as exc:
        guard.authorize_download_dir(None)
    assert exc.value.kind == "missing_out_dir"


def test_authorize_download_dir_refuses_root():
    with pytest.raises(GuardError):
        guard.authorize_download_dir("/")


def test_authorize_download_dir_refuses_home():
    with pytest.raises(GuardError):
        guard.authorize_download_dir("~")


def test_authorize_download_dir_refuses_repo_root():
    repo_root = Path(__file__).resolve().parents[3]
    with pytest.raises(GuardError):
        guard.authorize_download_dir(str(repo_root))


def test_authorize_download_dir_refuses_traversal_into_system_dir(tmp_path):
    # pytest's tmp_path is nested several levels deep, so ".." must climb
    # all the way to actually land on "/etc" -- easiest to prove the
    # traversal is resolved (not treated as a literal path) by climbing
    # tmp_path's own full depth back to the filesystem root and then in.
    depth = len(tmp_path.resolve().parts) - 1  # parts[0] is the root itself
    traversal = tmp_path.joinpath(*([".."] * depth), "etc")
    with pytest.raises(GuardError):
        guard.authorize_download_dir(str(traversal))


def test_authorize_download_dir_refuses_symlink_into_repo(tmp_path):
    repo_root = Path(__file__).resolve().parents[3]
    link = tmp_path / "sneaky"
    link.symlink_to(repo_root)
    with pytest.raises(GuardError):
        guard.authorize_download_dir(str(link))


def test_authorize_download_dir_allows_an_ordinary_subdirectory(tmp_path):
    target = tmp_path / "downloads"
    target.mkdir()
    resolved = guard.authorize_download_dir(str(target))
    assert resolved == target.resolve()


def test_authorize_download_size_refuses_oversize():
    with pytest.raises(GuardError) as exc:
        guard.authorize_download_size(guard.MAX_DOWNLOAD_BYTES + 1)
    assert exc.value.kind == "oversize"


def test_authorize_download_size_allows_under_cap():
    guard.authorize_download_size(1024)  # must not raise


def test_authorize_filename_refuses_unsafe_names():
    with pytest.raises(GuardError) as exc:
        guard.authorize_filename("payload.sh")
    assert exc.value.kind == "unsafe_filename"


def test_authorize_filename_allows_safe_names():
    assert guard.authorize_filename("photo.jpg") == "photo.jpg"
