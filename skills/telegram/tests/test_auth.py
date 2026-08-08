import json
import os
import time

import pytest

from lib import auth
from lib.auth import ConfigurationError, SessionSecurityError

from tests.conftest import CHANNEL_CHAT_ID, USER_CHAT_ID, write_session


# --------------------------------------------------------------------------
# load_config validation
# --------------------------------------------------------------------------


def test_load_config_requires_api_id_and_hash(env):
    del env["TELEGRAM_API_ID"]
    with pytest.raises(ConfigurationError, match="TELEGRAM_API_ID"):
        auth.load_config(env)


def test_load_config_rejects_non_integer_api_id(env):
    env["TELEGRAM_API_ID"] = "not-a-number"
    with pytest.raises(ConfigurationError):
        auth.load_config(env)


def test_load_config_allows_missing_allowlist_but_leaves_it_empty(env):
    del env["TELEGRAM_ALLOWED_CHATS"]
    config = auth.load_config(env)
    assert config.allowed_chats == frozenset()


def test_load_config_rejects_bad_allowlist_entry(env):
    env["TELEGRAM_ALLOWED_CHATS"] = "123456,@notanid"
    with pytest.raises(ConfigurationError):
        auth.load_config(env)


def test_load_config_rejects_bad_confirm_mode(env):
    env["TELEGRAM_CONFIRM_MODE"] = "auto"
    with pytest.raises(ConfigurationError):
        auth.load_config(env)


def test_load_config_max_read_limit_can_only_lower_the_ceiling(env):
    env["TELEGRAM_MAX_READ_LIMIT"] = "5000"
    config = auth.load_config(env)
    assert config.max_read_limit == 200  # the hard ceiling, not 5000

    env["TELEGRAM_MAX_READ_LIMIT"] = "50"
    config = auth.load_config(env)
    assert config.max_read_limit == 50


def test_load_config_refuses_session_path_inside_git_worktree(env):
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    env["TELEGRAM_SESSION_FILE"] = os.path.join(repo_root, "session.json")
    with pytest.raises(SessionSecurityError):
        auth.load_config(env)


# --------------------------------------------------------------------------
# session blob: load/validate/expire
# --------------------------------------------------------------------------


def test_write_then_load_session_state_round_trips(config):
    write_session(config)
    state = auth.load_session_state(config.session_file)
    assert state is not None
    assert state.session_string == "FAKE_SESSION_STRING"


def test_load_session_state_returns_none_when_absent(config):
    assert auth.load_session_state(config.session_file) is None


def test_load_session_state_refuses_loose_file_permissions(config):
    write_session(config, mode=0o644)
    with pytest.raises(SessionSecurityError):
        auth.load_session_state(config.session_file)


def test_load_session_state_refuses_future_created_at(config):
    write_session(config, created_at=time.time() + 10_000)
    with pytest.raises(SessionSecurityError):
        auth.load_session_state(config.session_file)


def test_is_expired_false_for_a_fresh_session(config):
    write_session(config)
    state = auth.load_session_state(config.session_file)
    assert auth.is_expired(state, config) is False


def test_is_expired_true_past_ttl(config):
    write_session(config, created_at=time.time() - (config.session_ttl_sec + 60))
    state = auth.load_session_state(config.session_file)
    assert auth.is_expired(state, config) is True


def test_ttl_is_absolute_repeated_checks_do_not_extend_it(config):
    created = time.time() - (config.session_ttl_sec - 5)  # about to expire
    write_session(config, created_at=created)
    state = auth.load_session_state(config.session_file)
    first = auth.is_expired(state, config)
    # "Using" the session (re-checking) must never push created_at forward.
    state_again = auth.load_session_state(config.session_file)
    assert state_again.created_at == state.created_at
    second = auth.is_expired(state_again, config)
    assert first == second


def test_ttl_effective_value_is_the_smaller_of_blob_and_config(config):
    # Blob claims a huge ttl_sec; the env-configured ttl must still win.
    write_session(config, ttl_sec=10_000_000, created_at=time.time() - (config.session_ttl_sec + 60))
    state = auth.load_session_state(config.session_file)
    assert auth.is_expired(state, config) is True


def test_delete_session_state_is_idempotent(config):
    write_session(config)
    auth.delete_session_state(config.session_file)
    assert not config.session_file.exists()
    auth.delete_session_state(config.session_file)  # must not raise


# --------------------------------------------------------------------------
# peers.json
# --------------------------------------------------------------------------


def test_write_then_load_peers_round_trips(config):
    peers = {USER_CHAT_ID: {"kind": "user", "access_hash": 42, "title": "Alice"}}
    auth.write_peers(config.peers_file, peers)
    loaded = auth.load_peers(config.peers_file)
    assert loaded == peers


def test_load_peers_empty_when_absent(config):
    assert auth.load_peers(config.peers_file) == {}


def test_load_peers_refuses_loose_permissions(config):
    auth.write_peers(config.peers_file, {USER_CHAT_ID: {"kind": "user", "access_hash": 1, "title": "x"}})
    os.chmod(config.peers_file, 0o644)
    with pytest.raises(SessionSecurityError):
        auth.load_peers(config.peers_file)
