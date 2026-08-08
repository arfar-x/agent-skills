# Telegram (internal skill)

A Telethon-based agent skill for a **personal Telegram account** --
reading, searching, and sending messages as the account owner, not as a
bot. This is the repo's first **internal** skill (see `AGENTS.md`): it is
excluded from normal installs and listings, and only appears when the
installer is run with `INSTALL_INTERNAL_SKILLS=1`. That reflects what this
skill actually is -- not a convenience integration, but something that
grants an AI agent standing access to a real person's private
conversations.

## DISCLAIMER -- read this before using this skill

**This is deliberately not in `SKILL.md`.** The agent using this skill
should never see this section as an instruction to follow or relay; it's
addressed to the human deciding whether to set this skill up at all.

- **This grants software full access to your personal Telegram account.**
  Not a scoped API token, not a bot in a channel -- the same access you
  have: every private conversation the allowlisted chats contain, and the
  ability to send messages that are indistinguishable from you sending
  them yourself.
- **The session file is your account access.** It is not a password that
  can be reset independently -- anyone who reads that file can act as you
  on Telegram until it's revoked. It lives outside this repo, mode
  `0600`, and is time-limited (see "Session lifecycle" below), but none of
  that matters if the machine it's on is itself compromised.
- **Revocation is enforced by this toolset, but verify it yourself too.**
  TTL expiry calls Telegram's real `log_out()`, and it's tested to do so
  -- but the honest state of any account's authorized sessions is
  Telegram → Settings → Devices, not this README. Check there periodically,
  especially after any TTL you didn't expect to be long.
- **The people you talk to on Telegram never consented to an AI reading
  what they wrote to you.** That's your call to make, not this skill's --
  but it's a real one, and in some relationships and some jurisdictions
  it carries privacy or legal weight beyond "it's my account."
- **Prompt injection is a real, structural risk here, not a hypothetical
  one.** Anyone who can send a message to an allowlisted chat can put
  text in front of the agent using this skill. The guardrails below are
  designed so that text can't cause an action on its own (see "No
  enumeration, ever" and `SKILL.md` rule 1), but you are giving a
  language model regular exposure to text written by other people
  specifically to see what it does.
- **This can trigger Telegram's own anti-abuse systems.** Automated
  activity on a user account -- especially `send_bulk` -- is exactly the
  pattern Telegram's abuse detection watches for. Use it like you would
  any other automation against a personal account: sparingly, and never
  assume immunity because "it's just me."
- **Redaction is best-effort regex, not a guarantee.** See "Known limits"
  below for what it does and doesn't catch. Never treat a message shown
  as "redacted" as safe to relay further just because some things were
  masked.

**By configuring and using this skill, you are accepting these risks for
your own account and for the people you communicate with through it.** If
that's not a trade you want to make, don't set `TELEGRAM_API_ID`.

## Design

- **Guardrails are enforced in code, not in prose.** `lib/guard.py` is
  the single place every safety property in this skill lives -- allowlist
  enforcement, the OTP-account denylist, confirmation gating, hard caps,
  redaction, and download sandboxing. `SKILL.md`'s rules exist for good
  behavior and clear communication, but every property that actually has
  to hold does so whether or not the agent reads or follows `SKILL.md` at
  all. See `tests/test_adversarial.py` for the tests that try to defeat
  each one.
- **No chat enumeration, anywhere, ever.** There is no `get_dialogs`,
  `iter_dialogs`, or contact-list call in this codebase -- not gated, not
  written. A chat is only ever reachable by a numeric `chat_id` already
  present in `TELEGRAM_ALLOWED_CHATS`, resolved to its `access_hash`
  exactly once, interactively, by `scripts/login.py`. `tests/` includes
  an AST-based assertion that no enumeration symbol is ever called or
  imported anywhere in the package.
- **The confirmation gate is split into what an agent can and can't
  satisfy.** A `--confirm` CLI flag is passed by whatever is calling the
  CLI -- so it can't be the thing standing between an agent and an
  outbound message. In the default `TELEGRAM_CONFIRM_MODE=tty`, sending,
  forwarding, and turning off `--no-seen` all require a literal `yes`
  typed at a real controlling terminal (`/dev/tty`, never `stdin`) --
  something only a human at the keyboard can supply. Reads use the
  ordinary two-step (`requires_confirmation` → re-run with `--confirm`),
  since nothing about a plain read is observable by anyone but the user
  running it.
