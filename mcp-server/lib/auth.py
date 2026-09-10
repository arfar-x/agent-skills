"""Builds this server's inbound `AuthProvider`, if one is configured.

Verifying *who* is calling is what lets `lib/credentials.py` decide
whether to trust a per-request credential header instead of always
falling back to this server's own process environment -- see that
module's own docstring for the full picture. This module only builds
the provider fastmcp's `FastMCP(auth=...)` consumes; it doesn't touch
credential resolution itself.

Deliberately narrow: every provider here validates a bearer token that
some other already-established flow produced (e.g. a chat client's own
Keycloak login, forwarded as a header) -- none of them make this server
into an OAuth authorization server itself. fastmcp's own
`KeycloakAuthProvider` assumes the opposite shape (Dynamic Client
Registration -- an MCP client doing an interactive browser OAuth flow
against Keycloak *through* this server, which needs this server's own
public `base_url` for OAuth metadata). That's the wrong tool here: this
server sits on an internal network, reached by one client that already
holds its own token, not by arbitrary MCP clients registering
themselves. `JWTVerifier` configured directly against Keycloak's JWKS
endpoint covers the actual need with less machinery.

Every provider is opt-in, gated purely on its own env vars being
present -- there is no separate `--auth-provider=keycloak` flag to also
set. Absent those vars, `build_auth_provider()` returns None and
`FastMCP(auth=None)` is exactly today's behavior.
"""

from __future__ import annotations

import os

from fastmcp.server.auth import AuthProvider


def _keycloak_provider() -> AuthProvider | None:
    """Built only when MCP_AUTH_KEYCLOAK_REALM_URL is set -- providing
    that var is the entire opt-in.

    MCP_AUTH_KEYCLOAK_REALM_URL: the realm's own URL, e.g.
        https://keycloak.example.com/realms/myrealm
    MCP_AUTH_KEYCLOAK_AUDIENCE: optional -- expected `aud` claim.
        Recommended once this is used for anything beyond local testing,
        same as fastmcp's own JWTVerifier docs recommend.
    """
    realm_url = os.environ.get("MCP_AUTH_KEYCLOAK_REALM_URL")
    if not realm_url:
        return None

    from fastmcp.server.auth.providers.jwt import JWTVerifier

    realm_url = realm_url.rstrip("/")
    return JWTVerifier(
        jwks_uri=f"{realm_url}/protocol/openid-connect/certs",
        issuer=realm_url,
        algorithm="RS256",
        audience=os.environ.get("MCP_AUTH_KEYCLOAK_AUDIENCE") or None,
    )


#: Checked in order; the first provider whose own env vars are present
#: wins. Add a new provider function above and list it here -- nothing
#: else in this repo needs to change to support it.
_PROVIDER_FACTORIES = (_keycloak_provider,)


def build_auth_provider() -> AuthProvider | None:
    for factory in _PROVIDER_FACTORIES:
        provider = factory()
        if provider is not None:
            return provider
    return None
