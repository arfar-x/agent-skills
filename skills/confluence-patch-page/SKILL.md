---
name: confluence-patch-page
description: >-
  Changes part of a Confluence page through its Markdown source block --
  exact text replacements, whole-section replacements, label changes --
  in one call, sending only the change instead of the whole page. Use for
  "change X to Y on page Z", "rewrite the Limits section", "mark this
  spec approved". Needs a page written with a source block (create_page or
  update_page with --body_markdown --source_title). This is a write
  operation gated behind explicit user confirmation.
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
    prompt: "Skip the confirm step before changing pages? (true/false)"
    required_for: optional, defaults to false (asks before every write)
---

# Confluence: Patch Page

**Write, gated.** Run from this skill's directory:

```bash
uv run ../confluence/scripts/confluence_tool.py patch_page --page_id 12345678 \
  [--find "exact old text" --replace "new text" ...] [--replace_all] \
  [--section "Heading" --section_markdown "new content" ...] \
  [--add_labels a,b] [--remove_labels c] [--title "New Title"] --confirm
```

(`uv run` installs the dependencies on first use. Without `uv`, use
`python3` in place of `uv run`, after a one-time `pip install -r ../confluence/requirements.txt`.)

The tool reads the page's Markdown source block, applies the edits,
renders the page again (keeping the source block) and writes it, then
adds/removes labels -- all in one confirmed call. Send only the change,
never the whole page:

- `--find`/`--replace` come in pairs, applied in order. Each `--find` must
  occur **exactly once** in the Markdown (include enough surrounding text
  to make it unique), unless `--replace_all`. Copy it verbatim from the
  page's `markdown_source` (returned by `confluence-get-page`) -- Markdown
  markers such as `**` are part of the text.
- `--section`/`--section_markdown` come in pairs: the content under that
  heading (to the next heading of the same or higher level) is replaced;
  the heading line stays. Pass the heading's text, with or without `#`s.
- Every edit is exact or the whole call fails and nothing is written.
- `--add_labels`/`--remove_labels` alone change labels without rewriting
  the page.

A page without a source block can't be patched -- write it once with
`confluence-update-page --body_markdown ... --source_title ...`.

The write is pinned to the version that was read: if the page was edited
in between, Confluence rejects it with a version-conflict error -- re-run
to see the new diff rather than retrying blindly.

This refuses to execute unless run with `--confirm` (enforced in code,
not just prompted). Unless `CONFLUENCE_AUTO_CONFIRM_WRITES=true` is set:

1. Run it without `--confirm` first: the result's `pending_action.diff`
   is a unified diff of exactly what will change. Show it to the user and
   wait for their explicit yes.
2. Only then re-run the same command with `--confirm` appended.
3. If the result has `"requires_confirmation": true`, treat that as the
   tool declining to act -- relay `pending_action` to the user and ask,
   don't retry with `--confirm` on your own.

If the result contains `"error"`, tell the user what went wrong in
plain language instead of retrying silently or fabricating a result.

See `../confluence/README.md` for architecture details and the full
environment-variable table.
