---
name: confluence-search
description: >-
  Runs an arbitrary CQL query against Confluence and returns structured
  page results. Use for "find pages about X", "search Confluence for
  Y", or any lookup not covered by a more specific Confluence skill.
  This is a read-only operation.
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

# Confluence: Search

**Read-only.** Run from this skill's directory:

```bash
python3 ../confluence/scripts/confluence_tool.py search --cql "space = ENG AND type = page AND text ~ 'onboarding'" \
  [--max_results 25] [--include_body]
```

(First-time setup, once per environment: `pip install -r
../confluence/requirements.txt`.)

`--cql` is required -- a real [CQL](https://developer.atlassian.com/cloud/confluence/advanced-searching-using-cql/)
query, not a plain keyword string; build it yourself (e.g.
`space = ENG`, `type = page`, `title ~ '...'` for a title match,
`text ~ '...'` for a body-content match, `label = "..."`). Never guess
a space key -- resolve it via the parent `confluence` skill's
`list_spaces`/`get_space` first if you don't already know it.

Results don't include each page's body text by default -- pass
`--include_body` only when you actually need to quote matching content,
not just list titles; page bodies are often the largest single field
per result.

If the result contains `"error"`, tell the user what went wrong in
plain language (e.g. a malformed CQL expression) instead of retrying
silently or fabricating a result.

See `../confluence/README.md` for architecture details and the full
environment-variable table.
