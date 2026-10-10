"""The single reusable GitLab REST client.

Every tool in this skill talks to GitLab exclusively through
:class:`GitLabClient`. No other module may issue HTTP requests to GitLab.
This centralizes authentication, retries, pagination, rate-limit
handling and error normalization -- the same role
``confluence_client.py`` plays for the Confluence toolset.

Targets a self-hosted (or gitlab.com) instance's REST API v4 at
``{base_url}/api/v4``, authenticated by a single bearer token.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from . import models
from .auth import GitLabConfig, load_config, load_credential
from .credentials import Credential
from .diff_position import resolve_position
from .utils import safe_get

logger = logging.getLogger("glab_skill.client")

_API = "/api/v4"


class GitLabApiError(RuntimeError):
    """Base class for all GitLab client errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class GitLabAuthError(GitLabApiError):
    """Raised on 401/403 responses -- invalid or insufficient credentials."""


class GitLabNotFoundError(GitLabApiError):
    """Raised on 404 responses -- project, MR, file, or ref does not exist."""


class GitLabRateLimitError(GitLabApiError):
    """Raised when rate limiting could not be resolved via retries."""


class GitLabValidationError(GitLabApiError):
    """Raised on 400/409/422 responses -- invalid parameters or position."""


def encode_project(project: str) -> str:
    """URL-encode a numeric id or ``group/sub/project`` path for use in a URL path."""
    return quote(str(project).strip(), safe="")


