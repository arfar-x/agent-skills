from __future__ import annotations

import lib.auth as auth


def test_no_provider_configured_by_default(monkeypatch):
    monkeypatch.delenv("MCP_AUTH_KEYCLOAK_REALM_URL", raising=False)
    assert auth.build_auth_provider() is None


def test_keycloak_provider_built_when_realm_url_set(monkeypatch):
    monkeypatch.setenv("MCP_AUTH_KEYCLOAK_REALM_URL", "https://keycloak.example.com/realms/myrealm")
    provider = auth.build_auth_provider()
    assert provider is not None
    assert provider.issuer == "https://keycloak.example.com/realms/myrealm"
    assert provider.jwks_uri == "https://keycloak.example.com/realms/myrealm/protocol/openid-connect/certs"


def test_keycloak_realm_url_trailing_slash_is_stripped(monkeypatch):
    monkeypatch.setenv("MCP_AUTH_KEYCLOAK_REALM_URL", "https://keycloak.example.com/realms/myrealm/")
    provider = auth.build_auth_provider()
    assert provider.issuer == "https://keycloak.example.com/realms/myrealm"
    assert "//protocol" not in provider.jwks_uri


def test_keycloak_audience_is_optional(monkeypatch):
    monkeypatch.setenv("MCP_AUTH_KEYCLOAK_REALM_URL", "https://keycloak.example.com/realms/myrealm")
    monkeypatch.delenv("MCP_AUTH_KEYCLOAK_AUDIENCE", raising=False)
    provider = auth.build_auth_provider()
    assert provider.audience is None


def test_keycloak_audience_is_passed_through_when_set(monkeypatch):
    monkeypatch.setenv("MCP_AUTH_KEYCLOAK_REALM_URL", "https://keycloak.example.com/realms/myrealm")
    monkeypatch.setenv("MCP_AUTH_KEYCLOAK_AUDIENCE", "my-mcp-server")
    provider = auth.build_auth_provider()
    assert provider.audience == "my-mcp-server"
