---
name: confluence-get-page
description: >-
  Fetches a single Confluence page's content and metadata by its
  content id. Use for "what does page X say", "show me page 12345678",
  or as the first step in summarizing/editing a page once you know its
  id. This is a read-only operation.
version: 1.0.0
metadata:
  category: software-development
  hermes:
    tags: [confluence, documentation, wiki, read]
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
---

# Confluence: Get Page

**Read-only.** Run from this skill's directory:

```bash
python3 ../confluence/scripts/confluence_tool.py get_page --page_id 12345678
```

(First-time setup, once per environment: `pip install -r
../confluence/requirements.txt`.)

`--page_id` is required. If you only know a page's title and space
(not its numeric id), use `get_page_by_title` on the parent
`confluence` skill's CLI instead -- see `../confluence/SKILL.md`.

The returned `page.body_plain_text` is a best-effort plain-text
rendering of the page's real storage-format content -- report that
text, don't re-derive or paraphrase from the raw markup.

If the result contains `"error"`, tell the user what went wrong in
plain language instead of retrying silently or fabricating a result.

See `../confluence/README.md` for architecture details and the full
environment-variable table.