class GitLabClient:
    """High-level client wrapping the GitLab REST API.

    Public methods return normalized dicts (see :mod:`lib.models`), never
    raw GitLab payloads.
    """

    def __init__(
        self,
        config: Optional[GitLabConfig] = None,
        credential: Optional[Credential] = None,
        session: Optional[requests.Session] = None,
    ):
        self.config = config or load_config()
        self.credential = credential or load_credential()
        self.session = session or self._build_session()
        logger.debug("GitLabClient initialized against %s using %r", self.config.base_url, self.credential)

    # ------------------------------------------------------------------
    # Transport
    # ------------------------------------------------------------------

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=self.config.max_retries,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET", "PUT", "DELETE"}),  # never auto-retry a POST: it could double-post a comment
            respect_retry_after_header=True,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update({"Accept": "application/json"})
        self.credential.apply(session)
        session.verify = self.config.verify_ssl
        return session

    def _send(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Any] = None,
    ) -> requests.Response:
        url = f"{self.config.base_url}{_API}{path}"
        logger.info("GitLab request: %s %s", method, path)
        try:
            response = self.session.request(
                method, url, params=params, json=json_body, timeout=self.config.timeout_seconds
            )
        except requests.exceptions.Timeout as exc:
            raise GitLabApiError(f"Timed out contacting GitLab at {url} after {self.config.timeout_seconds}s") from exc
        except requests.exceptions.ConnectionError as exc:
            raise GitLabApiError(f"Could not connect to GitLab at {self.config.base_url}: {exc}") from exc
        self._raise_for_status(response)
        return response

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self._send(method, path, **kwargs)
        if response.status_code == 204 or not response.content:
            return {}
        try:
            return response.json()
        except ValueError as exc:
            raise GitLabApiError(f"GitLab returned a non-JSON response ({response.status_code}) for {path}") from exc

    def _raise_for_status(self, response: requests.Response) -> None:
        if response.ok:
            return
        status = response.status_code
        message = self._extract_error_message(response)
        if status == 401:
            raise GitLabAuthError(f"GitLab authentication failed (401). Check GITLAB_TOKEN. Details: {message}", status)
        if status == 403:
            raise GitLabAuthError(
                f"GitLab denied access (403) -- the token lacks permission or scope (posting needs `api`). "
                f"Details: {message}",
                status,
            )
        if status == 404:
            raise GitLabNotFoundError(f"GitLab resource not found (404): {message}", status)
        if status in (400, 409, 422):
            raise GitLabValidationError(f"GitLab rejected the request ({status}): {message}", status)
        if status == 429:
            retry_after = response.headers.get("Retry-After", "unknown")
            raise GitLabRateLimitError(
                f"GitLab rate limit exceeded (429) even after retries. Retry-After={retry_after}. Details: {message}",
                status,
            )
        if status >= 500:
            raise GitLabApiError(f"GitLab server error ({status}): {message}", status)
        raise GitLabApiError(f"Unexpected GitLab response ({status}): {message}", status)

    @staticmethod
    def _extract_error_message(response: requests.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return response.text[:500] if response.text else str(response.reason)
        if isinstance(payload, dict):
            for key in ("message", "error", "error_description"):
                if payload.get(key):
                    return str(payload[key])[:500]
        return str(payload)[:500]

    def _paginate(self, path: str, *, params: Optional[Dict[str, Any]] = None, max_results: int = 100) -> List[Any]:
        """Walk GitLab's ``page``/``per_page`` pagination (``X-Next-Page`` header)."""
        collected: List[Any] = []
        page = 1
        params = dict(params or {})
        while len(collected) < max_results:
            params["page"] = page
            params["per_page"] = min(100, max_results - len(collected))
            response = self._send("GET", path, params=params)
            items = response.json() if response.content else []
            if not isinstance(items, list):
                break
            collected.extend(items)
            next_page = response.headers.get("X-Next-Page")
            if not items or not next_page:
                break
            page = int(next_page)
        return collected[:max_results]

    def _project_path(self, project: str) -> str:
        return f"/projects/{encode_project(project)}"

    # ------------------------------------------------------------------
    # Identity / projects / repository
    # ------------------------------------------------------------------

    def current_user(self) -> Dict[str, Any]:
        return models.user(self._request("GET", "/user"))

    def get_project(self, project: str) -> Dict[str, Any]:
        return models.project(self._request("GET", self._project_path(project)))

    def search_projects(self, search: str, membership: bool = False, max_results: int = 20) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"search": search, "order_by": "last_activity_at"}
        if membership:
            params["membership"] = "true"
        return [models.project(p) for p in self._paginate("/projects", params=params, max_results=max_results)]

    def list_branches(self, project: str, search: Optional[str] = None, max_results: int = 50) -> List[Dict[str, Any]]:
        params = {"search": search} if search else {}
        items = self._paginate(f"{self._project_path(project)}/repository/branches", params=params, max_results=max_results)
        return [models.branch(b) for b in items]

    def get_tree(
        self,
        project: str,
        path: Optional[str] = None,
        ref: Optional[str] = None,
        recursive: bool = False,
        max_results: int = 200,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {}
        if path:
            params["path"] = path
        if ref:
            params["ref"] = ref
        if recursive:
            params["recursive"] = "true"
        items = self._paginate(f"{self._project_path(project)}/repository/tree", params=params, max_results=max_results)
        return [models.tree_entry(e) for e in items]

    def get_file(self, project: str, file_path: str, ref: str, max_bytes: int = 200_000) -> Dict[str, Any]:
        """Fetch one file's raw content at ``ref``, truncated at ``max_bytes``."""
        path = f"{self._project_path(project)}/repository/files/{quote(file_path.lstrip('/'), safe='')}/raw"
        response = self._send("GET", path, params={"ref": ref})
        data = response.content
        if b"\x00" in data[:8000]:
            return {"file_path": file_path, "ref": ref, "binary": True, "size_bytes": len(data), "content": None}
        truncated = len(data) > max_bytes
        return {
            "file_path": file_path,
            "ref": ref,
            "binary": False,
            "size_bytes": len(data),
            "truncated": truncated,
            "content": data[:max_bytes].decode("utf-8", errors="replace"),
        }

    # ------------------------------------------------------------------
    # Merge requests (read)
    # ------------------------------------------------------------------

    def list_mrs(
        self,
        project: Optional[str] = None,
        state: str = "opened",
        scope: str = "all",
        reviewer_me: bool = False,
        search: Optional[str] = None,
        max_results: int = 20,
    ) -> List[Dict[str, Any]]:
        path = f"{self._project_path(project)}/merge_requests" if project else "/merge_requests"
        params: Dict[str, Any] = {"state": state, "scope": scope, "order_by": "updated_at"}
        if reviewer_me:
            params["reviewer_username"] = self.current_user()["username"]
        if search:
            params["search"] = search
        return [models.mr_summary(m) for m in self._paginate(path, params=params, max_results=max_results)]

    def _mr_path(self, project: str, mr_iid: int) -> str:
        return f"{self._project_path(project)}/merge_requests/{int(mr_iid)}"

    def get_mr(self, project: str, mr_iid: int) -> Dict[str, Any]:
        return models.mr_detail(self._request("GET", self._mr_path(project, mr_iid)))

    def get_mr_diff(self, project: str, mr_iid: int, file_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Per-file unified diffs for an MR.

        Uses ``/diffs`` and falls back to the older ``/changes`` endpoint
        when the instance is too old to have it.
        """
        base = self._mr_path(project, mr_iid)
        try:
            items = self._paginate(f"{base}/diffs", max_results=1000)
        except GitLabNotFoundError:
            changes = self._request("GET", f"{base}/changes")
            items = safe_get(changes, "changes", default=[])
        diffs = [models.file_diff(d) for d in items]
        if file_path:
            diffs = [d for d in diffs if file_path in (d["new_path"], d["old_path"])]
        return diffs

    def get_mr_discussions(self, project: str, mr_iid: int) -> List[Dict[str, Any]]:
        items = self._paginate(f"{self._mr_path(project, mr_iid)}/discussions", max_results=500)
        return [models.discussion(d) for d in items]

    def _discussion_path(self, project: str, mr_iid: int, discussion_id: str) -> str:
        return f"{self._mr_path(project, mr_iid)}/discussions/{quote(str(discussion_id), safe='')}"

    def get_mr_discussion(self, project: str, mr_iid: int, discussion_id: str) -> Dict[str, Any]:
        return models.discussion(self._request("GET", self._discussion_path(project, mr_iid, discussion_id)))

    def get_mr_discussion_note(self, project: str, mr_iid: int, discussion_id: str, note_id: int) -> Dict[str, Any]:
        """Return one note of a discussion, or raise 404 if the discussion doesn't hold it."""
        discussion = self.get_mr_discussion(project, mr_iid, discussion_id)
        for n in discussion["notes"]:
            if n["id"] == int(note_id):
                return n
        raise GitLabNotFoundError(
            f"Note {note_id} is not in discussion {discussion_id} of MR !{mr_iid} -- "
            "check both ids with get_mr_discussions.",
            404,
        )

    # ------------------------------------------------------------------
    # Merge requests (write -- callers gate these)
    # ------------------------------------------------------------------

    def add_mr_note(self, project: str, mr_iid: int, body: str, draft: bool = False) -> Dict[str, Any]:
        base = self._mr_path(project, mr_iid)
        if draft:
            return {"draft": True, "note": self._request("POST", f"{base}/draft_notes", json_body={"note": body})}
        return {"draft": False, "note": models.note(self._request("POST", f"{base}/notes", json_body={"body": body}))}

    def resolve_inline_position(
        self,
        project: str,
        mr_iid: int,
        file_path: str,
        new_line: Optional[int] = None,
        old_line: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Work out the exact inline position for a line, without posting anything."""
        mr = self._request("GET", self._mr_path(project, mr_iid))
        diff_refs = mr.get("diff_refs")
        if not diff_refs:
            raise GitLabValidationError("MR has no diff_refs yet (still being computed?) -- try again shortly.")
        files = self.get_mr_diff(project, mr_iid, file_path=file_path)
        if not files:
            raise GitLabValidationError(f"{file_path} is not changed in this MR, so it cannot take an inline comment.")
        return resolve_position(files[0], diff_refs, new_line=new_line, old_line=old_line)

    def add_mr_discussion(
        self, project: str, mr_iid: int, body: str, position: Dict[str, Any], draft: bool = False
    ) -> Dict[str, Any]:
        base = self._mr_path(project, mr_iid)
        if draft:
            data = self._request("POST", f"{base}/draft_notes", json_body={"note": body, "position": position})
            return {"draft": True, "note": data}
        data = self._request("POST", f"{base}/discussions", json_body={"body": body, "position": position})
        return {"draft": False, "discussion": models.discussion(data)}

    def edit_mr_note(self, project: str, mr_iid: int, discussion_id: str, note_id: int, body: str) -> Dict[str, Any]:
        path = f"{self._discussion_path(project, mr_iid, discussion_id)}/notes/{int(note_id)}"
        return models.note(self._request("PUT", path, json_body={"body": body}))

    def delete_mr_note(self, project: str, mr_iid: int, discussion_id: str, note_id: int) -> None:
        self._request("DELETE", f"{self._discussion_path(project, mr_iid, discussion_id)}/notes/{int(note_id)}")


_client_singleton: Optional[GitLabClient] = None
_client_lock = threading.Lock()


def get_client() -> GitLabClient:
    """Return a process-wide singleton :class:`GitLabClient`."""
    global _client_singleton
    with _client_lock:
        if _client_singleton is None:
            _client_singleton = GitLabClient()
        return _client_singleton


def reset_client() -> None:
    """Drop the cached singleton client (primarily for tests)."""
    global _client_singleton
    with _client_lock:
        _client_singleton = None
