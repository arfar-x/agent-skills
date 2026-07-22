import pytest

from lib.auth import AuthMode, ConfigurationError, load_config


def test_basic_auth_loads_successfully():
    config = load_config(
        env={
            "JIRA_BASE_URL": "https://jira.example.com/",
            "JIRA_USERNAME": "alice",
            "JIRA_PASSWORD": "secret",
        }
    )
    assert config.base_url == "https://jira.example.com"
    assert config.auth_mode is AuthMode.BASIC
    assert config.username == "alice"


def test_missing_base_url_raises():
    with pytest.raises(ConfigurationError, match="JIRA_BASE_URL"):
        load_config(env={"JIRA_USERNAME": "alice", "JIRA_PASSWORD": "secret"})


def test_base_url_without_scheme_raises():
    with pytest.raises(ConfigurationError, match="http"):
        load_config(
            env={
                "JIRA_BASE_URL": "jira.example.com",
                "JIRA_USERNAME": "alice",
                "JIRA_PASSWORD": "secret",
            }
        )


def test_basic_auth_missing_username_raises():
    with pytest.raises(ConfigurationError, match="JIRA_USERNAME"):
        load_config(env={"JIRA_BASE_URL": "https://jira.example.com", "JIRA_PASSWORD": "secret"})


def test_pat_auth_requires_token():
    with pytest.raises(ConfigurationError, match="JIRA_API_TOKEN"):
        load_config(env={"JIRA_BASE_URL": "https://jira.example.com", "JIRA_AUTH_MODE": "pat"})


def test_pat_auth_loads_successfully():
    config = load_config(
        env={
            "JIRA_BASE_URL": "https://jira.example.com",
            "JIRA_AUTH_MODE": "pat",
            "JIRA_API_TOKEN": "tok_123",
        }
    )
    assert config.auth_mode is AuthMode.PAT
    assert config.api_token == "tok_123"


def test_invalid_auth_mode_raises():
    with pytest.raises(ConfigurationError, match="JIRA_AUTH_MODE"):
        load_config(
            env={
                "JIRA_BASE_URL": "https://jira.example.com",
                "JIRA_AUTH_MODE": "oauth",
            }
        )


def test_auto_confirm_writes_defaults_false():
    config = load_config(
        env={
            "JIRA_BASE_URL": "https://jira.example.com",
            "JIRA_USERNAME": "alice",
            "JIRA_PASSWORD": "secret",
        }
    )
    assert config.auto_confirm_writes is False


def test_auto_confirm_writes_can_be_enabled():
    config = load_config(
        env={
            "JIRA_BASE_URL": "https://jira.example.com",
            "JIRA_USERNAME": "alice",
            "JIRA_PASSWORD": "secret",
            "JIRA_AUTO_CONFIRM_WRITES": "true",
        }
    )
    assert config.auto_confirm_writes is True