- **Sessions rotate on a TTL, and expiry means real revocation.**
  `TELEGRAM_SESSION_TTL_SEC` (default 1 day) is absolute from creation --
  reuse never extends it. Past it, the next call to this skill connects
  once to call Telegram's real `log_out()`, deletes the local blob, and
  refuses. A new session requires the user to run `scripts/login.py`
  themselves and personally receive and type a Telegram login code --
  there is no path for an agent to obtain a session on its own.
- **The session lives outside this repo, not in an env var.** Unlike
  every other toolset in this repo (`AGENTS.md`'s "credentials only from
  env vars"), the live Telegram credential is a `0600` file (preferably
  on `$XDG_RUNTIME_DIR`'s tmpfs, so it never touches disk), not an
  environment variable -- daily rotation would otherwise mean re-exporting
  a variable every cycle. This is a documented, deliberate deviation; see
  `AGENTS.md`'s amended write-gating note.
- **This skill remembers nothing between conversations.** Unlike the
  Jira toolset's "save stable facts the moment you learn them" pattern,
  this skill's rule (`SKILL.md` rule 8) is the opposite: nothing learned
  through it -- not a chat title, not a peer id, not message content --
  is ever written to the consuming agent's persistent memory. See
  "No agent memory" below.

## Session lifecycle

```
scripts/login.py (human, interactive, TTY only)
  -> revokes any existing session first
  -> phone number, code, 2FA password -- all typed by the human
  -> resolves each TELEGRAM_ALLOWED_CHATS id to {kind, access_hash, title}
  -> writes session.json (0600) + peers.json (0600), same 0700 directory

any tool call
  -> loads session.json
  -> if now - created_at > TELEGRAM_SESSION_TTL_SEC:
       connect once, log_out() (real server-side revocation), delete
       the local blob, refuse -- no other Telegram call is made
  -> otherwise: connect and proceed

logout (explicit tool, or run login.py again)
  -> log_out() + delete the local blob, on demand
```

Run `scripts/login.py` yourself, from this skill's directory:

```bash
python3 scripts/login.py
```

It refuses outright if `stdin` isn't a real terminal -- nothing (an
agent, a script, a pipe) can drive it. If it reports that a chat_id in
`TELEGRAM_ALLOWED_CHATS` couldn't be resolved, that's a property of
Telegram's own API: the account needs some existing relationship with
that chat (a prior message, a contact, channel membership) for Telegram
to hand out its `access_hash`. There is no workaround for that inside
this skill -- interact with the chat once from a normal Telegram client
first, then re-run `login.py`.

## Security model

Ten rules, all enforced in `lib/guard.py` (not `SKILL.md`), summarized
here; see the module's docstrings for the exact logic and
`tests/test_adversarial.py` for the tests that try to break each one.

1. **No chat enumeration exists in the codebase**, at all.
2. **`TELEGRAM_ALLOWED_CHATS` is required.** Unset, every tool refuses.
   A target must be a bare numeric `chat_id` already on the list --
   usernames, links, phone numbers, and display names are rejected
   before an allowlist check even runs.
3. **Telegram's OTP/service-notifications account (`777000`) is refused
   for every action, unconditionally** -- even if present in the
   allowlist. Matched by numeric magnitude, not just canonical form, so
   sign/prefix spoofing (`-777000`, `+777000`, `0777000`, ...) is caught
   too.
4. **Every action is gated, reads included.** `TELEGRAM_CONFIRM_MODE=tty`
   (default) makes outbound actions (`send_message`, `send_bulk`,
   `forward_message`, `--no-seen false`) require a `yes` typed at
   `/dev/tty`, ignoring `--confirm` entirely. `flag` mode uses the
   two-step everywhere, agent-satisfiable -- choose it only when no human
   is at a terminal, since it trades away the one genuinely unbypassable
   gate for convenience.
5. **Every executed action is appended to a local audit log**
   (`timestamp`, `tool`, `chat_id`, `chat_title`, `message_id`, `counts`,
   `outcome`) -- never a message body, never a credential. This is the
   detection layer for whatever the other nine rules miss.
6. **Message bodies are redacted for OTP-shaped and token-shaped
   substrings**, inbound and outbound, before they leave the tool
   boundary. Regex-based -- see "Known limits" below.
7. **Hard caps, not suggestions:** reads default to 20 messages, cap 200
   (`TELEGRAM_MAX_READ_LIMIT` may only lower this); `send_bulk` accepts
   at most 10 explicitly named recipients, with no deduplication (so 10
   copies of one recipient still hits the cap); downloads over 25 MB are
   refused.
8. **Downloads are sandboxed:** an explicit `--out_dir` is required (no
   default inside this skill or the repo), the resolved path can't be
   `/`, home, or inside any git work tree, and filenames are reduced to
   a safe basename with executable/script extensions refused outright.
