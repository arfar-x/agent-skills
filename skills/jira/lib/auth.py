"""Authentication and configuration handling for the Jira Assistant skill.

Credentials are always sourced from environment variables. No credentials
may be hard-coded or embedded in source. Two auth modes are supported:
HTTP Basic (username + password) and a single bearer token (a Jira Data
Center Personal Access Token, or an OAuth access token if one is ever
supplied this way) -- see `load_credential()`.

Credential material (`load_credential()`, returning a
`lib.credentials.Credential`) is deliberately kept separate from
`JiraConfig`, which holds only *behavioral* settings (timeouts, retries,
which project to default to, ...). `JiraClient` accepts whichever
`Credential` it's handed and never inspects how it was obtained --
whether that's this process's own environment (personal/direct use) or
a credential resolved per-request by `mcp-server` on behalf of one
specific caller behind a multi-user chat client.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Mapping, Optional

from .credentials import BasicCredential, BearerCredential, Credential

logger = logging.getLogger("jira_skill.auth")


class ConfigurationError(RuntimeError):
    """Raised when the skill is misconfigured (missing/invalid env vars)."""


@dataclass(frozen=True)
class JiraConfig:
    """Validated runtime configuration for the Jira client.

    Deliberately holds no credential material -- see `load_credential()`
    for that. Everything here is a behavioral setting, independent of
    which auth mode is in use.

    Attributes:
        base_url: Root URL of the Jira instance, e.g. ``https://jira.example.com``.
        timeout_seconds: Per-request network timeout.
        max_retries: Maximum retry attempts for idempotent/rate-limited requests.
        verify_ssl: Whether to verify TLS certificates (disable only for
            trusted internal instances with self-signed certs).
        auto_confirm_writes: When True, write operations (transition,
            worklog, comment) execute without requiring explicit
            confirmation from the caller.
        default_project: Optional Jira project key (e.g. ``PAYKAN``) used
            by tools that need a project scope (e.g. ``triage``) when the
            caller doesn't pass one explicitly. If unset, callers must
            resolve/pass a project themselves -- never guessed in code.
        deployment_type: ``"cloud"`` or ``"server"`` (the latter also
            covers Data Center). Jira Cloud identifies users by
            ``accountId``; Server/Data Center has no such concept and
            uses the username under ``name`` instead -- the two shapes
            aren't interchangeable. Only needed for setting an assignee
            (``create_issue``/``edit_issue``); if unset, that fails
            clearly rather than guessing one shape.
    """

    base_url: str
    timeout_seconds: float = 30.0
    max_retries: int = 3
    verify_ssl: bool = True
    auto_confirm_writes: bool = False
    default_project: Optional[str] = None
    deployment_type: Optional[str] = None


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
    """Load and validate Jira auth credentials from environment variables.

    Two modes, checked in this order:

    1. ``JIRA_PAT`` set -- a bearer token (a Jira Data Center Personal
       Access Token, or any other single-token credential the deployment
       hands this skill the same way). Takes precedence over Basic auth
       if both happen to be set, since a PAT is the more specific choice
       when someone has gone to the trouble of minting one.
    2. ``JIRA_USERNAME`` + ``JIRA_PASSWORD`` both set -- HTTP Basic auth.

    Args:
        env: Optional explicit mapping to read from instead of the
            process environment (primarily for testing, and this is
            also the seam `mcp-server` uses to hand this skill a
            per-request credential instead of its own process env).

    Raises:
        ConfigurationError: If neither mode is fully configured. The
            message names both options so operators aren't left
            guessing which env vars to set.
    """
    source: Mapping[str, str] = env if env is not None else os.environ

    pat = _env(source, "JIRA_PAT")
    if pat:
        return BearerCredential(token=pat)

    username = _env(source, "JIRA_USERNAME")
    password = _env(source, "JIRA_PASSWORD")
    if username and password:
        return BasicCredential(username=username, password=password)

    missing = [name for name, value in (("JIRA_USERNAME", username), ("JIRA_PASSWORD", password)) if not value]
    raise ConfigurationError(
        "No Jira credential configured. Set either JIRA_PAT (a Personal "
        "Access Token or other bearer token), or both JIRA_USERNAME and "
        "JIRA_PASSWORD for Basic auth. Currently missing: "
        f"{', '.join(missing) if missing else 'JIRA_USERNAME, JIRA_PASSWORD'} "
        "(and JIRA_PAT is not set)."
    )


def load_config(env: Optional[Mapping[str, str]] = None) -> JiraConfig:
    """Load and validate Jira behavioral configuration from environment
    variables. Does not touch credential material -- see
    `load_credential()` for that.

    Args:
        env: Optional explicit mapping to read from instead of the
            process environment (primarily for testing).

    Raises:
        ConfigurationError: If required variables are missing or
            inconsistent. The message identifies exactly what is wrong so
            operators can fix configuration without reading source code.

    Environment variables:
        JIRA_BASE_URL (required): Root URL of the Jira instance.
        JIRA_TIMEOUT_SECONDS (optional, default 30).
        JIRA_MAX_RETRIES (optional, default 3).
        JIRA_VERIFY_SSL (optional, default true).
        JIRA_AUTO_CONFIRM_WRITES (optional, default false).
        JIRA_DEFAULT_PROJECT (optional, default unset).
        JIRA_DEPLOYMENT_TYPE (optional, default unset): "cloud" or
            "server" -- only required for setting an assignee.
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

    deployment_type_raw = _env(source, "JIRA_DEPLOYMENT_TYPE")
    deployment_type = None
    if deployment_type_raw:
        deployment_type = deployment_type_raw.strip().lower()
        if deployment_type not in {"cloud", "server"}:
            raise ConfigurationError(
                f"JIRA_DEPLOYMENT_TYPE={deployment_type_raw!r} must be 'cloud' "
                "or 'server' ('server' also covers Data Center)."
            )

    config = JiraConfig(
        base_url=base_url,
        timeout_seconds=_env_float(source, "JIRA_TIMEOUT_SECONDS", 30.0),
        max_retries=_env_int(source, "JIRA_MAX_RETRIES", 3),
        verify_ssl=_env_bool(source, "JIRA_VERIFY_SSL", True),
        auto_confirm_writes=_env_bool(source, "JIRA_AUTO_CONFIRM_WRITES", False),
        default_project=_env(source, "JIRA_DEFAULT_PROJECT"),
        deployment_type=deployment_type,
    )
    logger.info("Loaded Jira configuration: base_url=%s auto_confirm_writes=%s", config.base_url, config.auto_confirm_writes)
    return config
