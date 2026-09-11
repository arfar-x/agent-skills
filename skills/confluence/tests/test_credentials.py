import pytest

from lib.auth import ConfigurationError, load_credential
from lib.credentials import BasicCredential, BearerCredential


def test_load_credential_prefers_pat_over_basic():
    cred = load_credential(
        env={"CONFLUENCE_PAT": "tok123", "CONFLUENCE_USERNAME": "alice", "CONFLUENCE_PASSWORD": "secret"}
    )
    assert isinstance(cred, BearerCredential)
    assert cred.token == "tok123"


def test_load_credential_basic_when_no_pat():
    cred = load_credential(env={"CONFLUENCE_USERNAME": "alice", "CONFLUENCE_PASSWORD": "secret"})
    assert isinstance(cred, BasicCredential)
    assert cred.username == "alice"
    assert cred.password == "secret"


def test_load_credential_raises_when_nothing_configured():
    with pytest.raises(ConfigurationError, match="CONFLUENCE_USERNAME"):
        load_credential(env={})


def test_load_credential_raises_when_only_username_set():
    with pytest.raises(ConfigurationError, match="CONFLUENCE_PASSWORD"):
        load_credential(env={"CONFLUENCE_USERNAME": "alice"})


def test_basic_credential_repr_never_leaks_password():
    cred = BasicCredential(username="alice", password="super-secret")
    assert "super-secret" not in repr(cred)


def test_bearer_credential_repr_never_leaks_token():
    cred = BearerCredential(token="super-secret-token")
    assert "super-secret-token" not in repr(cred)


def test_bearer_credential_apply_sets_authorization_header():
    from unittest.mock import MagicMock

    session = MagicMock()
    session.headers = {}
    BearerCredential(token="tok123").apply(session)
    assert session.headers["Authorization"] == "Bearer tok123"


def test_basic_credential_apply_sets_session_auth():
    from unittest.mock import MagicMock

    session = MagicMock()
    BasicCredential(username="alice", password="secret").apply(session)
    assert session.auth == ("alice", "secret")
