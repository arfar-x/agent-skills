import pytest

from lib.auth import ConfigurationError, load_config


def test_base_url_loads_successfully():
    config = load_config(env={"JIRA_BASE_URL": "https://jira.example.com/"})
    assert config.base_url == "https://jira.example.com"


def test_missing_base_url_raises():
    with pytest.raises(ConfigurationError, match="JIRA_BASE_URL"):
        load_config(env={})


def test_base_url_without_scheme_raises():
    with pytest.raises(ConfigurationError, match="http"):
        load_config(env={"JIRA_BASE_URL": "jira.example.com"})


def test_auto_confirm_writes_defaults_false():
    config = load_config(env={"JIRA_BASE_URL": "https://jira.example.com"})
    assert config.auto_confirm_writes is False


def test_auto_confirm_writes_can_be_enabled():
    config = load_config(
        env={
            "JIRA_BASE_URL": "https://jira.example.com",
            "JIRA_AUTO_CONFIRM_WRITES": "true",
        }
    )
    assert config.auto_confirm_writes is True


def test_deployment_type_defaults_unset():
    config = load_config(env={"JIRA_BASE_URL": "https://jira.example.com"})
    assert config.deployment_type is None


@pytest.mark.parametrize("raw,expected", [("cloud", "cloud"), ("Server", "server"), (" CLOUD ", "cloud")])
def test_deployment_type_accepted_case_insensitively(raw, expected):
    config = load_config(
        env={
            "JIRA_BASE_URL": "https://jira.example.com",
            "JIRA_DEPLOYMENT_TYPE": raw,
        }
    )
    assert config.deployment_type == expected


def test_deployment_type_rejects_unknown_value():
    with pytest.raises(ConfigurationError, match="JIRA_DEPLOYMENT_TYPE"):
        load_config(
            env={
                "JIRA_BASE_URL": "https://jira.example.com",
                "JIRA_DEPLOYMENT_TYPE": "datacenter",
            }
        )
