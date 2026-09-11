# Confluence Assistant

A production-ready agent skill that lets an LLM act as a high-level
Confluence assistant -- finding and summarizing pages, searching
documentation, and creating/updating pages, comments, and labels --
without ever exposing raw Confluence REST APIs to the model. Follows
the same toolset shape as `skills/jira/` in this repo: runtime-specific
details are confined to `SKILL.md`'s frontmatter, and the skill body
and CLI itself don't assume any particular agent runtime -- see the
top-level `README.md`'s "Installation" section for how to set this
skill up. See "Agent memory" below for what a consuming agent should
remember across turns and sessions.

## Design

- **Thin tools, smart model.** Every tool in `tools/` only validates
  input, calls the shared Confluence client, and returns structured
  JSON. No tool summarizes, explains, or reasons -- that happens in the
  agent, guided by `SKILL.md`.
- **One Confluence client.** `lib/confluence_client.py` is the only code
  in this skill that talks HTTP to Confluence. It owns authentication,
  retries, pagination, rate-limit handling, error normalization, and
  optional response caching.
- **Deployment-aware REST path, resolved once.** Unlike Jira (which uses
  the same `/rest/api/2` path for both Cloud and Server/Data Center),
  Confluence mounts its REST API at a different path per deployment --
  Cloud under `/wiki/rest/api`, Server/Data Center directly under
  `/rest/api`. `ConfluenceClient` resolves this once from
  `CONFLUENCE_DEPLOYMENT_TYPE` at construction and uses it for every
  request; see `lib/confluence_client.py`'s module docstring. This is
  why `CONFLUENCE_DEPLOYMENT_TYPE` is a **required** setting here, where
  Jira's equivalent is optional.
- **Write operations are gated.** `create_page()`, `update_page()`,
  `delete_page()`, `add_comment()`, `add_label()`, and `remove_label()`
  refuse to execute unless called with `confirm=true` (CLI: `--confirm`),
  or `CONFLUENCE_AUTO_CONFIRM_WRITES=true` is set. This backs up
  `SKILL.md`'s confirmation rule with an enforced safety net in code.
- **Page updates auto-resolve the version.** Confluence requires every
  content update to state the next version number and rejects a stale
  one (409) -- `update_page()` fetches the page's current version and
  increments it automatically, so callers never pass one in the normal
  case (there is no Jira analog to this; a plain field edit in Jira has
  no version concept).
