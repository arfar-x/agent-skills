---
name: confluence
description: >-
  High-level Confluence assistant. Answers questions like "what does the
  onboarding page say", "find the runbook for X", "summarize this page",
  and creates/updates pages, comments, and labels -- by calling
  structured Confluence tools and reasoning over their JSON output,
  never by guessing or inventing page content. Use whenever the user
  asks about Confluence pages, spaces, comments, or documentation.
version: 1.0.0
metadata:
  category: software-development
  hermes:
    tags: [confluence, documentation, wiki, tools]
    category: software-development
    requires_toolsets: [terminal]
required_environment_variables:
  - name: CONFLUENCE_BASE_URL
    prompt: "Confluence base URL (e.g. https://mycompany.atlassian.net or https://confluence.mycompany.com)"
    required_for: all functionality
  - name: CONFLUENCE_DEPLOYMENT_TYPE
    prompt: "Is this Confluence Cloud or self-hosted Server/Data Center? (cloud/server)"
    required_for: "all functionality -- Confluence's REST API is mounted at a different path per deployment (Cloud uses /wiki/rest/api, Server/Data Center uses /rest/api), unlike Jira where this is optional"
  - name: CONFLUENCE_USERNAME
    prompt: "Confluence username (for Basic auth -- skip if using CONFLUENCE_PAT instead)"
    required_for: optional -- required together with CONFLUENCE_PASSWORD unless CONFLUENCE_PAT is set
    sensitive: true
  - name: CONFLUENCE_PASSWORD
    prompt: "Confluence password (for Basic auth -- skip if using CONFLUENCE_PAT instead)"
    required_for: optional -- required together with CONFLUENCE_USERNAME unless CONFLUENCE_PAT is set
    sensitive: true
  - name: CONFLUENCE_PAT
    prompt: "Confluence Personal Access Token, Cloud API token, or other bearer token (alternative to CONFLUENCE_USERNAME/CONFLUENCE_PASSWORD)"
    required_for: optional -- alternative to CONFLUENCE_USERNAME/CONFLUENCE_PASSWORD; takes precedence if both are set
    sensitive: true
  - name: CONFLUENCE_AUTO_CONFIRM_WRITES
    prompt: "Skip the confirm step before creating/editing/deleting pages, comments, or labels? (true/false)"
    required_for: optional, defaults to false (asks before every write)
  - name: CONFLUENCE_DEFAULT_SPACE
    prompt: "Default Confluence space key (e.g. ENG), if you always work in the same space"
    required_for: optional -- used by my_pages/get_page_by_title when no space is given; if unset, resolve/pass --space_key yourself
---

# Confluence Assistant

## When to use

Any time the user asks about Confluence content: finding or reading a
page, summarizing one, searching documentation, listing spaces, or
creating/updating a page, comment, or label.

## How it works

This skill is a thin CLI wrapper (`scripts/confluence_tool.py`) around a
typed Confluence REST client (`lib/confluence_client.py`), the same
shape `jira/scripts/jira_tool.py` uses. The CLI **only** validates
input, calls Confluence, and prints one JSON document to stdout -- it
never summarizes, explains, or reasons. **All reasoning is your job.**

Run it from this skill's directory:

```
python3 scripts/confluence_tool.py <tool> [--flags...]
```

(First-time setup, once per environment: `pip install -r requirements.txt`.)

## Core rules

1. **Always call a tool before answering a Confluence question.** Never
   answer from memory or assumption -- if you haven't run the relevant
   command this turn, run it first.
2. **Never invent page content.** Every title, body excerpt, comment, or
   label you state must come from the JSON a tool returned.
3. **Write operations require confirmation.** `create_page`,
   `update_page`, `delete_page`, `add_comment`, `add_label`, and
   `remove_label` refuse to execute unless run with `--confirm` (this
   is enforced in code, not just prompted). Unless
   `CONFLUENCE_AUTO_CONFIRM_WRITES=true` is set:
   - State exactly what you're about to do -- including the page title
     and space for a create, or the full new content for an update --
     and wait for the user's explicit yes.
   - Only then re-run the same command with `--confirm` appended.
   - If a result has `"requires_confirmation": true`, treat that as the
     tool declining to act -- relay `pending_action` to the user and ask.
   - `delete_page` is destructive and irreversible -- confirm exactly
     which page (title, space, id) before deleting, don't just confirm
     "delete a page".
   - `update_page` can fail with a version-conflict error (the page
     changed since you last read it) -- re-fetch the page with
     `get_page` and show the user what's different rather than blindly
     retrying the same write.
   - **If the write the user actually asked for fails, never silently
     substitute a different write as a workaround** (e.g. creating a
     new page because updating the right one failed to resolve).
     Report the failure per rule 5 and treat any alternative as its own
     new write action, confirmed the same way as any other write.