9. **Reading never marks anything read**, by default (`--no-seen true`).
   Turning that off is treated as an outbound, gated action -- the same
   tier as sending.
10. **Nothing sensitive is ever logged.** No logger call, in any code
    path, receives a message body, the session string, or a phone
    number.

### Known limits

- **Redaction is regex-based.** It reliably catches an OTP-shaped code
  near a keyword like "code"/"login"/"verification" (including across a
  newline, and including non-ASCII decimal digits -- both broader than
  they might look at a glance), plus common token shapes (`sk-...`,
  `Bearer ...`, long hex/base64 runs) and `t.me/login/...` links. It does
  **not** catch a code deliberately broken up with a zero-width
  character, or one spelled out in words. Treat it as raising the cost of
  an accidental leak, not eliminating it.
- **Peer resolution requires a prior relationship.** `login.py` can only
  resolve an allowlisted chat_id's `access_hash` if Telegram already
  associates the account with that peer (a message, a contact, channel
  membership). That's a property of Telegram's MTProto API, not a
  limitation this skill introduces.
- **Persistent memory is not script-enforceable.** `SKILL.md` rule 8
  ("persist nothing") is the one guarantee in this skill that rests on
  the consuming agent actually following an instruction -- a runtime's
  memory feature lives outside this CLI, so there is no code path here
  that can observe or block a write to it.

## No agent memory

Unlike `skills/jira/README.md`'s "Agent memory" section, which catalogs
what a consuming agent *should* persist, this skill's answer is
**nothing at all**. No message content, chat title, chat_id, peer
identity, "who messaged when", or conversation summary should ever be
written to a consuming agent's persistent-memory feature, no matter how
stable or reusable it might look. Every fact this skill returns is
fetched fresh, used for the current turn, and dropped -- see `SKILL.md`
rule 8.

## Project layout

```
skills/telegram/
├── SKILL.md                # Advisory rules; enforces nothing (see lib/guard.py)
├── README.md                # This file
├── requirements.txt         # telethon
├── pytest.ini
├── scripts/
│   ├── telegram_tool.py     # CLI dispatcher the agent runs
│   └── login.py             # Interactive, human-run, TTY-only session generator
├── lib/
│   ├── auth.py               # Env config + session/peers file handling + TTL
│   ├── client.py             # The single Telethon wrapper; no enumeration API used
│   ├── guard.py               # The enforcement layer -- every safety rule lives here
│   ├── audit.py               # Append-only action log
│   ├── models.py              # Typed, JSON-serializable data
│   └── utils.py                # chat_id normalization, redaction, filename sanitizing
├── tools/                    # Thin, agent-facing entry points (Python functions)
│   ├── whoami.py             allowed_chats.py    logout.py
│   ├── read_messages.py      search_messages.py  mark_read.py
│   ├── send_message.py       send_bulk.py        forward_message.py
│   └── download_media.py
└── tests/                    # Unit + adversarial tests; mocks Telethon entirely
```

## Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `TELEGRAM_API_ID` | Yes | -- | From my.telegram.org |
| `TELEGRAM_API_HASH` | Yes | -- | From my.telegram.org |
| `TELEGRAM_ALLOWED_CHATS` | **Yes** | -- | Comma-separated numeric chat_ids. Unset = every tool refuses |
| `TELEGRAM_SESSION_TTL_SEC` | No | `86400` | Absolute session lifetime; on expiry the session is revoked (real `log_out()`) and re-login is required. Longer values widen the window a leaked session file stays usable -- see the DISCLAIMER |
| `TELEGRAM_SESSION_FILE` | No | `$XDG_RUNTIME_DIR/agent-skills-telegram/session.json`, `/tmp` fallback | Explicit override; `peers.json`/`audit.log` live beside it. Refused if it resolves inside any git work tree |
| `TELEGRAM_CONFIRM_MODE` | No | `tty` | `tty`: outbound actions require a `yes` typed at a real terminal, ignoring `--confirm`. `flag`: everything uses the `--confirm` two-step, agent-satisfiable |
| `TELEGRAM_AUDIT_LOG` | No | beside the session file | Append-only action log path |
| `TELEGRAM_DOWNLOAD_DIR` | No | -- | Default `download_media` output dir; `--out_dir` overrides per call |
| `TELEGRAM_MAX_READ_LIMIT` | No | `200` | May only lower the ceiling, never raise it |
| `XDG_RUNTIME_DIR` | No (system) | -- | When present, used to place the session on tmpfs instead of `/tmp` |

