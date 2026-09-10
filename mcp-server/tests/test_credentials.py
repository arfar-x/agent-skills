from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import lib.credentials as credentials


def _manifest(required_env=(), toolset="jira"):
    return SimpleNamespace(toolset=toolset, required_environment_variables=required_env)


def setup_function():
    # credentials.configure() sets process-lifetime state -- reset it (and
    # the one-shot warning flag) before every test so tests don't leak
    # into each other via module-level state.
    credentials.configure(trust_request_credentials=False)
    credentials._warned_untrusted_headers_seen = False


@patch("lib.credentials._get_http_headers", return_value={})
def test_resolve_env_with_no_headers_uses_process_env(mock_headers, monkeypatch):
    monkeypatch.setenv("JIRA_BASE_URL", "https://jira.example.com")
    manifest = _manifest(required_env=({"name": "JIRA_BASE_URL", "required_for": "all functionality"},))
    env = credentials.resolve_env(manifest, trust_request_credentials=False)
    assert env["JIRA_BASE_URL"] == "https://jira.example.com"


@patch(
    "lib.credentials._get_http_headers",
    return_value={"x-agent-skills-env-jira_password": "from-header"},
)
def test_untrusted_header_is_ignored_and_falls_back_to_process_env(mock_headers, monkeypatch):
    monkeypatch.setenv("JIRA_PASSWORD", "from-process-env")
    manifest = _manifest(required_env=({"name": "JIRA_PASSWORD", "required_for": "all functionality"},))
    env = credentials.resolve_env(manifest, trust_request_credentials=False)
    assert env["JIRA_PASSWORD"] == "from-process-env"


@patch(
    "lib.credentials._get_http_headers",
    return_value={"x-agent-skills-env-jira_password": "from-header"},
)
def test_trusted_header_overrides_process_env(mock_headers, monkeypatch):
    monkeypatch.setenv("JIRA_PASSWORD", "from-process-env")
    manifest = _manifest(required_env=({"name": "JIRA_PASSWORD", "required_for": "all functionality"},))
    env = credentials.resolve_env(manifest, trust_request_credentials=True)
    assert env["JIRA_PASSWORD"] == "from-header"


@patch(
    "lib.credentials._get_http_headers",
    return_value={"x-agent-skills-env-telegram_api_id": "999"},
)
def test_header_for_an_undeclared_var_is_never_injected_even_when_trusted(mock_headers, monkeypatch):
    manifest = _manifest(required_env=({"name": "JIRA_BASE_URL", "required_for": "all functionality"},))
    env = credentials.resolve_env(manifest, trust_request_credentials=True)
    assert "TELEGRAM_API_ID" not in env


@patch("lib.credentials._get_http_headers", return_value={})
def test_env_is_scoped_to_declared_vars_not_the_whole_process_env(mock_headers, monkeypatch):
    monkeypatch.setenv("JIRA_BASE_URL", "https://jira.example.com")
    monkeypatch.setenv("TELEGRAM_API_ID", "some-other-toolsets-secret")
    manifest = _manifest(required_env=({"name": "JIRA_BASE_URL", "required_for": "all functionality"},))
    env = credentials.resolve_env(manifest, trust_request_credentials=False)
    assert "TELEGRAM_API_ID" not in env


@patch("lib.credentials._get_http_headers", return_value={})
def test_infra_vars_pass_through_when_present(mock_headers, monkeypatch):
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    manifest = _manifest(required_env=())
    env = credentials.resolve_env(manifest, trust_request_credentials=False)
    assert env["PATH"] == "/usr/bin:/bin"


def test_is_trusted_reflects_configure():
    credentials.configure(trust_request_credentials=True)
    assert credentials.is_trusted() is True
    credentials.configure(trust_request_credentials=False)
    assert credentials.is_trusted() is False


def test_resolve_trust_cli_flag_wins(monkeypatch):
    monkeypatch.delenv("MCP_TRUST_REQUEST_CREDENTIALS", raising=False)
    assert credentials.resolve_trust_request_credentials(True) is True


def test_resolve_trust_falls_back_to_env_var(monkeypatch):
    monkeypatch.setenv("MCP_TRUST_REQUEST_CREDENTIALS", "1")
    assert credentials.resolve_trust_request_credentials(False) is True


def test_resolve_trust_defaults_false(monkeypatch):
    monkeypatch.delenv("MCP_TRUST_REQUEST_CREDENTIALS", raising=False)
    assert credentials.resolve_trust_request_credentials(False) is False
