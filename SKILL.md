---
name: brightbean-studio
description: |
  Draft, schedule, update, and cancel social-media posts via the Brightbean
  Studio Agent API. Trigger when the user wants to publish or schedule a post
  to LinkedIn (personal or company), Facebook, Instagram, TikTok, YouTube,
  Pinterest, Threads, Mastodon, Bluesky, or Google Business through a
  Brightbean Studio workspace, or to inspect / cancel posts already
  scheduled there. Works with both Streamable HTTP MCP (preferred when
  available) and a REST API at `/api/v1/...`. Requires a `bb_studio_...`
  bearer token issued from the Brightbean Studio org settings.
---

# Brightbean Studio Agent

You can act on the user's social-media accounts through their Brightbean
Studio workspace. The studio is a multi-tenant scheduler — every action
runs inside one Organization, one Workspace, and against one of the
SocialAccounts the API key explicitly allowlists.

## When to use this skill

Use when the user asks to:

- Draft a post (LinkedIn / Facebook / Instagram / TikTok / YouTube / Pinterest /
  Threads / Mastodon / Bluesky / Google Business)
- Schedule a post for a specific future time
- Inspect the status of a post you previously created
- Cancel a scheduled post
- List the connected accounts available to act on

Do NOT use this skill when:

- The user only wants help writing copy (no schedule/publish involved)
- The platform isn't on the supported list above (e.g. native X/Twitter — not
  in Brightbean's `PlatformCredential.Platform` choices today)
- The user wants analytics or comment moderation — not in scope for v1

## Quick start

The single most important question: **does the runtime have MCP access to a
`brightbean-studio` server?** If yes, prefer the MCP tool calls — they're
typed, validated against `inputSchema`, and produce cleaner responses than
HTTP JSON. If not, use the REST API.

You can probe MCP availability by attempting `list_accounts` first; if the
tool isn't registered, fall back to `GET /api/v1/accounts/`.

### Step 1 — Make sure you have a token

The token format is `bb_studio_<random>_<lookup>`. The user generates it
from **Organization Settings → API Keys** in the Brightbean Studio UI. If
the user says "I haven't created one yet," walk them through:

1. Open the Brightbean Studio app
2. Go to Organization Settings → API Keys (sidebar)
3. Click **Issue new key**
4. Pick the workspace and the connected accounts the agent should act on
5. Tick the permissions:
   - **`create_posts`** — required for drafting and editing
   - **`publish_directly`** — required for scheduling (the API splits
     these so an editor can draft but only a publisher can schedule)
6. Copy the plaintext token from the one-time reveal modal. **Brightbean
   doesn't store it; if the user closes that modal, they need to issue a
   new key.**

### Step 2 — Discover scope

Always call this first when starting a new session, so you know which
account IDs are valid:

- MCP: `list_accounts` (no arguments)
- REST: `GET /api/v1/accounts/`

The response lists every `SocialAccount` the key may act on, with its
`id`, `platform`, `account_name`, `account_handle`, and `connection_status`.
A `connection_status` other than `"connected"` means the user needs to
re-link the account before you can schedule into it — Brightbean rejects
scheduling on disconnected accounts and would burn a quota slot otherwise.

### Step 3 — Draft, then schedule

Two-step pattern (recommended):

1. **Draft** the post (low-risk, no permission needed beyond `create_posts`,
   easy to iterate on copy with the user)
2. **Schedule** the draft once the user confirms the copy + the timing

You can also create-and-schedule in one call if the user is confident.

For copy length, Brightbean Studio's per-platform character limits live
in `apps/social_accounts/models.py::SocialAccount.char_limit`:

| Platform              | Character limit |
|-----------------------|-----------------|
| linkedin_personal     | 3000            |
| linkedin_company      | 3000            |
| facebook              | 63,206          |
| instagram             | 2200            |
| tiktok                | 2200            |
| youtube               | 5000            |
| pinterest             | 500             |
| threads               | 500             |
| bluesky               | 300             |
| mastodon              | 500             |

Always confirm with the user before scheduling — there is no built-in
"are you sure?" gate beyond `publish_directly` permission.

## Common workflows

Detailed walkthroughs (Python + shell) live in `examples/`:

- `examples/python/01_list_accounts.py` and `examples/shell/list_accounts.sh`
- `examples/python/02_create_draft.py` and `examples/shell/create_draft.sh`
- `examples/python/03_schedule_post.py` and `examples/shell/schedule_post.sh`
- `examples/python/04_cancel_post.py` and `examples/shell/cancel_post.sh`
- `examples/python/05_idempotent_retry.py` and `examples/shell/idempotent_retry.sh`
- `examples/python/06_mcp_client.py` — pure JSON-RPC over HTTP, no SDK needed