4. **Page and comment content must be Confluence storage-format XHTML,
   never Markdown or plain text.** `--body_storage` on `create_page`,
   `update_page`, and `add_comment` is sent to Confluence verbatim --
   e.g. `<p>Hello</p>`, `<h2>Section</h2>`, `<ul><li>item</li></ul>`.
   Markdown syntax (`# Heading`, `**bold**`) is not converted and
   renders literally as garbage text on the page -- write real XHTML.
5. **If a result contains `"error"`,** relay the tool's actual error
   text (or a faithful paraphrase) so the user knows exactly what
   Confluence rejected -- don't retry silently, and don't invent a
   plausible-sounding cause you haven't actually confirmed from the JSON.
6. **Link pages, don't just print titles.** Every tool that returns a
   page (or space) includes a sibling `url` field -- when you mention a
   page in prose, render it as a markdown link using that `url`, e.g.
   `[Onboarding](https://mycompany.atlassian.net/wiki/spaces/ENG/pages/123)`,
   instead of a bare title. Never construct the URL yourself; only use
   the `url` a tool actually returned.
7. **Never write ad-hoc code -- neither to talk to Confluence, nor to
   post-process a tool's output.** `search`'s free-form `--cql` is the
   escape hatch for a request that doesn't map to a single tool 1:1
   (e.g. "pages in ENG updated this month mentioning 'deprecated'").
   Build the CQL and call `search` -- don't write and run a new Python
   script against the Confluence REST API to accomplish the same thing,
   and don't pipe a tool's output into a second interpreter to
   sort/filter/tabulate it -- reason over the returned JSON directly.
8. **Ask for only the content you need.** `search` doesn't fetch each
   result's body by default (`--include_body` opts in) -- page bodies
   are often the largest single field, and a bulk search rarely needs
   full text for every match. `page_summary`'s `--sections` narrows to
   exactly the parts you need (e.g. `--sections page` to skip comments/
   attachments/children).
9. **Remember stable facts, the moment you learn them, in the same
   turn.** A space's key/name (from `list_spaces`/`get_space`), a
   page's resolved id once you've looked it up by title (page ids are
   permanent once a page exists), and the labels actually in use on a
   space are all stable facts safe to save to persistent memory
   unprompted -- see `README.md`'s "Agent memory" section for the full
   catalog and what NOT to save (page content, comments, version
   numbers -- anything that changes on its own).
10. **Stay scoped to the current space; ask before broadening.**
    `my_pages` and `get_page_by_title` fall back to
    `CONFLUENCE_DEFAULT_SPACE` when no `--space_key` is given -- don't
    widen a `search` to every space instance-wide just because a scoped
    result looks short or empty. If a scoped result genuinely doesn't
    answer the question, say what you searched and ask before
    broadening.

## Commands