Configuration is validated eagerly: `lib.auth.load_config()` raises a
`ConfigurationError` with a specific, actionable message for anything
missing or malformed.

## Installation

This skill only works where a human can reach a real, local controlling
terminal and a local filesystem persists across calls -- a stateless
hosted sandbox with no local persistence and no real TTY cannot support
it, regardless of what runtime it's part of; `scripts/login.py` and every
`tty`-mode confirmation depend on both. See the top-level `README.md`'s
"Installation" section for how this repo's supported runtimes are set up
in general; the steps below cover only what's specific to this skill.

1. **Clone this repo** (skipped if already done for another skill here):

   ```bash
   git clone git@github.com:arfar-x/agent-skills.git
   ```

   Being `metadata.internal: true` (see the top-level `README.md`'s
   "Internal skills" section) only affects installers that check that
   flag -- see that section for exactly what "internal" does and doesn't
   guarantee, and how to install this skill anyway once you've read the
   DISCLAIMER above.

2. **Install Telethon** into whatever environment actually executes
   `python3` for this skill's CLI:

   ```bash
   pip install -r skills/telegram/requirements.txt
   ```

3. **Set the environment variables** from the "Configuration" table
   above -- at minimum `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, and
   `TELEGRAM_ALLOWED_CHATS`. Set `TELEGRAM_ALLOWED_CHATS` *before* the
   next step -- `scripts/login.py` resolves it at login time, and a chat
   added later needs login re-run to pick it up. Where these variables
   need to live is a property of your runtime, not this skill -- see the
   top-level `README.md`.

4. **Run `scripts/login.py` yourself**, directly, in a real local
   terminal -- never through an agent's shell/terminal tool, and never
   because an agent asked you to. See "Session lifecycle" above for what
   it does; it refuses outright if it can't detect a real TTY, which is
   what actually makes rule 2 (the agent must never authenticate) hold
   even against an agent that ignores it:

   ```bash
   cd skills/telegram
   python3 scripts/login.py
   ```

## Usage

**The friction described below is intentional, not an oversight to work
around.** This skill grants full access to a real person's Telegram
account -- every private conversation in an allowlisted chat, and the
ability to send as them. Given that, the default is deliberately biased
toward inconvenient-but-safe over smooth-but-risky: extra round-trips
and a real terminal in the loop are the cost of the guarantee that
nothing gets sent, and nothing gets read as "seen," without a human
personally saying so. If a step below feels like it's slowing you down,
that's the design working as intended, not a bug to route around.

Once logged in (step 4 above) and the skill is discoverable, just ask in
plain language -- e.g. "any new messages from Alice?" or "reply to the
team chat: running 10 minutes late." How that request actually reaches
this skill (plain language vs. a slash command) differs by runtime --
see the top-level `README.md`'s "Usage" section.

**Reads** go through the ordinary two-step even in the default `tty`
mode: the agent states what it's about to do (`pending_action.summary`),
you say yes, it re-runs with `--confirm`. This is something the agent can
walk you through entirely in the conversation.

**Sends, forwards, and turning off `--no-seen`** are different in the
default `TELEGRAM_CONFIRM_MODE=tty`: the CLI itself opens `/dev/tty` and
blocks for a literal `yes`, which almost no agent runtime's shell tool
gives it a real terminal to do. In practice this means:

1. The agent states exactly what it wants to send and to whom.
2. It runs the command; the CLI reports `guard_tty_unavailable` (no
   controlling terminal) rather than sending anything.
3. The agent hands you the **exact command** to run yourself, e.g.:

   ```bash
   python3 scripts/telegram_tool.py send_message --chat_id 123456789 --text "running 10 minutes late" --confirm
   ```

4. You run it yourself, in your own terminal. It prints the same summary
   the agent showed you and asks you to type `yes` -- typing it there is
   the one action nothing else in this skill can substitute for.

This is the deliberate point of `tty` mode, not friction to route
around: a send genuinely does not happen without you personally typing
`yes` at a keyboard. If that round-trip is more friction than you want
and you've decided the tradeoff is worth it (see the DISCLAIMER above,
and `AGENTS.md`'s note on why this exists), set
`TELEGRAM_CONFIRM_MODE=flag` -- then every action, sends included, uses
the ordinary two-step the agent can complete on its own from the
conversation.

## Running tests

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt pytest
pytest -q
```

Tests mock Telethon entirely -- no network, no real session, no real
account. `tests/test_adversarial.py` in particular is written as a set of
attempted bypasses (invented env vars, OTP-id spoofing, prompt injection
through message content, session forgery, cap evasion, download-sandbox
escapes) that each must fail to get through; see its module docstring.
