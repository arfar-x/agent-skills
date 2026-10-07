import pytest

from lib.auth import ConfigurationError, load_config, load_credential
from lib.credentials import BearerCredential


def test_load_credential_token():
    assert isinstance(load_credential({"GITLAB_TOKEN": " abc "}), BearerCredential)
    assert load_credential({"GITLAB_TOKEN": " abc "}).token == "abc"


def test_load_credential_missing():
    with pytest.raises(ConfigurationError, match="GITLAB_TOKEN"):
        load_credential({})


def test_load_config_defaults_and_overrides():
    cfg = load_config({"GITLAB_BASE_URL": "https://g.example.com/", "GITLAB_AUTO_CONFIRM_WRITES": "true",
                       "GITLAB_DEFAULT_PROJECT": "grp/proj"})
    assert cfg.base_url == "https://g.example.com"
    assert cfg.auto_confirm_writes is True
    assert cfg.default_project == "grp/proj"
    assert cfg.verify_ssl is True


@pytest.mark.parametrize("env", [{}, {"GITLAB_BASE_URL": "gitlab.example.com"}, {"GITLAB_BASE_URL": "https://x", "GITLAB_MAX_RETRIES": "x"}])
def test_load_config_invalid(env):
    with pytest.raises(ConfigurationError):
        load_config(env)


def test_credential_repr_hides_token():
    assert "abc" not in repr(load_credential({"GITLAB_TOKEN": "abc"}))
