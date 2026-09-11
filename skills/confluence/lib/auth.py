"""Authentication and configuration handling for the Confluence Assistant skill.

Credentials are always sourced from environment variables. No credentials
may be hard-coded or embedded in source. Two auth modes are supported,
identical in shape to the `jira` toolset's: HTTP Basic (username +
password) and a single bearer token (a Confluence Data Center Personal
Access Token, a Confluence Cloud API token used as a bearer token, or an
OAuth access token if one is ever supplied this way) -- see
`load_credential()`.

Credential material (`load_credential()`, returning a
`lib.credentials.Credential`) is deliberately kept separate from
`ConfluenceConfig`, which holds only *behavioral* settings (timeouts,
retries, which space to default to, which REST path this deployment
uses, ...). `ConfluenceClient` accepts whichever `Credential` it's
handed and never inspects how it was obtained -- whether that's this
process's own environment (personal/direct use) or a credential
resolved per-request by `mcp-server` on behalf of one specific caller
behind a multi-user chat client.

One deliberate difference from `jira/lib/auth.py`: Jira uses the same
`/rest/api/2` path for both Cloud and Server/Data Center, so
`JIRA_DEPLOYMENT_TYPE` is optional there (only needed for the assignee
field shape). Confluence's REST API is mounted at a different path per
deployment -- Cloud under `/wiki/rest/api`, Server/Data Center directly
under `/rest/api` -- so every single request needs to know which one to
use. `CONFLUENCE_DEPLOYMENT_TYPE` is therefore **required** here, not
optional-until-needed.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Mapping, Optional

from .credentials import BasicCredential, BearerCredential, Credential

logger = logging.getLogger("confluence_skill.auth")

#: "server" also covers Data Center -- same convention `jira` uses.
VALID_DEPLOYMENT_TYPES = {"cloud", "server"}


class ConfigurationError(RuntimeError):
    """Raised when the skill is misconfigured (missing/invalid env vars)."""


@dataclass(frozen=True)
class ConfluenceConfig:
    """Validated runtime configuration for the Confluence client.

    Deliberately holds no credential material -- see `load_credential()`
    for that. Everything here is a behavioral setting, independent of
    which auth mode is in use.

    Attributes:
        base_url: Root URL of the Confluence instance, e.g.
            ``https://mycompany.atlassian.net`` (Cloud) or
            ``https://confluence.mycompany.com`` (Server/Data Center).
        deployment_type: ``"cloud"`` or ``"server"`` (the latter also
            covers Data Center). Unlike Jira, this is required: it picks
            the REST path prefix every request uses (see
            `ConfluenceClient._API_PATH`), not just one narrow field
            shape.
        timeout_seconds: Per-request network timeout.
        max_retries: Maximum retry attempts for idempotent/rate-limited requests.
        verify_ssl: Whether to verify TLS certificates (disable only for
            trusted internal instances with self-signed certs).
        auto_confirm_writes: When True, write operations (create_page,
            update_page, delete_page, add_comment, add_label,
            remove_label) execute without requiring explicit
            confirmation from the caller.
        default_space: Optional Confluence space key (e.g. ``ENG``) used
            by tools that need a space scope (e.g. ``my_pages``,
            ``get_page_by_title``) when the caller doesn't pass one
            explicitly. If unset, callers must resolve/pass a space
            themselves -- never guessed in code.
    """

    base_url: str
    deployment_type: str
    timeout_seconds: float = 30.0
    max_retries: int = 3
    verify_ssl: bool = True
    auto_confirm_writes: bool = False
    default_space: Optional[str] = None


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
    """Load and validate Confluence auth credentials from environment variables.

    Two modes, checked in this order -- identical logic to `jira`'s:

    1. ``CONFLUENCE_PAT`` set -- a bearer token (a Confluence Data Center
       Personal Access Token, a Confluence Cloud API token used as a
       bearer token, or any other single-token credential the deployment
       hands this skill the same way). Takes precedence over Basic auth
       if both happen to be set, since a PAT is the more specific choice
       when someone has gone to the trouble of minting one.
    2. ``CONFLUENCE_USERNAME`` + ``CONFLUENCE_PASSWORD`` both set -- HTTP
       Basic auth.

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

    pat = _env(source, "CONFLUENCE_PAT")
    if pat:
        return BearerCredential(token=pat)

    username = _env(source, "CONFLUENCE_USERNAME")
    password = _env(source, "CONFLUENCE_PASSWORD")
    if username and password:
        return BasicCredential(username=username, password=password)

    missing = [name for name, value in (("CONFLUENCE_USERNAME", username), ("CONFLUENCE_PASSWORD", password)) if not value]
    raise ConfigurationError(
        "No Confluence credential configured. Set either CONFLUENCE_PAT (a "
        "Personal Access Token, a Cloud API token, or other bearer token), or "
        "both CONFLUENCE_USERNAME and CONFLUENCE_PASSWORD for Basic auth. "
        "Currently missing: "
        f"{', '.join(missing) if missing else 'CONFLUENCE_USERNAME, CONFLUENCE_PASSWORD'} "
        "(and CONFLUENCE_PAT is not set)."
    )


