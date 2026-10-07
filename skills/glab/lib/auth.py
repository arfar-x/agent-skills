"""Authentication and configuration handling for the GitLab (glab) skill.

Credentials always come from environment variables. One auth mode is
supported: ``GITLAB_TOKEN`` -- a GitLab personal / project / group access
token, sent as ``Authorization: Bearer <token>`` (GitLab's REST API
accepts this alongside its own ``PRIVATE-TOKEN`` header). GitLab's REST
API has no username/password mode; the only password route is the OAuth
password grant, which newer versions disable by default and which cannot
work with 2FA, so it is deliberately not offered.

Credential material (`load_credential()`) is kept separate from
`GitLabConfig`, which holds only behavioral settings -- same split as
`confluence/lib/auth.py`.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Mapping, Optional

from .credentials import BearerCredential, Credential

logger = logging.getLogger("glab_skill.auth")


class ConfigurationError(RuntimeError):
    """Raised when the skill is misconfigured (missing/invalid env vars)."""


@dataclass(frozen=True)
class GitLabConfig:
    """Validated runtime configuration for the GitLab client.

    Attributes:
        base_url: Root URL of the GitLab instance, e.g.
            ``https://gitlab.mycompany.com`` (no ``/api/v4`` suffix).
        timeout_seconds: Per-request network timeout.
        max_retries: Maximum retry attempts for idempotent/rate-limited requests.
        verify_ssl: Whether to verify TLS certificates (disable only for
            trusted internal instances with self-signed certs).
        auto_confirm_writes: When True, write operations (add_mr_note,
            add_mr_discussion) execute without an explicit confirm.
        default_project: Optional project id or ``group/project`` path used
            when a tool is called without ``--project``.
    """

    base_url: str
    timeout_seconds: float = 30.0
    max_retries: int = 3
    verify_ssl: bool = True
    auto_confirm_writes: bool = False
    default_project: Optional[str] = None


def _env(source: Mapping[str, str], name: str, default: Optional[str] = None) -> Optional[str]:
    value = source.get(name, default)
    if value is not None:
        value = value.strip()
    return value or default


def _env_bool(source: Mapping[str, str], name: str, default: bool) -> bool:
    raw = source.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(source: Mapping[str, str], name: str, default: float) -> float:
    raw = source.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigurationError(f"Environment variable {name}={raw!r} is not a valid number") from exc


def _env_int(source: Mapping[str, str], name: str, default: int) -> int:
    raw = source.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"Environment variable {name}={raw!r} is not a valid integer") from exc


def load_credential(env: Optional[Mapping[str, str]] = None) -> Credential:
    """Load the GitLab token from the environment.

    Args:
        env: Optional explicit mapping instead of the process environment
            (testing, and the seam `mcp-server` uses for per-request creds).

    Raises:
        ConfigurationError: If ``GITLAB_TOKEN`` is not set.
    """
    source: Mapping[str, str] = env if env is not None else os.environ
    token = _env(source, "GITLAB_TOKEN")
    if token:
        return BearerCredential(token=token)
    raise ConfigurationError(
        "No GitLab credential configured. Set GITLAB_TOKEN to a personal access "
        "token (scope `read_api` for read-only use, `api` to post MR comments)."
    )


def load_config(env: Optional[Mapping[str, str]] = None) -> GitLabConfig:
    """Load and validate GitLab behavioral configuration from the environment.

    Environment variables:
        GITLAB_BASE_URL (required): Root URL of the GitLab instance.
        GITLAB_TIMEOUT_SECONDS (optional, default 30).
        GITLAB_MAX_RETRIES (optional, default 3).
        GITLAB_VERIFY_SSL (optional, default true).
        GITLAB_AUTO_CONFIRM_WRITES (optional, default false).
        GITLAB_DEFAULT_PROJECT (optional, default unset).
    """
    source: Mapping[str, str] = env if env is not None else os.environ

    base_url = _env(source, "GITLAB_BASE_URL")
    if not base_url:
        raise ConfigurationError(
            "GITLAB_BASE_URL is not set. Configure it to the root URL of your "
            "GitLab instance, e.g. https://gitlab.mycompany.com"
        )
    base_url = base_url.rstrip("/")
    if not (base_url.startswith("http://") or base_url.startswith("https://")):
        raise ConfigurationError(f"GITLAB_BASE_URL={base_url!r} must start with http:// or https://")

    config = GitLabConfig(
        base_url=base_url,
        timeout_seconds=_env_float(source, "GITLAB_TIMEOUT_SECONDS", 30.0),
        max_retries=_env_int(source, "GITLAB_MAX_RETRIES", 3),
        verify_ssl=_env_bool(source, "GITLAB_VERIFY_SSL", True),
        auto_confirm_writes=_env_bool(source, "GITLAB_AUTO_CONFIRM_WRITES", False),
        default_project=_env(source, "GITLAB_DEFAULT_PROJECT"),
    )
    logger.info(
        "Loaded GitLab configuration: base_url=%s auto_confirm_writes=%s",
        config.base_url,
        config.auto_confirm_writes,
    )
    return config
