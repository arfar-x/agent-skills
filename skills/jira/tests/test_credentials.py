"""Tests for lib.auth.load_credential() and the shared Credential types
it returns (lib.credentials, symlinked from skills/_shared/credentials/http.py
-- these tests exercise them through that real symlinked import path, the
same way production code does).
"""

from unittest.mock import MagicMock

import pytest

from lib.auth import ConfigurationError, load_credential
from lib.credentials import BasicCredential, BearerCredential, NoCredential


def test_basic_credential_loads_from_username_and_password():
    credential = load_credential(env={"JIRA_USERNAME": "alice", "JIRA_PASSWORD": "secret"})
    assert isinstance(credential, BasicCredential)
    assert credential.username == "alice"
    assert credential.password == "secret"


def test_bearer_credential_loads_from_pat():
    credential = load_credential(env={"JIRA_PAT": "sometoken"})
    assert isinstance(credential, BearerCredential)
    assert credential.token == "sometoken"


def test_pat_takes_precedence_over_basic_when_both_set():
    credential = load_credential(
        env={"JIRA_PAT": "sometoken", "JIRA_USERNAME": "alice", "JIRA_PASSWORD": "secret"}
    )
    assert isinstance(credential, BearerCredential)


def test_missing_both_modes_raises_naming_both_options():
    with pytest.raises(ConfigurationError, match="JIRA_PAT"):
        load_credential(env={})


def test_partial_basic_missing_password_raises():
    with pytest.raises(ConfigurationError, match="JIRA_PASSWORD"):
        load_credential(env={"JIRA_USERNAME": "alice"})


def test_partial_basic_missing_username_raises():
    with pytest.raises(ConfigurationError, match="JIRA_USERNAME"):
        load_credential(env={"JIRA_PASSWORD": "secret"})


def test_basic_credential_apply_sets_session_auth():
    session = MagicMock()
    BasicCredential(username="alice", password="secret").apply(session)
    assert session.auth == ("alice", "secret")


def test_bearer_credential_apply_sets_authorization_header():
    session = MagicMock()
    session.headers = {}
    BearerCredential(token="sometoken").apply(session)
    assert session.headers["Authorization"] == "Bearer sometoken"


def test_no_credential_apply_is_a_pure_noop():
    session = MagicMock()
    result = NoCredential().apply(session)
    assert result is None
    # A real assignment (as BasicCredential does) would make session.auth a
    # tuple; NoCredential must never touch it at all.
    assert not isinstance(session.auth, tuple)


@pytest.mark.parametrize(
    "credential",
    [BasicCredential(username="alice", password="hunter2"), BearerCredential(token="sk-secretvalue")],
)
def test_credential_repr_never_exposes_the_secret(credential):
    text = repr(credential)
    assert "hunter2" not in text
    assert "sk-secretvalue" not in text
