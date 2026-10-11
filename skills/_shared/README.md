# `_shared`

**This directory is not a skill and must never contain a `SKILL.md`.**

It holds code that more than one toolset symlinks into its own `lib/`, so a
fix or an addition lands once instead of being hand-copied into every
toolset that needs it.

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

A toolset that needs one of these files symlinks it into its own `lib/`,
e.g.:

```bash
ln -s ../../_shared/credentials/http.py skills/jira/lib/credentials.py
ln -s ../../_shared/attachments/files.py skills/jira/lib/attachment_files.py
ln -s ../../_shared/text/patch.py skills/jira/lib/text_patch.py
```

**Windows note:** if a checkout has `git config core.symlinks false` (some
older Git-for-Windows setups without Developer Mode), a symlink materializes
as a plain text file containing the target path instead of a real symlink --
`credentials.py` would then be a one-line text file, not code. Enable
Developer Mode (or run `git config core.symlinks true` before cloning) if
you hit an import error here on Windows.

A structurally different credential shape (e.g. a future `git`-the-CLI
toolset, which needs SSH keys or a credential helper, not a value applied to
an HTTP session) gets its own module here when that toolset actually exists
-- not stubbed out speculatively ahead of it.
