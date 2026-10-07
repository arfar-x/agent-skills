# GitLab (glab) Assistant

A production-ready agent skill that lets an LLM work with a GitLab
instance (self-hosted or gitlab.com) on a user's behalf -- reading
project info, repository files, merge requests, their diffs and
discussions, and posting general or inline comments on merge requests --
without ever exposing raw GitLab REST APIs to the model. Same toolset
shape as `skills/confluence/` and `skills/jira/`: runtime-specific
details stay in `SKILL.md`'s frontmatter, and the CLI itself assumes no
particular agent runtime. See the top-level `README.md`'s "Installation"
section for setup.

Its main consumer beyond direct questions is the standalone
[`code-review`](../code-review) skill, which uses this toolset to review
a remote merge request and (only when asked) post its findings back.

## Design

- **Thin tools, smart model.** Every tool in `tools/` validates input,
  calls the shared client, and returns structured JSON. No tool
  summarizes or reasons -- that happens in the agent, guided by `SKILL.md`.
- **One GitLab client.** `lib/glab_client.py` is the only code that
  talks HTTP to GitLab. It owns auth, retries, pagination
  (`page`/`per_page` + `X-Next-Page`), error normalization, and
  project-path URL encoding (`group/sub/repo` -> `group%2Fsub%2Frepo`).
  `POST`s are never auto-retried, so a transient 5xx cannot double-post
  a comment.
- **Token auth only.** `GITLAB_TOKEN` is a personal (or project/group)
  access token sent as `Authorization: Bearer`. GitLab's REST API has no
  username/password mode; the OAuth password grant is disabled by
  default on newer versions and cannot work with 2FA, so it is
  deliberately not supported. Scope `read_api` is enough to read; posting
  comments needs `api`.
- **Write operations are gated.** `add_mr_note` and `add_mr_discussion`
  refuse to execute unless called with `confirm=true` (CLI: `--confirm`),
  or `GITLAB_AUTO_CONFIRM_WRITES=true` is set.
- **Inline positions are resolved, not passed.** GitLab rejects an inline
  comment unless `position` (base/start/head SHAs, old/new line pair)
  matches the diff exactly. `add_mr_discussion` takes a plain file +
  line, parses that file's diff (`lib/diff_position.py`), and builds the
  position itself -- *before* the confirm gate, so an impossible line
  fails before the user approves anything, and the `pending_action` shows
  the line GitLab will really anchor to.
- **Drafts.** `--draft` saves a draft note (GitLab's `draft_notes` API,
  GitLab 15.9+) that only the token's user sees until they submit their
  review in the UI. Default is to publish immediately.

## Agent memory

For the **agent using these skills**, not for maintainers of this repo.
Save a fact to your runtime's persistent memory the moment you learn it,
in the same turn, unprompted.

| Fact | Source | Why it's safe to cache |
|---|---|---|
| A project's `group/repo` path -> numeric id, and its default branch | `get_project` | Renames/default-branch changes are rare |
| The token's own username | `whoami` | Fixed for a given token |

**What NOT to remember:** MR state, diffs, discussions, branch heads, and
file contents -- they change on their own and must be fetched fresh.
Test: "would this still be true next week without anyone doing anything?"

## Project layout

```
skills/glab/
├── SKILL.md                 # Skill manifest + agent instructions
├── scripts/glab_tool.py     # CLI dispatcher
├── tools/                   # One thin module per action
├── lib/
│   ├── glab_client.py       # The single GitLab REST client
│   ├── auth.py              # Env-based config + credential
│   ├── credentials.py       # Symlink -> ../../_shared/credentials/http.py
│   ├── diff_position.py     # file+line -> GitLab inline `position`
│   ├── models.py            # Payload normalizers
│   └── utils.py
└── tests/
```

Thin per-action wrapper skills (each shells out to
`../glab/scripts/glab_tool.py`):

| Skill | Action(s) |
|---|---|
| [`glab-file`](../glab-file) | `get_file`, `get_tree` |
| [`glab-mrs`](../glab-mrs) | `list_mrs` |
| [`glab-mr`](../glab-mr) | `get_mr`, `get_mr_discussions` |
| [`glab-mr-diff`](../glab-mr-diff) | `get_mr_diff` |
| [`glab-mr-comment`](../glab-mr-comment) | `add_mr_note`, `add_mr_discussion` (orchestrator, write, gated) |

## Configuration

All configuration comes from environment variables; nothing is hard-coded.

| Variable | Required | Default | Description |
|---|---|---|---|
| `GITLAB_BASE_URL` | Yes | -- | Root URL, e.g. `https://gitlab.mycompany.com` (no `/api/v4`) |
| `GITLAB_TOKEN` | Yes | -- | Personal/project/group access token. `read_api` to read, `api` to comment |
| `GITLAB_DEFAULT_PROJECT` | No | unset | Project id or `group/repo` path used when `--project` is omitted |
| `GITLAB_AUTO_CONFIRM_WRITES` | No | `false` | Skip the confirm step for MR comments |
| `GITLAB_VERIFY_SSL` | No | `true` | Disable only for trusted internal instances with self-signed certs |
| `GITLAB_TIMEOUT_SECONDS` | No | `30` | Per-request timeout |
| `GITLAB_MAX_RETRIES` | No | `3` | Retries for rate-limited/5xx `GET`s |

## Testing

```bash
cd skills/glab
pip install -r requirements.txt pytest
pytest -q
```
