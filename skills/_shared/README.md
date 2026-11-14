# `_shared`

**This directory is not a skill and must never contain a `SKILL.md`.**

It holds the source of code that more than one toolset needs. Each toolset
keeps a real copy in its own `lib/`, written by `scripts/sync_shared.py`, so a
fix or an addition lands once here and is propagated by one command instead of
being hand-edited in every toolset.

Both consumers this repo currently has visibility into discover skills by
walking for `SKILL.md` presence, not by listing directory names under
`skills/`:

- This repo's own `mcp-server/lib/registry.py` builds its candidate list from
  `entry.is_dir() and skill_md.exists()` -- a directory with none never enters
  the list.
- [`npx skills`](https://github.com/vercel-labs/skills)'s own `discoverSkills`
  does the same.

So a directory here with no `SKILL.md` is structurally invisible to both --
not specially excluded, just never considered. `mcp-server/tests/test_registry.py`
asserts this stays true; adding a `SKILL.md` here would fail that test on
purpose.

## Layout

```
attachments/
└── files.py  # Local-file side of attachment upload/download: safe remote
              # file names, no-overwrite atomic capped download writes,
              # upload-file validation. No HTTP -- each toolset's client
              # does its own requests. Used by Jira and Confluence.
credentials/
└── http.py   # Credential protocol + BasicCredential/BearerCredential/
              # NoCredential -- the HTTP-session family. Used by any
              # toolset that authenticates a `requests.Session` (Jira
              # today; Confluence and GitLab's REST/GraphQL APIs fit the
              # same shape).
text/
└── patch.py  # Exact, unambiguous text replacement for partial edits of
              # a stored document (find must occur exactly once unless
              # replace_all; pairs are all or nothing). Used by Jira
              # (description edits) and Confluence (page Markdown).
```

A toolset that needs one of these files gets a copy in its own `lib/`.
Register the pair in `CONSUMERS` in `scripts/sync_shared.py`, then:

```bash
make sync-shared    # copy every shared file into its consumers' lib/
make check-shared   # fail if a copy is missing, a symlink, or has drifted
```

**Why copies, not symlinks:** `npx skills add` installs a skill by copying
only that skill's directory, and it skips any symlink that resolves outside
it (`SKILLS_SYMLINK_OUTSIDE_SKILL`). A `lib/credentials.py` symlinked to
`../../_shared/...` is therefore missing from the installed skill and the
toolset fails on import. Real files install correctly, with no manual fix on
the user's machine. Always edit the file here, never the copy; the copies are
byte-identical and `scripts/tests/test_sync_shared.py` enforces it.

A structurally different credential shape (e.g. a future `git`-the-CLI
toolset, which needs SSH keys or a credential helper, not a value applied to
an HTTP session) gets its own module here when that toolset actually exists
-- not stubbed out speculatively ahead of it.
