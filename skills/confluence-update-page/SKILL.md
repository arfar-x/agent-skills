---
name: confluence-update-page
description: >-
  Updates an existing Confluence page's title and/or content. Use for
  "update page X to say Y", "add a section about Z to the runbook", or
  "rename this page". This is a write operation gated behind explicit
  user confirmation.
version: 1.0.0
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
    prompt: "Skip the confirm step before updating pages? (true/false)"
    required_for: optional, defaults to false (asks before every write)
---

# Confluence: Update Page

**Write, gated.** Run from this skill's directory:

```bash
python3 ../confluence/scripts/confluence_tool.py update_page --page_id 12345678 \
  [--title "New Title"] [--body_storage "<p>New content.</p>"] --confirm
```

(First-time setup, once per environment: `pip install -r
../confluence/requirements.txt`.)

`--page_id` is required; give at least one of `--title`/`--body_storage`.
**`--body_storage` replaces the entire page body -- there is no partial
or append update.** If the user asked to add a section rather than
replace the page, first fetch the page's current content (the parent
`confluence` skill's `get_page`), compose the *full* new body with your
addition included, then pass that whole thing here. Content must be
Confluence storage-format XHTML, never Markdown.

The page's version number is resolved and incremented automatically --
never pass one yourself. If the page was edited since you last read it,
Confluence rejects the write with a version-conflict error -- re-fetch
the page and show the user what changed rather than blindly retrying
the same write.

This refuses to execute unless run with `--confirm` (enforced in code,
not just prompted). Unless `CONFLUENCE_AUTO_CONFIRM_WRITES=true` is set:

1. State exactly what you're about to change -- the new title and/or a
   summary of the new content -- and wait for the user's explicit yes.
2. Only then re-run the same command with `--confirm` appended.
3. If the result has `"requires_confirmation": true`, treat that as the
   tool declining to act -- relay `pending_action` to the user and ask,
   don't retry with `--confirm` on your own.

If the result contains `"error"`, tell the user what went wrong in
plain language instead of retrying silently or fabricating a result.

See `../confluence/README.md` for architecture details and the full
environment-variable table.