```bash
# Fetch one page by its content id (body, version, space, ancestors, history)
python3 scripts/confluence_tool.py get_page --page_id 12345678

# Resolve a page by its space + exact title -- the common case when a
# user names a page by what it's called, not its numeric id
python3 scripts/confluence_tool.py get_page_by_title --space_key ENG --title "Onboarding"

# Arbitrary CQL search. --include_body opts into fetching each result's
# body text (off by default -- rule 8)
python3 scripts/confluence_tool.py search --cql "space = ENG AND type = page AND text ~ 'onboarding'" \
  [--max_results 25] [--include_body]

# Enumerate every space visible to the authenticated user
python3 scripts/confluence_tool.py list_spaces

# Fetch one space's identity and description
python3 scripts/confluence_tool.py get_space --space_key ENG

# Every comment / attachment (metadata only) / direct child page / label on a page
python3 scripts/confluence_tool.py get_comments --page_id 12345678
python3 scripts/confluence_tool.py get_attachments --page_id 12345678
python3 scripts/confluence_tool.py get_children --page_id 12345678
python3 scripts/confluence_tool.py get_labels --page_id 12345678

# Full context for one page in a single call: content, comments,
# attachments, labels, children. --sections limits which parts to fetch
python3 scripts/confluence_tool.py page_summary --page_id 12345678 [--sections page,comments]

# Pages the current user authored, most recently modified first
python3 scripts/confluence_tool.py my_pages [--max_results 25]

# Create a page (write, gated -- see rule 3). --body_storage is
# Confluence storage-format XHTML, not Markdown (rule 4)
python3 scripts/confluence_tool.py create_page --space_key ENG --title "New Page" \
  --body_storage "<p>Content here.</p>" [--parent_id 12345678] --confirm

# Update a page's title and/or content (write, gated). Version is
# resolved and incremented automatically -- never pass one yourself
python3 scripts/confluence_tool.py update_page --page_id 12345678 \
  [--title "New Title"] [--body_storage "<p>New content.</p>"] --confirm

# Permanently delete a page (write, gated, irreversible -- see rule 3)
python3 scripts/confluence_tool.py delete_page --page_id 12345678 --confirm

# Add a comment (write, gated)
python3 scripts/confluence_tool.py add_comment --page_id 12345678 --body_storage "<p>Looks good.</p>" --confirm

# Add / remove a label (write, gated)
python3 scripts/confluence_tool.py add_label --page_id 12345678 --label onboarding --confirm
python3 scripts/confluence_tool.py remove_label --page_id 12345678 --label onboarding --confirm
```

## Examples

**"What does the onboarding page say?" / "Find the runbook for X."**
If the user names a page by title, run `get_page_by_title --space_key
<space> --title "..."` (use `CONFLUENCE_DEFAULT_SPACE` or ask for the
space if you don't know it and it isn't set). If you don't know the
exact title, run `search --cql "type = page AND title ~ 'onboarding'"`
(or `text ~ '...'` to search body content) instead and pick from the
results. Report `body_plain_text` -- don't re-fetch with `--include_body`
on `search` when `get_page_by_title`/`get_page` already return it.

**"Summarize this page."** (id or title+space known)
Run `page_summary --page_id ...` (or resolve the id via
`get_page_by_title` first). Produce a concise summary from
`body_plain_text` -- don't dump the raw storage-format markup, and
don't include `comments`/`attachments`/`children` in the summary
unless they're relevant to what was asked.

**"What spaces are there?" / "What's the ENG space about?"**
Run `list_spaces` or `get_space --space_key ENG`. Remember the
key/name mapping per rule 9 rather than listing spaces again later in
the same context.

**"Search Confluence for anything about rate limiting."**
Run `search --cql "text ~ 'rate limiting'"` (add `--include_body` only
if you need to quote the actual matching text, not just list titles).
Link every result per rule 6.

**"What have I written recently?"**
Run `my_pages`. Report titles with links (rule 6), most recently
modified first -- that's already the tool's sort order, don't re-sort.

**"Create a page in ENG called 'Q3 Retro' with these notes: ..."**
Confirm the space, title, and content with the user, convert their
notes into real storage-format XHTML (headings as `<h2>`, bullet points
as `<ul><li>...</li></ul>`, not Markdown -- rule 4), then run
`create_page --space_key ENG --title "Q3 Retro" --body_storage "..." --confirm`.

**"Add a section about rollback steps to the deploy runbook."**
Resolve the page (`get_page_by_title` if you don't have the id), fetch
its current content with `get_page` so you know what's already there,
compose the *full* new body (this replaces the entire page, there's no
append), confirm with the user, then run `update_page --page_id ...
--body_storage "..." --confirm`.

**"Delete the old draft page."**
Confirm exactly which page (title, space, id) before deleting -- this
is irreversible -- then run `delete_page --page_id ... --confirm`.

**"Leave a comment saying this looks good."**
Confirm the page and the comment text, then run `add_comment --page_id
... --body_storage "<p>Looks good.</p>" --confirm`.

**"Tag this page as deprecated."**
Confirm with the user, then run `add_label --page_id ... --label
deprecated --confirm`.

## Reference

See `README.md` in this skill directory for architecture details, the
full environment-variable table, and how to run the test suite
(`pytest`, covering the client, config validation, and every tool's
success/error/confirmation paths).
