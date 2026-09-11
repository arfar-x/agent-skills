"""The single reusable Confluence REST client.

Every tool in this skill talks to Confluence exclusively through
:class:`ConfluenceClient`. No other module may issue HTTP requests to
Confluence. This centralizes authentication, retries, pagination,
rate-limit handling, error normalization, and (optional) response
caching, so that behavior is consistent everywhere and never duplicated.

Supports both Confluence Cloud and self-hosted Confluence Server / Data
Center via an explicit ``base_url``, using either HTTP Basic auth
(username + password) or a single bearer token (a Personal Access
Token, a Cloud API token, or any other single-token credential) -- see
``lib.auth.load_credential``. Uses the REST API v1 ``/content`` family
of endpoints throughout (not the newer Cloud-only v2 API), the same
"one API generation, works everywhere" choice ``jira_client.py`` makes
by sticking to ``/rest/api/2`` instead of Cloud's ``/rest/api/3``.

Unlike Jira (which uses the same REST path for both deployments),
Confluence mounts its REST API at a different path per deployment --
Cloud under ``/wiki/rest/api``, Server/Data Center directly under
``/rest/api`` on the base URL. ``_API_PATH``/``_WEB_PREFIX`` below are
resolved once from ``config.deployment_type`` at construction time and
used for every request; see ``lib.auth.ConfluenceConfig`` for why this
is a required setting here where Jira's equivalent is optional.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .auth import ConfluenceConfig, load_config, load_credential
from .credentials import Credential
from .models import Ancestor, Attachment, Comment, Page, Space
from .utils import safe_get, storage_to_plain_text

logger = logging.getLogger("confluence_skill.client")


class ConfluenceApiError(RuntimeError):
    """Base class for all Confluence client errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class ConfluenceAuthError(ConfluenceApiError):
    """Raised on 401/403 responses -- invalid or insufficient credentials."""


class ConfluenceNotFoundError(ConfluenceApiError):
    """Raised on 404 responses -- page, space, or resource does not exist."""


class ConfluenceRateLimitError(ConfluenceApiError):
    """Raised when Confluence rate limiting could not be resolved via retries."""


class ConfluenceValidationError(ConfluenceApiError):
    """Raised on 400 responses -- typically invalid CQL or field values."""


class _TTLCache:
    """A minimal thread-safe in-memory TTL cache for idempotent GET requests."""

    def __init__(self, ttl_seconds: float):
        self._ttl = ttl_seconds
        self._store: Dict[str, Any] = {}
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self._ttl > 0

    def get(self, key: str) -> Optional[Any]:
        if not self.enabled:
            return None
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if time.monotonic() >= expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._store[key] = (time.monotonic() + self._ttl, value)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


