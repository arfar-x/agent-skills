---
name: confluence-add-comment
description: >-
  Adds a comment to a Confluence page. Use for "leave a comment on page
  X saying Y" or "comment on this page". This is a write operation
  gated behind explicit user confirmation.
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
    prompt: "Skip the confirm step before posting comments? (true/false)"
    required_for: optional, defaults to false (asks before every write)
---

# Confluence: Add Comment

**Write, gated.** Run from this skill's directory:

```bash
python3 ../confluence/scripts/confluence_tool.py add_comment --page_id 12345678 \
  --body_storage "<p>Looks good.</p>" --confirm
```

(First-time setup, once per environment: `pip install -r
../confluence/requirements.txt`.)

`--page_id` and `--body_storage` are required. `--body_storage` must be
Confluence storage-format XHTML (e.g. `<p>...</p>`), not Markdown or
plain text.

This refuses to execute unless run with `--confirm` (enforced in code,
not just prompted). Unless `CONFLUENCE_AUTO_CONFIRM_WRITES=true` is set:

1. State exactly which page and what comment text you're about to post,
   and wait for the user's explicit yes.
2. Only then re-run the same command with `--confirm` appended.
3. If the result has `"requires_confirmation": true`, treat that as the
   tool declining to act -- relay `pending_action` to the user and ask,
   don't retry with `--confirm` on your own.

If the result contains `"error"`, tell the user what went wrong in
plain language instead of retrying silently or fabricating a result.

See `../confluence/README.md` for architecture details and the full
environment-variable table.
