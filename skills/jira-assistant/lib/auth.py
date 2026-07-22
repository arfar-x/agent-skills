"""Authentication and configuration handling for the Jira Assistant skill.

Credentials are always sourced from environment variables. No credentials
may be hard-coded or embedded in source. Supports two authentication
modes against self-hosted (or cloud) Jira instances:

* Basic auth (username + password) -- the default.
* Personal Access Token (PAT / bearer token) -- opt-in via
  ``JIRA_AUTH_MODE=pat``.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Optional

logger = logging.getLogger("jira_skill.auth")


class AuthMode(str, Enum):
    """Supported authentication strategies."""

    BASIC = "basic"
    PAT = "pat"


class ConfigurationError(RuntimeError):
    """Raised when the skill is misconfigured (missing/invalid env vars)."""


@dataclass(frozen=True)
class JiraConfig:
    """Validated runtime configuration for the Jira client.

    Attributes:
        base_url: Root URL of the Jira instance, e.g. ``https://jira.example.com``.
        auth_mode: Which authentication strategy to use.
        username: Basic-auth username. Required when ``auth_mode`` is BASIC.
        password: Basic-auth password. Required when ``auth_mode`` is BASIC.
        api_token: Personal access token. Required when ``auth_mode`` is PAT.
        timeout_seconds: Per-request network timeout.
        max_retries: Maximum retry attempts for idempotent/rate-limited requests.
        verify_ssl: Whether to verify TLS certificates (disable only for
            trusted internal instances with self-signed certs).
        auto_confirm_writes: When True, write operations (transition,
            worklog, comment) execute without requiring explicit
            confirmation from the caller.
    """

    base_url: str
    auth_mode: AuthMode
    username: Optional[str] = None
    password: Optional[str] = None
    api_token: Optional[str] = None
    timeout_seconds: float = 30.0
    max_retries: int = 3
    verify_ssl: bool = True
    auto_confirm_writes: bool = False

    def auth_summary(self) -> str:
        """Return a redacted, human-readable description of the auth mode."""
        if self.auth_mode is AuthMode.PAT:
            return "Personal Access Token (bearer)"
        return f"Basic auth (user={self.username})"


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


def load_config(env: Optional[Mapping[str, str]] = None) -> JiraConfig:
    """Load and validate Jira configuration from environment variables.

    Args:
        env: Optional explicit mapping to read from instead of the
            process environment (primarily for testing).

    Raises:
        ConfigurationError: If required variables are missing or
            inconsistent. The message identifies exactly what is wrong so
            operators can fix configuration without reading source code.

    Environment variables:
        JIRA_BASE_URL (required): Root URL of the Jira instance.
        JIRA_AUTH_MODE (optional): "basic" (default) or "pat".
        JIRA_USERNAME / JIRA_PASSWORD (required for basic auth).
        JIRA_API_TOKEN (required for PAT auth).
        JIRA_TIMEOUT_SECONDS (optional, default 30).
        JIRA_MAX_RETRIES (optional, default 3).
        JIRA_VERIFY_SSL (optional, default true).
        JIRA_AUTO_CONFIRM_WRITES (optional, default false).
    """
    source: Mapping[str, str] = env if env is not None else os.environ

    base_url = _env(source, "JIRA_BASE_URL")
    if not base_url:
        raise ConfigurationError(
            "JIRA_BASE_URL is not set. Configure it to the root URL of your "
            "Jira instance, e.g. https://jira.mycompany.com"
        )
    base_url = base_url.rstrip("/")
    if not (base_url.startswith("http://") or base_url.startswith("https://")):
        raise ConfigurationError(
            f"JIRA_BASE_URL={base_url!r} must start with http:// or https://"
        )

    auth_mode_raw = (_env(source, "JIRA_AUTH_MODE", "basic") or "basic").lower()
    try:
        auth_mode = AuthMode(auth_mode_raw)
    except ValueError as exc:
        raise ConfigurationError(
            f"JIRA_AUTH_MODE={auth_mode_raw!r} is invalid. Must be 'basic' or 'pat'."
        ) from exc

    username = _env(source, "JIRA_USERNAME")
    password = _env(source, "JIRA_PASSWORD")
    api_token = _env(source, "JIRA_API_TOKEN")

    if auth_mode is AuthMode.BASIC:
        missing = [
            name
            for name, value in (("JIRA_USERNAME", username), ("JIRA_PASSWORD", password))
            if not value
        ]
        if missing:
            raise ConfigurationError(
                "Basic authentication selected (JIRA_AUTH_MODE=basic, the default) "
                f"but the following environment variables are missing: {', '.join(missing)}"
            )
    else:  # PAT
        if not api_token:
            raise ConfigurationError(
                "JIRA_AUTH_MODE=pat selected but JIRA_API_TOKEN is not set."
            )

    config = JiraConfig(
        base_url=base_url,
        auth_mode=auth_mode,
        username=username,
        password=password,
        api_token=api_token,
        timeout_seconds=_env_float(source, "JIRA_TIMEOUT_SECONDS", 30.0),
        max_retries=_env_int(source, "JIRA_MAX_RETRIES", 3),
        verify_ssl=_env_bool(source, "JIRA_VERIFY_SSL", True),
        auto_confirm_writes=_env_bool(source, "JIRA_AUTO_CONFIRM_WRITES", False),
    )
    logger.info(
        "Loaded Jira configuration: base_url=%s auth=%s auto_confirm_writes=%s",
        config.base_url,
        config.auth_summary(),
        config.auto_confirm_writes,
    )
    return config
