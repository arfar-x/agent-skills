---
name: confluence-create-page
description: >-
  Creates a new Confluence page in a space, optionally as a child of an
  existing page. Use for "create a page in X called Y" or "add a new
  page under Z". This is a write operation gated behind explicit user
  confirmation.
version: 1.1.0
metadata:
  category: software-development
  hermes:
    tags: [confluence, documentation, wiki, write]
    category: software-development
    requires_toolsets: [terminal]
required_environment_variables:
  - name: CONFLUENCE_BASE_URL
    prompt: "Confluence base URL (e.g. https://mycompany.atlassian.net or https://confluence.mycompany.com)"
    required_for: all functionality
  - name: CONFLUENCE_DEPLOYMENT_TYPE
    prompt: "Is this Confluence Cloud or self-hosted Server/Data Center? (cloud/server)"
    required_for: "all functionality -- Confluence's REST API is mounted at a different path per deployment"
  - name: CONFLUENCE_USERNAME
    prompt: "Confluence username"
    required_for: basic auth mode (the default)
  - name: CONFLUENCE_PASSWORD
    prompt: "Confluence password"
    required_for: basic auth mode (the default)
  - name: CONFLUENCE_AUTO_CONFIRM_WRITES
    prompt: "Skip the confirm step before creating pages? (true/false)"
    required_for: optional, defaults to false (asks before every write)
---

# Confluence: Create Page

**Write, gated.** Run from this skill's directory:

```bash
uv run ../confluence/scripts/confluence_tool.py create_page --space_key ENG --title "New Page" \
  --body_storage "<p>Content here.</p>" [--parent_id 12345678] --confirm
# or, from Markdown -- rendered by the tool, optionally kept on the page for later patching
uv run ../confluence/scripts/confluence_tool.py create_page --space_key ENG --title "New Page" \
  --body_markdown "# New Page..." [--source_title "Markdown source"] [--labels a,b] --confirm
```

(`uv run` installs the dependencies on first use. Without `uv`, use
`python3` in place of `uv run`, after a one-time `pip install -r ../confluence/requirements.txt`.)

`--space_key` and `--title` are required, plus exactly one of
`--body_storage` or `--body_markdown`. `--body_storage` must be
Confluence **storage-format XHTML** -- e.g. `<p>...</p>`, `<h2>...</h2>`
-- never Markdown, which would render literally. To write Markdown, pass
`--body_markdown` instead and the tool renders it. With `--source_title`
the Markdown is also kept on the page as a collapsed source block, so a
later change can go through `confluence-patch-page` instead of a full
rewrite. `--labels` (comma-separated) are added right after creation, in
the same confirmed call. `--parent_id` is optional -- pass it to create this as a child of
an existing page instead of a space-root page.

This refuses to execute unless run with `--confirm` (enforced in code,
not just prompted). Unless `CONFLUENCE_AUTO_CONFIRM_WRITES=true` is set:

1. State exactly what you're about to create -- the space, title, and a
   summary of the content -- and wait for the user's explicit yes.
2. Only then re-run the same command with `--confirm` appended.
3. If the result has `"requires_confirmation": true`, treat that as the
   tool declining to act -- relay `pending_action` to the user and ask,
   don't retry with `--confirm` on your own.

If the result contains `"error"`, tell the user what went wrong in
plain language instead of retrying silently or fabricating a result.

See `../confluence/README.md` for architecture details and the full
environment-variable table.
