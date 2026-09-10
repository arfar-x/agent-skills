"""Credentials for toolsets that authenticate an HTTP `requests.Session`.

A toolset never constructs one of these to match its own env vars' shape
-- it reads whichever env vars it declares (`JIRA_USERNAME`/`JIRA_PASSWORD`,
a future `JIRA_PAT`, `CONFLUENCE_TOKEN`, ...) and builds whichever
concrete `Credential` fits what was actually configured. The toolset's
own request code then only ever calls `credential.apply(session)` --
it doesn't know or care whether that credential came from this
process's own environment (personal/direct use) or was resolved
per-request by `mcp-server` on behalf of one specific caller behind a
multi-user chat client. That indifference is the entire point: the same
toolset code serves both.

This module is symlinked, not copied, into every toolset that needs it
-- see `../README.md`. Keep it dependency-light and toolset-agnostic;
anything specific to one toolset's own env var names belongs in that
toolset's own `lib/auth.py`, not here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    import requests


@runtime_checkable
class Credential(Protocol):
    """Something that knows how to authenticate an outgoing HTTP request.

    Concrete implementations below cover HTTP Basic auth and a single
    bearer token (which itself covers a Personal Access Token, a plain
    API key, and an OAuth access token -- identical wire format, so one
    type serves all three, see `BearerCredential`).
    """

    def apply(self, session: "requests.Session") -> None:
        """Configure `session` so subsequent requests are authenticated."""
        ...


class BasicCredential:
    """HTTP Basic auth -- a username/password pair."""

    __slots__ = ("username", "password")

    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password

    def apply(self, session: "requests.Session") -> None:
        session.auth = (self.username, self.password)

    def __repr__(self) -> str:  # never expose the password, even in logs
        return f"BasicCredential(username={self.username!r})"


class BearerCredential:
    """A single opaque token sent as `Authorization: Bearer <token>`.

    Covers a Jira Data Center Personal Access Token, a plain API key
    (e.g. a GitLab PAT -- GitLab's own docs confirm `Authorization:
    Bearer <token>` works for its REST API, not only its `PRIVATE-TOKEN`
    header), and an OAuth access token: the wire format is identical in
    all three cases.
    """

    __slots__ = ("token",)

    def __init__(self, token: str) -> None:
        self.token = token

    def apply(self, session: "requests.Session") -> None:
        session.headers["Authorization"] = f"Bearer {self.token}"

    def __repr__(self) -> str:  # never expose the token, even in logs
        return "BearerCredential(token=***)"


class NoCredential:
    """No authentication at all, for an endpoint that genuinely needs
    none. Applying it is a deliberate no-op, not something forgotten."""

    def apply(self, session: "requests.Session") -> None:
        return None

    def __repr__(self) -> str:
        return "NoCredential()"