Read those before composing your own request — the canonical request /
response shapes for every endpoint are there.

## Critical contracts

### Idempotency

Every POST endpoint (`/posts/` create, `/posts/{id}/schedule`,
`/posts/{id}/cancel`) accepts an `idempotency_key` field (REST body) or
an `idempotency_key` argument (MCP tools, when present). **Always set
this when you're doing a write you'd retry on network error.** The
server stores the first response for 24 hours and replays it on
matching retries; if the same key arrives with a different body, you'll
get HTTP 422.

A simple convention: `idempotency_key = f"{user_session_id}-{action}-{uuid4()}"`.

### Allowlist enforcement (security boundary)

The API key allowlists specific `SocialAccount` IDs. Two things follow:

1. Any `POST /posts/` body that names a `social_account_id` outside the
   allowlist returns **HTTP 403**. Don't try to fetch a list of "all
   accounts in the workspace" — the key wouldn't see them.
2. `GET /posts/{id}`, `PATCH /posts/{id}`, `/schedule`, `/cancel` return
   **HTTP 404** if any child of the post targets an account outside the
   allowlist. 404 (not 403) is deliberate — the API doesn't leak the
   existence of foreign post IDs.

### Approval workflow

If the workspace is configured with `approval_workflow_mode` set to
`required_internal` or `required_internal_and_client`, **direct scheduling
is rejected with HTTP 422** and a message about the approval workflow.
In that case, the user has to route the post through their internal
approval flow before it can be scheduled. There's no API-only way to
bypass this.

### Rate limits

Six tiers stack:

| Tier                  | Default          | When you'll hit it                          |
|-----------------------|------------------|----------------------------------------------|
| Per-key writes        | 120/min          | Bulk-importing >120 posts in one minute      |
| Per-key reads         | 300/min          | Polling status faster than ~5 reads/s        |
| Per-key publish hop   | 1/5s per account | Triggering many schedule actions for one acct|
| Per-workspace writes  | 1000/min agg     | Multiple keys aggregating in one workspace   |
| Per-IP failed auth    | 10/min           | Bad bearer brute-force defense               |
| Per-platform 24h cap  | platform-specific (see below) | Daily platform quota                |

Per-platform 24h caps (default; overridable per-account):

| linkedin (any) | facebook | instagram | tiktok | youtube | pinterest | threads | mastodon | bluesky | google_business |
|----------------|----------|-----------|--------|---------|-----------|---------|----------|---------|------------------|
| 100            | 200      | 25        | 15     | 50      | 100       | 250     | 200      | 200     | 50               |

The 429 response carries `Retry-After` (HTTP header, seconds) and a JSON
body like `{"error": "rate_limited", "tier": "platform_quota:instagram",
"limit": 25, "remaining": 0, "retry_after": 4271}`. Honour `tier`: a
`platform_quota:*` 429 means "try a different account" or "wait until
tomorrow"; a `per_key_writes` 429 means "slow down."

### Error envelope

All 4xx/5xx (HTTP and the equivalent inside JSON-RPC) follow the same
shape so you can parse `error` to branch:

```json
{
  "error": "rate_limited|forbidden|not_found|unprocessable_entity|conflict|bad_request",
  "detail": "human-readable explanation",
  "tier": "...", "limit": 0, "remaining": 0, "retry_after": 0
}
```

For MCP JSON-RPC errors, the codes follow the standard:
`-32700` parse error, `-32600` invalid request, `-32601` method not found,
`-32602` invalid params (the most common — tool argument validation lives
here), `-32603` internal error.

## Reference

The detailed docs are in `reference/`:

- `reference/overview.md` — visual map of orgs, workspaces, accounts, keys
- `reference/authentication.md` — bearer token format and HTTPS guard
- `reference/rest-api.md` — every endpoint, every field, every status code
- `reference/mcp-tools.md` — every tool, its `inputSchema`, and example
  invocations
- `reference/errors.md` — every error you can get and how to recover
- `reference/rate-limits.md` — the six-tier limit system in full
- `reference/workflows.md` — recipes (draft → review → schedule, schedule
  → cancel, schedule → reschedule, multi-account fan-out)

## MCP server configuration

If the user wants to wire Brightbean Studio into Claude Desktop, Cursor,
or any MCP-aware client, point them at the snippets in
`mcp/claude_desktop_config.json` and `mcp/cursor_config.json`. The
streamable-HTTP transport lives at `https://studio.brightbean.xyz/api/v1/mcp/`
(or the user's own host if self-hosted) and authenticates with the same
`bb_studio_...` bearer token.