def load_config(env: Optional[Mapping[str, str]] = None) -> ConfluenceConfig:
    """Load and validate Confluence behavioral configuration from
    environment variables. Does not touch credential material -- see
    `load_credential()` for that.

    Args:
        env: Optional explicit mapping to read from instead of the
            process environment (primarily for testing).

    Raises:
        ConfigurationError: If required variables are missing or
            inconsistent. The message identifies exactly what is wrong so
            operators can fix configuration without reading source code.

    Environment variables:
        CONFLUENCE_BASE_URL (required): Root URL of the Confluence instance.
        CONFLUENCE_DEPLOYMENT_TYPE (required): "cloud" or "server" -- picks
            the REST path prefix every request uses. Unlike Jira's
            equivalent variable, this is not optional here.
        CONFLUENCE_TIMEOUT_SECONDS (optional, default 30).
        CONFLUENCE_MAX_RETRIES (optional, default 3).
        CONFLUENCE_VERIFY_SSL (optional, default true).
        CONFLUENCE_AUTO_CONFIRM_WRITES (optional, default false).
        CONFLUENCE_DEFAULT_SPACE (optional, default unset).
    """
    source: Mapping[str, str] = env if env is not None else os.environ

    base_url = _env(source, "CONFLUENCE_BASE_URL")
    if not base_url:
        raise ConfigurationError(
            "CONFLUENCE_BASE_URL is not set. Configure it to the root URL of your "
            "Confluence instance, e.g. https://mycompany.atlassian.net (Cloud) or "
            "https://confluence.mycompany.com (Server/Data Center)."
        )
    base_url = base_url.rstrip("/")
    if not (base_url.startswith("http://") or base_url.startswith("https://")):
        raise ConfigurationError(
            f"CONFLUENCE_BASE_URL={base_url!r} must start with http:// or https://"
        )

    deployment_type_raw = _env(source, "CONFLUENCE_DEPLOYMENT_TYPE")
    if not deployment_type_raw:
        raise ConfigurationError(
            "CONFLUENCE_DEPLOYMENT_TYPE is not set. Set it to 'cloud' or 'server' "
            "('server' also covers Data Center) -- unlike Jira, Confluence's REST "
            "API is mounted at a different path per deployment (Cloud: "
            "/wiki/rest/api, Server/Data Center: /rest/api), so every request "
            "needs to know which one to use."
        )
    deployment_type = deployment_type_raw.strip().lower()
    if deployment_type not in VALID_DEPLOYMENT_TYPES:
        raise ConfigurationError(
            f"CONFLUENCE_DEPLOYMENT_TYPE={deployment_type_raw!r} must be 'cloud' "
            "or 'server' ('server' also covers Data Center)."
        )

    config = ConfluenceConfig(
        base_url=base_url,
        deployment_type=deployment_type,
        timeout_seconds=_env_float(source, "CONFLUENCE_TIMEOUT_SECONDS", 30.0),
        max_retries=_env_int(source, "CONFLUENCE_MAX_RETRIES", 3),
        verify_ssl=_env_bool(source, "CONFLUENCE_VERIFY_SSL", True),
        auto_confirm_writes=_env_bool(source, "CONFLUENCE_AUTO_CONFIRM_WRITES", False),
        default_space=_env(source, "CONFLUENCE_DEFAULT_SPACE"),
    )
    logger.info(
        "Loaded Confluence configuration: base_url=%s deployment_type=%s auto_confirm_writes=%s",
        config.base_url,
        config.deployment_type,
        config.auto_confirm_writes,
    )
    return config
