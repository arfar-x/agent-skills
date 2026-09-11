import os
import sys
from unittest.mock import MagicMock

import pytest

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SKILL_ROOT not in sys.path:
    sys.path.insert(0, SKILL_ROOT)

from lib.auth import ConfluenceConfig  # noqa: E402
from lib.confluence_client import ConfluenceClient, reset_client  # noqa: E402
from lib.credentials import BasicCredential  # noqa: E402


@pytest.fixture
def confluence_config() -> ConfluenceConfig:
    return ConfluenceConfig(
        base_url="https://confluence.example.com",
        deployment_type="server",
        max_retries=0,
    )


@pytest.fixture
def confluence_config_cloud() -> ConfluenceConfig:
    return ConfluenceConfig(
        base_url="https://example.atlassian.net",
        deployment_type="cloud",
        max_retries=0,
    )


@pytest.fixture
def confluence_credential() -> BasicCredential:
    return BasicCredential(username="alice", password="secret")


@pytest.fixture
def mock_session():
    return MagicMock()


@pytest.fixture
def client(confluence_config, confluence_credential, mock_session) -> ConfluenceClient:
    return ConfluenceClient(config=confluence_config, credential=confluence_credential, session=mock_session)


@pytest.fixture(autouse=True)
def _reset_singleton():
    yield
    reset_client()


def make_response(status_code=200, json_data=None, headers=None, text=""):
    response = MagicMock()
    response.status_code = status_code
    response.ok = 200 <= status_code < 400
    response.headers = headers or {}
    response.text = text
    response.content = b"x" if (json_data is not None or text) else b""
    response.json.return_value = json_data if json_data is not None else {}
    response.reason = "Error"
    return response