- **Body content is Confluence storage-format XHTML, not Markdown.**
  Both Cloud and Server/Data Center accept and return the same `storage`
  representation, so one write path and one plain-text converter
  (`lib/utils.py`'s `storage_to_plain_text()`) cover both deployments --
  the direct analog of `jira/lib/utils.py`'s Cloud-ADF-vs-Server-wiki-markup
  split, except Confluence doesn't actually have two shapes to reconcile.

## Agent memory

This section is for the **agent using these skills**, not for someone
maintaining this repo (that's the top-level `AGENTS.md`/`CLAUDE.md`).

**The rule, stated once:** save a fact to your runtime's
persistent-memory feature (if it has one) the moment you learn it -- in
the same turn, unprompted, not as a follow-up triggered by the user
asking "will you remember that?" See `skills/jira/README.md`'s own
"Agent memory" section for the full reasoning; this table is
Confluence's version of the same catalog.

| Fact | Source | Why it's safe to cache |
|---|---|---|
| A space's key and name | `list_spaces`, `get_space` | Spaces are rarely created/renamed |
| A page's resolved content id, once looked up by title | `get_page_by_title` | A page's id never changes once it exists |
| Labels actually in use on a space | `get_labels` calls over time | A team's labeling vocabulary is stable |

**What NOT to remember:** page content (body, comments, attachments),
and version numbers -- these change on their own and must always be
fetched fresh (`get_page`, `get_comments`, `page_summary`). If you're
ever unsure, ask: "would this still be true next week without anyone
doing anything?" A space's key: yes. What a page currently says: no.

## Project layout

```
skills/confluence/
├── SKILL.md                  # Skill manifest: frontmatter + agent instructions
├── scripts/
│   └── confluence_tool.py    # CLI dispatcher the agent runs via `terminal`
├── tools/                    # Thin, agent-facing entry points (Python functions)
│   ├── get_page.py
│   ├── get_page_by_title.py
│   ├── search.py
│   ├── list_spaces.py
│   ├── get_space.py
│   ├── get_comments.py
│   ├── get_attachments.py
│   ├── get_children.py
│   ├── get_labels.py
│   ├── page_summary.py
│   ├── my_pages.py
│   ├── create_page.py
│   ├── update_page.py
│   ├── delete_page.py
│   ├── add_comment.py
│   ├── add_label.py
│   └── remove_label.py
├── lib/                      # Shared implementation, not directly agent-facing
│   ├── confluence_client.py  # The single Confluence REST client
│   ├── auth.py                # Env-based configuration + validation
│   ├── models.py               # Typed, JSON-serializable data models
│   └── utils.py                 # Storage-format-XHTML-to-plain-text conversion
└── tests/                    # Unit tests for the client and every tool
```

## Configuration

All configuration comes from environment variables. **No credentials are
ever hard-coded.**

| Variable | Required | Default | Description |
|---|---|---|---|
| `CONFLUENCE_BASE_URL` | Yes | -- | Root URL of your Confluence instance, e.g. `https://mycompany.atlassian.net` (Cloud) or `https://confluence.mycompany.com` (Server/Data Center) |
| `CONFLUENCE_DEPLOYMENT_TYPE` | **Yes** | -- | `cloud` or `server` (the latter also covers Data Center). Required for every request -- Confluence's REST API path differs by deployment (see "Design" above), unlike Jira's equivalent variable which is optional |
| `CONFLUENCE_USERNAME` | Yes\*\* | -- | Basic-auth username -- set together with `CONFLUENCE_PASSWORD`, or use `CONFLUENCE_PAT` instead |
| `CONFLUENCE_PASSWORD` | Yes\*\* | -- | Basic-auth password -- set together with `CONFLUENCE_USERNAME`, or use `CONFLUENCE_PAT` instead |
| `CONFLUENCE_PAT` | Yes\*\* | -- | A Personal Access Token, Cloud API token, or other bearer token, sent as `Authorization: Bearer <token>`. Alternative to `CONFLUENCE_USERNAME`/`CONFLUENCE_PASSWORD`; takes precedence if both are set. \*\*Exactly one auth mode must be configured |
| `CONFLUENCE_TIMEOUT_SECONDS` | No | `30` | Per-request timeout |
| `CONFLUENCE_MAX_RETRIES` | No | `3` | Retries for `429`/`5xx` responses |
| `CONFLUENCE_VERIFY_SSL` | No | `true` | Disable only for trusted self-signed internal instances |
| `CONFLUENCE_AUTO_CONFIRM_WRITES` | No | `false` | Skip the confirmation gate for every write tool |
| `CONFLUENCE_CACHE_TTL_SECONDS` | No | `0` | Optional TTL cache for idempotent GET requests; `0` disables caching |
| `CONFLUENCE_DEFAULT_SPACE` | No | -- | Space key (e.g. `ENG`) used by `my_pages`/`get_page_by_title` when `--space_key` isn't given |

Configuration is validated eagerly: `lib.auth.load_config()` (behavioral
settings) and `lib.auth.load_credential()` (auth) each raise a
`ConfigurationError` with a specific, actionable message if something's
missing or inconsistent. `scripts/confluence_tool.py`'s `main()` catches
this and prints it as a clean `{"error": {...}}` JSON document rather
than a raw traceback -- same as every other error this skill's tools
produce.

This skill supports the same two auth modes as `jira`, either of which
works against both Confluence Cloud and self-hosted Confluence
Server/Data Center:

- **HTTP Basic** (`CONFLUENCE_USERNAME` + `CONFLUENCE_PASSWORD`).
- **A single bearer token** (`CONFLUENCE_PAT`), sent as `Authorization:
  Bearer <token>` -- a Confluence Data Center Personal Access Token, a
  Confluence Cloud API token used as a bearer token, or any other
  credential that fits the same shape. Takes precedence over Basic auth
  if both happen to be set.

Credential handling itself (`Credential`/`BasicCredential`/
`BearerCredential`) lives in `skills/_shared/credentials/http.py` and is
symlinked into `lib/credentials.py` -- the same file `jira` symlinks,
unchanged -- see that directory's own `README.md` for why, and for the
Windows caveat on symlinked checkouts.

## Tools

| Tool | Read/Write | Description |
|---|---|---|
| `get_page(page_id, expand)` | Read | Fetch a single page's content and metadata by id |
| `get_page_by_title(space_key, title)` | Read | Resolve a page by its space + exact title |
| `search(cql, max_results, include_body)` | Read | Arbitrary CQL search; `include_body` opts into fetching each result's body text (off by default) |
| `list_spaces(max_results)` | Read | Enumerate every space visible to the authenticated user |
| `get_space(space_key)` | Read | One space's identity and description |
| `get_comments(page_id, max_results)` | Read | Every comment on a page |
| `get_attachments(page_id, max_results)` | Read | A page's attachments (metadata only -- no upload/download support) |
| `get_children(page_id, max_results)` | Read | A page's direct child pages |
| `get_labels(page_id)` | Read | The labels currently on a page |
| `page_summary(page_id, sections)` | Read | Page + comments + attachments + labels + children, as one document (or a subset via `sections`) |
| `my_pages(max_results)` | Read | Pages the current user authored, most recently modified first |
| `create_page(space_key, title, body_storage, parent_id, confirm)` | Write (gated) | Create a new page; `body_storage` is Confluence storage-format XHTML |
| `update_page(page_id, title, body_storage, confirm)` | Write (gated) | Update a page's title and/or content; version resolved and incremented automatically |
| `delete_page(page_id, confirm)` | Write (gated) | Permanently delete a page |
| `add_comment(page_id, body_storage, confirm)` | Write (gated) | Add a comment to a page |
| `add_label(page_id, label, confirm)` | Write (gated) | Add a label to a page |
| `remove_label(page_id, label, confirm)` | Write (gated) | Remove a label from a page |

Each tool is reachable both as a Python function (`tools/<name>.py`) and
as a CLI subcommand (`scripts/confluence_tool.py <name>`); see
`SKILL.md` for the exact CLI invocation the agent uses.

There is deliberately no attachment upload/download support, and no
user-search tool -- Confluence's user-lookup endpoints diverge more
between Cloud and Server/Data Center than anything else in this
toolset, and neither was judged to earn its added surface for a first
version. Both remain real, addressable gaps if a future need justifies
them, following the same pattern as every tool above.

## Thin skills

`confluence` (this skill) works standalone as a single do-everything
skill. The repo also ships a handful of thin, `SKILL.md`-only
`skills/confluence-<action>/` wrappers -- one per the highest-value
actions below, not one per tool (see the top-level `README.md`'s
"Layout and convention": thin wrappers are the norm for a toolset meant
to be installed piecemeal, not a requirement every tool must satisfy).
Each wrapper shells out to this skill's own `scripts/confluence_tool.py`,
contains no Python of its own, and has nothing to test. **Parent skill
for every row below: `confluence`.**

| Skill | Wraps | Type |
|---|---|---|
| `confluence-get-page` | `get_page` | Read |
| `confluence-search` | `search` | Read |
| `confluence-list-spaces` | `list_spaces` | Read |
| `confluence-create-page` | `create_page` | Write (gated) |
| `confluence-update-page` | `update_page` | Write (gated) |
| `confluence-delete-page` | `delete_page` | Write (gated, destructive) |
| `confluence-add-comment` | `add_comment` | Write (gated) |

The remaining tools (`get_page_by_title`, `get_space`, `get_comments`,
`get_attachments`, `get_children`, `get_labels`, `page_summary`,
`my_pages`, `add_label`, `remove_label`) have no dedicated wrapper --
reach them through the parent `confluence` skill's own CLI, exactly as
documented in `SKILL.md`'s "Commands" section. Skipping a wrapper never
weakens the write-gating on a tool that has one; that gate lives in the
tool's own code (`tools/*.py`), not in whether a thin skill exists.

Install one thin skill by name (`npx skills add arfar-x/agent-skills
--skill confluence-search`) if you only want that one slash command, or
install `confluence` alone for the do-everything form -- see the
top-level `README.md`'s "Installation" for the general install flow.

## Running tests

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt pytest
pytest -q
```

Tests mock the HTTP layer (`requests.Session`) so they run without a
real Confluence instance, and cover: configuration validation (including
`CONFLUENCE_DEPLOYMENT_TYPE` being required, unlike Jira's equivalent),
deployment-specific REST path selection, pagination, error-code mapping
(401/403/404/409/429/5xx), storage-format-to-plain-text conversion, and
every tool's success/validation/confirmation-gate paths.

See the top-level `README.md`'s "Installation" section for how to get
this skill discoverable by whichever runtime you're using.
