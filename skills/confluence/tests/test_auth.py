import pytest

from lib.auth import ConfigurationError, load_config


def test_load_config_requires_base_url():
    with pytest.raises(ConfigurationError, match="CONFLUENCE_BASE_URL"):
        load_config(env={})


def test_load_config_strips_trailing_slash():
    config = load_config(
        env={
            "CONFLUENCE_BASE_URL": "https://confluence.example.com/",
            "CONFLUENCE_DEPLOYMENT_TYPE": "server",
        }
    )
    assert config.base_url == "https://confluence.example.com"


def test_load_config_rejects_base_url_without_scheme():
    with pytest.raises(ConfigurationError, match="http"):
        load_config(
            env={"CONFLUENCE_BASE_URL": "confluence.example.com", "CONFLUENCE_DEPLOYMENT_TYPE": "server"}
        )


def test_load_config_requires_deployment_type_unlike_jira():
    """Unlike JIRA_DEPLOYMENT_TYPE (optional), CONFLUENCE_DEPLOYMENT_TYPE is
    required -- Confluence's REST path itself differs by deployment."""
    with pytest.raises(ConfigurationError, match="CONFLUENCE_DEPLOYMENT_TYPE"):
        load_config(env={"CONFLUENCE_BASE_URL": "https://confluence.example.com"})


def test_load_config_rejects_invalid_deployment_type():
    with pytest.raises(ConfigurationError, match="cloud.*server|server.*cloud"):
        load_config(
            env={
                "CONFLUENCE_BASE_URL": "https://confluence.example.com",
                "CONFLUENCE_DEPLOYMENT_TYPE": "datacenter",
            }
        )


def test_load_config_deployment_type_is_case_insensitive():
    config = load_config(
        env={"CONFLUENCE_BASE_URL": "https://confluence.example.com", "CONFLUENCE_DEPLOYMENT_TYPE": "CLOUD"}
    )
    assert config.deployment_type == "cloud"


def test_load_config_auto_confirm_writes_defaults_false():
    config = load_config(
        env={"CONFLUENCE_BASE_URL": "https://confluence.example.com", "CONFLUENCE_DEPLOYMENT_TYPE": "server"}
    )
    assert config.auto_confirm_writes is False


def test_load_config_auto_confirm_writes_can_be_enabled():
    config = load_config(
        env={
            "CONFLUENCE_BASE_URL": "https://confluence.example.com",
            "CONFLUENCE_DEPLOYMENT_TYPE": "server",
            "CONFLUENCE_AUTO_CONFIRM_WRITES": "true",
        }
    )
    assert config.auto_confirm_writes is True


def test_load_config_default_space_optional():
    config = load_config(
        env={"CONFLUENCE_BASE_URL": "https://confluence.example.com", "CONFLUENCE_DEPLOYMENT_TYPE": "server"}
    )
    assert config.default_space is None
