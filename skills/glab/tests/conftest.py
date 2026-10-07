import os
import sys
from unittest.mock import MagicMock

import pytest

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SKILL_ROOT not in sys.path:
    sys.path.insert(0, SKILL_ROOT)

from lib.auth import GitLabConfig  # noqa: E402
from lib.credentials import BearerCredential  # noqa: E402
from lib.glab_client import GitLabClient, reset_client  # noqa: E402


@pytest.fixture
def config() -> GitLabConfig:
    return GitLabConfig(base_url="https://gitlab.example.com", max_retries=0)


@pytest.fixture
def mock_session():
    return MagicMock()


@pytest.fixture
def client(config, mock_session) -> GitLabClient:
    return GitLabClient(config=config, credential=BearerCredential("tok"), session=mock_session)


@pytest.fixture(autouse=True)
def _reset_singleton():
    yield
    reset_client()


def make_response(status_code=200, json_data=None, headers=None, text="", content=None):
    response = MagicMock()
    response.status_code = status_code
    response.ok = 200 <= status_code < 400
    response.headers = headers or {}
    response.text = text
    response.reason = "reason"
    if content is None:
        content = b"{}" if json_data is not None else (text.encode() if text else b"")
    response.content = content
    response.json.return_value = json_data
    return response


DIFF_REFS = {"base_sha": "b", "start_sha": "s", "head_sha": "h"}

SAMPLE_DIFF = (
    "@@ -1,4 +1,5 @@\n"
    " ctx1\n"
    "-removed\n"
    "+added1\n"
    "+added2\n"
    " ctx2\n"
)
