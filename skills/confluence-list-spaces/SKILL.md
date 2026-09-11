---
name: confluence-list-spaces
description: >-
  Enumerates every Confluence space visible to the authenticated user.
  Use for "what spaces are there", "what's the key for the engineering
  space", or before creating a page when the destination space key
  isn't already known. This is a read-only operation.
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

# Confluence: List Spaces

**Read-only.** Run from this skill's directory:

```bash
python3 ../confluence/scripts/confluence_tool.py list_spaces [--max_results 100]
```

(First-time setup, once per environment: `pip install -r
../confluence/requirements.txt`.)

Each space's `key` is what every other Confluence tool needs as
`--space_key` -- resolve it here rather than guessing one from a
space's display name.

A space's key and name are stable facts -- if your runtime has
persistent memory, save them the moment you learn them (same turn,
unprompted) rather than calling this again later. See
`../confluence/README.md`'s "Agent memory" section.

If the result contains `"error"`, tell the user what went wrong in
plain language instead of retrying silently or fabricating a result.

See `../confluence/README.md` for architecture details and the full
environment-variable table.