class ConfluenceClient:
    """High-level, typed client wrapping the Confluence REST API.

    All public methods return the typed models defined in
    :mod:`lib.models` (or primitive JSON-safe structures) -- never raw
    Confluence REST payloads. This is what lets every tool stay "thin":
    tools only validate input, call this client, and hand back the result.
    """

    _API_PATH = {"cloud": "/wiki/rest/api", "server": "/rest/api"}
    #: Prefix in front of a content item's ``_links.webui`` relative link
    #: to build a real browsable URL -- Cloud mounts the whole wiki under
    #: ``/wiki``, Server/Data Center's web UI is at the base URL directly.
    _WEB_PREFIX = {"cloud": "/wiki", "server": ""}

    def __init__(
        self,
        config: Optional[ConfluenceConfig] = None,
        credential: Optional[Credential] = None,
        session: Optional[requests.Session] = None,
        cache_ttl_seconds: Optional[float] = None,
    ):
        import os

        self.config = config or load_config()
        self.credential = credential or load_credential()
        self._api_path = self._API_PATH[self.config.deployment_type]
        self._web_prefix = self._WEB_PREFIX[self.config.deployment_type]
        self.session = session or self._build_session()
        if cache_ttl_seconds is None:
            cache_ttl_seconds = float(os.environ.get("CONFLUENCE_CACHE_TTL_SECONDS", "0") or 0)
        self._cache = _TTLCache(cache_ttl_seconds)
        logger.debug(
            "ConfluenceClient initialized against %s (%s) using %r",
            self.config.base_url,
            self.config.deployment_type,
            self.credential,
        )

    # ------------------------------------------------------------------
    # Session / transport setup
    # ------------------------------------------------------------------

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=self.config.max_retries,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET", "POST", "PUT", "DELETE"}),
            respect_retry_after_header=True,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update({"Accept": "application/json", "Content-Type": "application/json"})

        self.credential.apply(session)
        session.verify = self.config.verify_ssl
        return session

    # ------------------------------------------------------------------
    # Low-level request plumbing
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Any] = None,
        cache: bool = False,
    ) -> Any:
        url = f"{self.config.base_url}{path}"
        cache_key = f"{method}:{url}:{sorted((params or {}).items())}"

        if cache and method == "GET":
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug("Cache hit for %s", url)
                return cached

        logger.info("Confluence request: %s %s", method, path)
        try:
            response = self.session.request(
                method,
                url,
                params=params,
                json=json_body,
                timeout=self.config.timeout_seconds,
            )
        except requests.exceptions.Timeout as exc:
            raise ConfluenceApiError(
                f"Timed out contacting Confluence at {url} after {self.config.timeout_seconds}s"
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            raise ConfluenceApiError(f"Could not connect to Confluence at {self.config.base_url}: {exc}") from exc

        self._raise_for_status(response)

        if response.status_code == 204 or not response.content:
            result: Any = {}
        else:
            try:
                result = response.json()
            except ValueError as exc:
                raise ConfluenceApiError(
                    f"Confluence returned a non-JSON response ({response.status_code}) for {url}"
                ) from exc

        if cache and method == "GET":
            self._cache.set(cache_key, result)

        return result

    def _raise_for_status(self, response: requests.Response) -> None:
        if response.ok:
            return

        status = response.status_code
        message = self._extract_error_message(response)

        if status == 401:
            raise ConfluenceAuthError(
                f"Confluence authentication failed (401). Check CONFLUENCE_USERNAME/"
                f"CONFLUENCE_PASSWORD or CONFLUENCE_PAT. Details: {message}",
                status_code=status,
            )
        if status == 403:
            raise ConfluenceAuthError(
                f"Confluence denied access (403) -- the configured account lacks permission. "
                f"Details: {message}",
                status_code=status,
            )
        if status == 404:
            raise ConfluenceNotFoundError(f"Confluence resource not found (404): {message}", status_code=status)
        if status == 400:
            raise ConfluenceValidationError(f"Confluence rejected the request (400): {message}", status_code=status)
        if status == 409:
            raise ConfluenceValidationError(
                f"Confluence rejected the request (409, usually a stale page version): {message}",
                status_code=status,
            )
        if status == 429:
            retry_after = response.headers.get("Retry-After", "unknown")
            raise ConfluenceRateLimitError(
                f"Confluence rate limit exceeded (429) even after retries. "
                f"Retry-After={retry_after}. Details: {message}",
                status_code=status,
            )
        if status >= 500:
            raise ConfluenceApiError(
                f"Confluence server error ({status}) after exhausting retries: {message}",
                status_code=status,
            )
        raise ConfluenceApiError(f"Unexpected Confluence response ({status}): {message}", status_code=status)

    @staticmethod
    def _extract_error_message(response: requests.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return response.text[:500] if response.text else response.reason

        if isinstance(payload, dict):
            message = payload.get("message")
            data_message = safe_get(payload, "data", "message")
            parts = [p for p in (message, data_message) if p]
            if parts:
                return "; ".join(parts)
        return str(payload)[:500]

    def _paginate(
        self,
        path: str,
        *,
        params: Dict[str, Any],
        items_key: str = "results",
        max_results_total: Optional[int] = None,
        page_size: int = 25,
    ) -> List[Dict[str, Any]]:
        """Transparently walk Confluence's ``start``/``limit``/``size`` +
        ``_links.next`` pagination and return all items.

        Unlike Jira's ``startAt/maxResults/total`` envelope (which reports
        a grand ``total`` up front), Confluence's ``/content*``/``/space``
        endpoints only ever tell you whether *another* page exists, via
        ``_links.next`` -- there is no total to check against. Every
        endpoint this client paginates always returns the
        ``results``/``size``/``_links`` envelope (never a bare array with
        no pagination signal at all, unlike a couple of Jira endpoints),
        so ``_links.next`` alone is trusted as the stop signal rather than
        also guessing from a short page -- a page can legitimately come
        back shorter than the requested ``limit`` while ``_links.next``
        still points at more data. Always requests one bounded page at a
        time (``page_size``, default 25) and walks forward via ``start``
        rather than asking Confluence for every result in a single large
        page -- keeps each request small and lets ``max_results_total``
        cut the walk short cheaply.
        """
        collected: List[Dict[str, Any]] = []
        start = int(params.get("start", 0))
        params = dict(params)

        while True:
            remaining = None
            if max_results_total is not None:
                remaining = max_results_total - len(collected)
                if remaining <= 0:
                    break
            batch_size = page_size if remaining is None else min(page_size, remaining)
            params["start"] = start
            params["limit"] = batch_size

            payload = self._request("GET", path, params=params)
            items = payload.get(items_key, []) if isinstance(payload, dict) else (payload or [])
            collected.extend(items)

            fetched_count = len(items)
            start += fetched_count
            has_next = bool(safe_get(payload, "_links", "next")) if isinstance(payload, dict) else False

            if fetched_count == 0:
                break
            if not has_next:
                break

        if max_results_total is not None:
            collected = collected[:max_results_total]
        return collected

    # ------------------------------------------------------------------
    # Model builders (translate raw Confluence JSON -> typed models)
    # ------------------------------------------------------------------

    def _web_url(self, raw: Dict[str, Any]) -> Optional[str]:
        webui = safe_get(raw, "_links", "webui")
        if not webui:
            return None
        return f"{self.config.base_url}{self._web_prefix}{webui}"

    def resolve_space(self, space_key: Optional[str] = None) -> Optional[str]:
        """Resolve an explicit ``space_key`` against ``CONFLUENCE_DEFAULT_SPACE``.

        Returns ``None`` (not a guess) if neither is available -- callers
        that require a space should raise on ``None`` themselves; callers
        where a space is only an optional narrowing can fall back to an
        unscoped call.
        """
        resolved = (space_key or self.config.default_space or "").strip()
        return resolved or None

    def _build_page(self, raw: Dict[str, Any]) -> Page:
        version = safe_get(raw, "version", "number", default=1)
        space_key = safe_get(raw, "space", "key", default="") or ""
        body_storage = safe_get(raw, "body", "storage", "value")
        ancestors_raw = raw.get("ancestors") or []
        ancestors = [Ancestor(id=a.get("id", ""), title=a.get("title", "") or "") for a in ancestors_raw]
        parent_id = ancestors[-1].id if ancestors else None
        return Page(
            id=raw.get("id", "") or "",
            title=raw.get("title", "") or "",
            space_key=space_key,
            version=int(version or 1),
            url=self._web_url(raw),
            body_plain_text=storage_to_plain_text(body_storage) if body_storage else None,
            parent_id=parent_id,
            ancestors=ancestors,
            created=safe_get(raw, "history", "createdDate"),
            updated=safe_get(raw, "version", "when"),
        )

    def _build_space(self, raw: Dict[str, Any]) -> Space:
        return Space(
            key=raw.get("key", "") or "",
            name=raw.get("name", "") or "",
            url=self._web_url(raw),
            description=safe_get(raw, "description", "plain", "value"),
        )

    @staticmethod
    def _build_comment(raw: Dict[str, Any], *, body_storage_override: Optional[str] = None) -> Comment:
        body_storage = body_storage_override if body_storage_override is not None else safe_get(raw, "body", "storage", "value")
        return Comment(
            id=raw.get("id", "") or "",
            author=safe_get(raw, "history", "createdBy", "displayName"),
            body_plain_text=storage_to_plain_text(body_storage),
            created=safe_get(raw, "history", "createdDate"),
        )

    def _build_attachment(self, raw: Dict[str, Any]) -> Attachment:
        download = safe_get(raw, "_links", "download")
        url = f"{self.config.base_url}{self._web_prefix}{download}" if download else self._web_url(raw)
        return Attachment(
            id=raw.get("id", "") or "",
            title=raw.get("title", "") or "",
            media_type=safe_get(raw, "metadata", "mediaType"),
            file_size=safe_get(raw, "extensions", "fileSize"),
            url=url,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    _DEFAULT_PAGE_EXPAND = "body.storage,version,space,ancestors,history"

    def get_page(self, page_id: str, *, expand: Optional[List[str]] = None) -> Page:
        """Fetch a single page by its content id."""
        self._require_page_id(page_id)
        params = {"expand": ",".join(expand) if expand else self._DEFAULT_PAGE_EXPAND}
        raw = self._request("GET", f"{self._api_path}/content/{page_id}", params=params, cache=True)
        return self._build_page(raw)

    def get_page_by_title(self, space_key: str, title: str) -> Optional[Page]:
        """Resolve a page by its space + exact title (Confluence pages are
        addressed by title within a space at least as often as by id)."""
        key = (space_key or "").strip()
        if not key:
            raise ConfluenceValidationError("space_key is required.")
        title = (title or "").strip()
        if not title:
            raise ConfluenceValidationError("title is required.")
        params = {
            "spaceKey": key,
            "title": title,
            "type": "page",
            "expand": self._DEFAULT_PAGE_EXPAND,
        }
        payload = self._request("GET", f"{self._api_path}/content", params=params)
        results = payload.get("results", [])
        if not results:
            return None
        return self._build_page(results[0])

    def search(
        self,
        cql: str,
        *,
        max_results: Optional[int] = 50,
        expand: Optional[List[str]] = None,
    ) -> List[Page]:
        """Run a CQL query and return matching content (auto-paginated).

        Args:
            cql: A valid CQL query string, e.g.
                ``"space = ENG AND type = page AND text ~ 'onboarding'"``.
            max_results: Safety cap on total items fetched (``None`` for
                unlimited, subject to Confluence's own hard limits).
            expand: Optional expand parameters. Defaults to
                ``["space", "version"]`` -- pass
                ``["body.storage", "space", "version"]`` explicitly to get
                each result's ``body_plain_text`` too, the token-cost
                tradeoff a bulk search should make deliberately.
        """
        if not cql or not cql.strip():
            raise ConfluenceValidationError("CQL query must not be empty.")

        params: Dict[str, Any] = {"cql": cql, "expand": ",".join(expand or ["space", "version"])}
        raw_pages = self._paginate(
            f"{self._api_path}/content/search",
            params=params,
            max_results_total=max_results,
            page_size=25,
        )
        return [self._build_page(raw) for raw in raw_pages]

    def list_spaces(self, *, max_results: Optional[int] = 100) -> List[Space]:
        """List every space visible to the authenticated user."""
        raw_spaces = self._paginate(
            f"{self._api_path}/space",
            params={"expand": "description.plain"},
            max_results_total=max_results,
            page_size=50,
        )
        return [self._build_space(raw) for raw in raw_spaces]

    def get_space(self, space_key: str) -> Space:
        """Fetch one space by its key."""
        key = (space_key or "").strip()
        if not key:
            raise ConfluenceValidationError("space_key is required.")
        raw = self._request(
            "GET", f"{self._api_path}/space/{key}", params={"expand": "description.plain"}, cache=True
        )
        return self._build_space(raw)

    def get_comments(self, page_id: str, *, max_results: Optional[int] = None) -> List[Comment]:
        """Fetch all comments on a page."""
        self._require_page_id(page_id)
        raw_comments = self._paginate(
            f"{self._api_path}/content/{page_id}/child/comment",
            params={"expand": "body.storage,history"},
            max_results_total=max_results,
            page_size=25,
        )
        return [self._build_comment(raw) for raw in raw_comments]

    def get_attachments(self, page_id: str, *, max_results: Optional[int] = None) -> List[Attachment]:
        """List a page's attachments (metadata only -- no upload/download support)."""
        self._require_page_id(page_id)
        raw_attachments = self._paginate(
            f"{self._api_path}/content/{page_id}/child/attachment",
            params={"expand": "metadata,extensions"},
            max_results_total=max_results,
            page_size=25,
        )
        return [self._build_attachment(raw) for raw in raw_attachments]

    def get_children(self, page_id: str, *, max_results: Optional[int] = None) -> List[Page]:
        """List a page's direct child pages."""
        self._require_page_id(page_id)
        raw_children = self._paginate(
            f"{self._api_path}/content/{page_id}/child/page",
            params={"expand": "space,version,ancestors"},
            max_results_total=max_results,
            page_size=25,
        )
        return [self._build_page(raw) for raw in raw_children]

    def get_labels(self, page_id: str) -> List[str]:
        """Return the label names currently on a page."""
        self._require_page_id(page_id)
        payload = self._request("GET", f"{self._api_path}/content/{page_id}/label", params={})
        return [label.get("name") for label in payload.get("results", []) if label.get("name")]

    def my_pages(self, *, max_results: Optional[int] = 50) -> List[Page]:
        """Pages authored by the current user, most recently modified first.

        The direct analog of ``jira_client.py``'s ``my_work`` for
        Confluence -- unlike Jira's ``currentUser()`` (which needed no
        special handling in JQL either), CQL's own ``currentUser()``
        already resolves against whichever credential this client is
        using, so no separate "who am I" lookup is needed first.
        """
        return self.search("creator = currentUser() order by lastmodified desc", max_results=max_results)

    def create_page(
        self,
        space_key: str,
        title: str,
        body_storage: str,
        *,
        parent_id: Optional[str] = None,
    ) -> Page:
        """Create a new page.

        Args:
            space_key: Destination space key, e.g. ``ENG``.
            title: Page title. Must be unique within the space.
            body_storage: Page content as Confluence storage-format XHTML
                (e.g. ``"<p>Hello</p>"``) -- not Markdown, not plain text.
                Sent to the API verbatim.
            parent_id: Optional parent page id, to create this as a child
                page instead of a space-root page.

        Raises:
            ConfluenceValidationError: If a required field is missing.
        """
        key = (space_key or "").strip()
        if not key:
            raise ConfluenceValidationError("space_key is required.")
        title = (title or "").strip()
        if not title:
            raise ConfluenceValidationError("title is required.")
        if not body_storage or not body_storage.strip():
            raise ConfluenceValidationError(
                "body_storage is required -- Confluence storage-format XHTML, e.g. '<p>...</p>'."
            )

        payload: Dict[str, Any] = {
            "type": "page",
            "title": title,
            "space": {"key": key},
            "body": {"storage": {"value": body_storage, "representation": "storage"}},
        }
        if parent_id:
            payload["ancestors"] = [{"id": str(parent_id)}]

        raw = self._request("POST", f"{self._api_path}/content", json_body=payload)
        return self.get_page(raw.get("id", ""))

    def update_page(
        self,
        page_id: str,
        *,
        title: Optional[str] = None,
        body_storage: Optional[str] = None,
        version: Optional[int] = None,
    ) -> Page:
        """Update an existing page's title and/or content.

        Confluence requires every update to state the *next* version
        number explicitly and rejects the request (409) if it doesn't
        match the page's real current version -- unlike Jira, which has
        no such concept for a plain field edit. This method fetches the
        page's current version and sends ``current + 1`` automatically
        unless ``version`` is passed explicitly (e.g. to intentionally
        retry against a version learned from a prior conflict error).

        Args:
            page_id: Target page id.
            title: New title (omit to leave unchanged).
            body_storage: New content, Confluence storage-format XHTML
                (omit to leave unchanged).
            version: Explicit version number to send instead of
                auto-incrementing. Only pass this when you have a
                specific reason to -- normally leave it unset.

        Raises:
            ConfluenceValidationError: If neither ``title`` nor
                ``body_storage`` is given.
        """
        self._require_page_id(page_id)
        if title is None and body_storage is None:
            raise ConfluenceValidationError("At least one of title/body_storage must be provided.")

        current = self._request(
            "GET", f"{self._api_path}/content/{page_id}", params={"expand": "version"}
        )
        current_version = int(safe_get(current, "version", "number", default=1) or 1)
        next_version = version if version is not None else current_version + 1

        payload: Dict[str, Any] = {
            "id": str(page_id),
            "type": "page",
            "title": title if title is not None else current.get("title", ""),
            "version": {"number": next_version},
        }
        if body_storage is not None:
            payload["body"] = {"storage": {"value": body_storage, "representation": "storage"}}

        raw = self._request("PUT", f"{self._api_path}/content/{page_id}", json_body=payload)
        return self._build_page(raw)

    def delete_page(self, page_id: str) -> None:
        """Permanently delete a page. Cannot be undone."""
        self._require_page_id(page_id)
        self._request("DELETE", f"{self._api_path}/content/{page_id}")

    def add_comment(self, page_id: str, body_storage: str) -> Comment:
        """Add a comment to a page.

        Args:
            page_id: Page to comment on.
            body_storage: Comment content, Confluence storage-format XHTML
                (e.g. ``"<p>...</p>"``).
        """
        self._require_page_id(page_id)
        if not body_storage or not body_storage.strip():
            raise ConfluenceValidationError(
                "body_storage is required -- Confluence storage-format XHTML, e.g. '<p>...</p>'."
            )
        payload = {
            "type": "comment",
            "container": {"id": str(page_id), "type": "page"},
            "body": {"storage": {"value": body_storage, "representation": "storage"}},
        }
        raw = self._request("POST", f"{self._api_path}/content", json_body=payload)
        # Built from the response's id/author/created plus the body we sent,
        # rather than re-fetching -- a fresh POST response doesn't reliably
        # echo back an expanded body.storage without a follow-up GET.
        return self._build_comment(raw, body_storage_override=body_storage)

    def add_label(self, page_id: str, label: str) -> List[str]:
        """Add a label to a page. Returns the page's full label list after adding."""
        self._require_page_id(page_id)
        label = (label or "").strip()
        if not label:
            raise ConfluenceValidationError("label is required.")
        payload = [{"prefix": "global", "name": label}]
        result = self._request("POST", f"{self._api_path}/content/{page_id}/label", json_body=payload)
        return [entry.get("name") for entry in result.get("results", []) if entry.get("name")]

    def remove_label(self, page_id: str, label: str) -> None:
        """Remove a label from a page."""
        self._require_page_id(page_id)
        label = (label or "").strip()
        if not label:
            raise ConfluenceValidationError("label is required.")
        self._request("DELETE", f"{self._api_path}/content/{page_id}/label/{label}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _require_page_id(page_id: str) -> None:
        if not page_id or not str(page_id).strip():
            raise ConfluenceValidationError("page_id must not be empty.")


_client_lock = threading.Lock()
_client_singleton: Optional[ConfluenceClient] = None


def get_client() -> ConfluenceClient:
    """Return a process-wide singleton :class:`ConfluenceClient`.

    Tools should use this instead of constructing their own client, so
    that configuration is validated once and the underlying HTTP session
    (with its connection pool and retry policy) is reused across calls.
    """
    global _client_singleton
    with _client_lock:
        if _client_singleton is None:
            _client_singleton = ConfluenceClient()
        return _client_singleton


def reset_client() -> None:
    """Drop the cached singleton client (primarily for tests)."""
    global _client_singleton
    with _client_lock:
        _client_singleton = None
