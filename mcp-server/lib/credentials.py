"""Per-call environment resolution for a toolset's subprocess.

`execute.py` used to build every subprocess's environment as a flat
`os.environ.copy()` -- one process, one identity, and every toolset
inheriting every *other* toolset's credentials along the way. This
module replaces that with two things:

1. **Scoping.** A subprocess only ever sees the infra vars every
   subprocess needs to run at all (`_INFRA_ENV_VARS` below), plus the
   *one* toolset's own declared `required_environment_variables` --
   never another toolset's. `manifest.required_environment_variables`
   (already parsed from that toolset's own `SKILL.md` frontmatter) is
   the allowlist.
2. **Per-request override.** A caller-supplied HTTP header can override
   one of those declared vars for a single call -- e.g. so `mcp-server`
   can hand a Jira request Alice's credential and a different request
   Bob's, instead of both hitting Jira as whatever the server process's
   own environment says. This is honored only when `trusted=True` --
   self-asserted headers on an unauthenticated transport are trivially
   spoofable, so an unconfigured deployment must ignore them and fall
   back to the process env, not silently trust whoever can reach the
   port.

`get_http_headers()` (fastmcp) is documented to never raise and to
return `{}` when there's no active HTTP request -- so this resolves
identically under stdio (personal/direct use) and HTTP, with no
transport branching: under stdio there's simply never anything to
override.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .registry import SkillManifest

logger = logging.getLogger("mcp_server.credentials")

#: Env vars every subprocess needs regardless of which toolset it is --
#: none of these are ever toolset-specific credentials. PATH in
#: particular is load-bearing: `subprocess.run` given a bare command
#: name (e.g. "python3", not an absolute path) needs PATH *in the env
#: dict it's given* to resolve it on POSIX -- omitting it isn't merely
#: "less complete," it can leave the interpreter unable to spawn at all
#: depending on where python3 actually lives (e.g. /usr/local/bin/python3
#: in this repo's own Dockerfile's python:3.12-slim base, which isn't
#: guaranteed to be covered by any implicit fallback search path).
_INFRA_ENV_VARS = frozenset(
    {
        "PATH",
        "HOME",
        "LANG",
        "LANGUAGE",
        "LC_ALL",
        "LC_CTYPE",
        "TMPDIR",
        "TMP",
        "TEMP",
        "PYTHONPATH",
        "PYTHONIOENCODING",
        "PYTHONUTF8",
        # requests/urllib3 read these directly for proxying and custom CA
        # bundles -- relevant here specifically because this repo's own
        # Jira docs anticipate self-signed certs on internal instances.
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "NO_PROXY",
        "http_proxy",
        "https_proxy",
        "no_proxy",
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
        "REQUESTS_CA_BUNDLE",
        "CURL_CA_BUNDLE",
    }
)

#: Header name prefix for a per-request env var override, e.g.
#: `X-Agent-Skills-Env-JIRA_USERNAME`. Deliberately generic -- not tied
#: to LibreChat or any other specific client; any HTTP client that can
#: set a header can use this.
_HEADER_PREFIX = "x-agent-skills-env-"  # get_http_headers() lowercases names

_warned_untrusted_headers_seen = False


#: Whether this server instance trusts per-request credential headers,
#: set once at startup (see `configure()`) from server.py's own
#: --trust-request-credentials flag / MCP_TRUST_REQUEST_CREDENTIALS env
#: var. Mirrors how server.py already resolves --include-internal once
#: at startup and uses it throughout -- a single process, configured
#: once, not something threaded as an explicit parameter through every
#: layer between server.py and here. Defaults False: today's behavior
#: (headers ignored, process env used) unless a deployment opts in.
_trust_request_credentials = False


def configure(*, trust_request_credentials: bool) -> None:
    """Called once by server.py at startup. Not meant to be called
    per-request or mid-run -- this is process-lifetime configuration,
    the same as which transport or which toolsets are active.
    """
    global _trust_request_credentials
    _trust_request_credentials = trust_request_credentials


def is_trusted() -> bool:
    return _trust_request_credentials


def resolve_trust_request_credentials(cli_flag: bool) -> bool:
    """--trust-request-credentials (explicit at launch) wins; otherwise
    fall back to MCP_TRUST_REQUEST_CREDENTIALS=1 -- same
    flag-or-env-var-fallback shape as
    `lib.registry.resolve_include_internal`, so the two config
    mechanisms already in this server agree instead of diverging.
    """
    if cli_flag:
        return True
    return os.environ.get("MCP_TRUST_REQUEST_CREDENTIALS") == "1"


def _declared_var_names(manifest: "SkillManifest") -> set[str]:
    return {v["name"] for v in manifest.required_environment_variables}


def _get_http_headers() -> dict[str, str]:
    """Isolated so tests can monkeypatch this one call instead of the
    whole fastmcp import chain, and so a missing/incompatible fastmcp
    import can't take down every toolset call -- see the except below.
    """
    try:
        from fastmcp.server.dependencies import get_http_headers
    except ImportError:  # pragma: no cover -- fastmcp is a hard dependency in practice
        return {}
    return get_http_headers()


def _header_overrides(declared: set[str]) -> dict[str, str]:
    """Per-request header values, filtered to only vars this toolset
    actually declares -- a caller can never inject an arbitrary env var
    name into the subprocess by naming it in a header.
    """
    overrides: dict[str, str] = {}
    for header_name, value in _get_http_headers().items():
        if not header_name.startswith(_HEADER_PREFIX):
            continue
        var_name = header_name[len(_HEADER_PREFIX) :].upper().replace("-", "_")
        if var_name in declared:
            overrides[var_name] = value
    return overrides


def resolve_env(manifest: "SkillManifest", *, trust_request_credentials: bool) -> dict[str, str]:
    """Build the environment for one toolset subprocess call.

    Scoped to infra vars plus exactly this toolset's own declared vars
    -- never another toolset's. Declared vars are sourced from the
    server's own process environment by default; when
    `trust_request_credentials` is True, a matching per-request header
    overrides that for this one call only (nothing is persisted).
    """
    declared = _declared_var_names(manifest)

    env: dict[str, str] = {name: os.environ[name] for name in _INFRA_ENV_VARS if name in os.environ}
    env.update({name: os.environ[name] for name in declared if name in os.environ})

    overrides = _header_overrides(declared)
    if trust_request_credentials:
        env.update(overrides)
    elif overrides:
        global _warned_untrusted_headers_seen
        if not _warned_untrusted_headers_seen:
            logger.warning(
                "Received %d credential header(s) (%s) for toolset %r but "
                "trust_request_credentials is not enabled -- ignoring them "
                "and using this server's own environment instead. Pass "
                "--trust-request-credentials (only once an AuthProvider "
                "verifies callers) to honor per-request credentials.",
                len(overrides),
                ", ".join(sorted(overrides)),
                manifest.toolset,
            )
            _warned_untrusted_headers_seen = True

    return env
