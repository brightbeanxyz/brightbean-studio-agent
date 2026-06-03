---
name: brightbean-studio
description: |
  Draft, schedule, update, cancel, AND inspect the performance of social-media
  posts via the Brightbean Studio Agent API. Trigger when the user wants to
  publish or schedule a post to LinkedIn (personal or company), Facebook,
  Instagram, TikTok, YouTube, Pinterest, Threads, Mastodon, Bluesky, or Google
  Business through a Brightbean Studio workspace, to inspect or cancel posts
  already scheduled there, OR to read channel-level and per-post analytics
  (views, reach, engagement rate, follower growth, daily sparklines). Works
  with both Streamable HTTP MCP (preferred when available) and a REST API at
  `/api/v1/...`. Requires a `bb_studio_...` bearer token issued from the
  Brightbean Studio org settings.
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
- Look up how a recent post performed, or how a channel is trending —
  views, reach, engagement rate, follower growth, daily sparklines

Analytics are **read-only and additive** — they let the agent see results,
but they don't post, cancel, or mutate anything. To act on what the agent
observes, use the write tools (`schedule_post`, `cancel_post`, etc.) which
keep their own permissions.

Do NOT use this skill when:

- The user only wants help writing copy (no schedule/publish involved)
- The platform isn't on the supported list above (e.g. native X/Twitter — not
  in Brightbean's `PlatformCredential.Platform` choices today)
- The user wants comment moderation or inbox replies — not in scope for v1

## Installation

The fastest path for Claude Code, Codex, Cursor, OpenClaw, and other
agentic CLIs is the [`skills`](https://www.npmjs.com/package/skills)
installer — it auto-detects the runtime and drops this skill into the
right directory:

```bash
npx skills@^1 add brightbeanxyz/brightbean-studio-agent
```

`@^1` pins to the v1.x line of the `skills` package; the installer is
moving quickly, and pinning the major keeps the install reproducible.

After install, the agent still needs a Brightbean bearer token and (for
runtimes that speak MCP) an MCP server entry pointed at
`https://studio.brightbean.xyz/api/v1/mcp/`. See **Quick start → Step 1**
for the token; the [`mcp/`](mcp/) directory has Claude Desktop and Cursor
config snippets.

**Manual install** if you'd rather not use `npx`: clone this repo into
the runtime's skill directory, e.g.
`git clone https://github.com/brightbeanxyz/brightbean-studio-agent ~/.claude/skills/brightbean-studio`.

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
   - **`view_analytics`** — **read-only** access to channel and per-post
     analytics. Does *not* let the agent cancel, re-schedule, or modify
     anything. Pair with `create_posts` if you want the agent to learn
     from past performance when drafting the next post; issue a
     `view_analytics`-only key when you want the agent to *observe* but
     not *act*.
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

### Step 4 — Observe and learn (optional)

Once a post is published, you can read its performance with the analytics
tools. The two questions the agent will typically want answered:

- **"How is this channel doing?"** — MCP: `get_account_analytics` /
  REST: `GET /api/v1/analytics/accounts/{account_id}?days=7|30|90`. Returns
  hero KPIs (views, reach, etc.) + engagement rate + follower growth, each
  as a `DerivedMetric` with `value`, `delta` (% vs. the prior window),
  `series` (daily sparkline), and `kind`.
- **"How did that post perform?"** — MCP: `get_post_analytics` /
  REST: `GET /api/v1/analytics/posts/{post_id}`. Returns per-platform
  metric tiles (latest value + daily sparkline since publish) for the
  same `post_id` `schedule_post` / `create_draft` returned.

Both surfaces include `captured_at` and `next_sync_eta` — use
`next_sync_eta` to decide when to poll again so you don't refresh faster
than the backend syncs. See the **Analytics polling cadence** subsection
under [Critical contracts](#critical-contracts) below for the rules.

The analytics surface is **observation only**: it does not unlock
mutating tools. If the agent decides (with the user) that a scheduled
post should be cancelled or re-scheduled based on what the analytics
show, the action still goes through `cancel_post` / `schedule_post`
(which need `create_posts` ± `publish_directly`).

## Endpoint reference

Every endpoint and tool the API exposes. Inlined here so the agent
doesn't have to chase `reference/*.md` for the wire shape — that
deeper docs in `reference/` are for when something goes wrong (full
error taxonomy, rate-limit math, security boundary deep-dive).

### Shared response shapes

The same envelopes show up across many endpoints. Defined once here,
referenced by name below.

**`AccountSummary`**
```json
{
  "id":                "uuid",
  "platform":          "linkedin_personal",
  "account_name":      "Jan on LinkedIn",
  "account_handle":    "",
  "connection_status": "connected"
}
```
`platform` is one of: `linkedin_personal`, `linkedin_company`,
`facebook`, `instagram`, `instagram_login`, `tiktok`, `youtube`,
`pinterest`, `threads`, `mastodon`, `bluesky`, `google_business`.
`connection_status` is one of: `connected`, `token_expiring`,
`disconnected`, `error`.

**`PlatformPostSummary`** (per-account child of a Post)
```json
{
  "id":                "uuid",
  "social_account_id": "uuid",
  "platform":          "linkedin_personal",
  "status":            "draft|pending_review|approved|scheduled|publishing|published|failed",
  "scheduled_at":      "ISO 8601 | null",
  "published_at":      "ISO 8601 | null",
  "platform_post_id":  ""  // filled by the publisher after success
}
```

**`PostResponse`** (returned by every Post-touching write + read)
```json
{
  "id":             "uuid",
  "workspace_id":   "uuid",
  "title":          "",
  "caption":        "string",
  "first_comment":  "",
  "scheduled_at":   "ISO 8601 | null",
  "published_at":   "ISO 8601 | null",
  "status":         "draft|scheduled|publishing|published|partially_published|failed",
  "platform_posts": [PlatformPostSummary, ...],
  "created_at":     "ISO 8601",
  "updated_at":     "ISO 8601"
}
```
Top-level `status` is the DERIVED aggregate over children. Drive
transitions from individual `platform_posts[]` rows.

**`ErrorResponse`** (every 4xx/5xx)
```json
{
  "error":       "rate_limited|forbidden|not_found|unprocessable_entity|conflict|bad_request|unauthorized",
  "detail":      "Human-readable explanation",
  "tier":        "...",   // 429 only
  "limit":       0,       // 429 only
  "remaining":   0,       // 429 only
  "retry_after": 0        // 429 only — seconds
}
```
On 429s the matching `Retry-After` HTTP header is also set.

**`DerivedMetric`** (every analytics number — hero KPI, engagement, growth, tile)
```json
{
  "key":    "views",                  // metric identifier
  "label":  "Views",                  // human label
  "kind":   "count",                  // "count" | "percent" | "minutes"
  "value":  32411.33,                 // aggregate over the window (sum for counts, avg for rates)
  "delta":  -8.8,                     // % change vs. the prior equal-length window
  "series": [970.1, 1427.6, /*…*/]    // daily values for the current window
}
```

**`EngagementCard`** (account analytics only; `null` on platforms without a denom)
```json
{
  "rate":  DerivedMetric,           // engagement rate %
  "parts": [DerivedMetric, ...]     // its numerator components (likes, comments, shares, …)
}
```

**`AccountAnalyticsResponse`** (return shape of `GET /analytics/accounts/{id}`)
```json
{
  "account_id":           "uuid",
  "platform":             "youtube",
  "account_name":         "PinkLion",
  "connection_status":    "connected|token_expiring|disconnected|error",
  "days":                 30,                // window size used (one of 7, 30, 90)
  "analytics_available":  true,
  "unavailable_reason":   null,              // string when analytics_available=false
  "hero_metrics":         [DerivedMetric, ...],
  "engagement":           EngagementCard | null,
  "follower_growth":      DerivedMetric | null,
  "captured_at":          "ISO 8601 | null",
  "next_sync_eta":        "ISO 8601 | null"  // when the backend next refreshes
}
```

**`PlatformPostAnalyticsResponse`** (one entry per platform child of a post)
```json
{
  "platform_post_id":     "uuid",
  "social_account_id":    "uuid",
  "platform":             "linkedin_company",
  "status":               "published|draft|scheduled|…",
  "published_at":         "ISO 8601 | null",
  "analytics_available":  true,
  "unavailable_reason":   null,
  "metric_tiles":         [
    {
      "key":        "impressions",
      "label":      "Impressions",
      "kind":       "count",
      "value":      2418,
      "series":     [/* daily values since publish */],
      "is_primary": true
    }
  ],
  "captured_at":          "ISO 8601 | null",
  "next_sync_eta":        "ISO 8601 | null"
}
```

**`PostAnalyticsResponse`** (return shape of `GET /analytics/posts/{id}`)
```json
{
  "post_id":        "uuid",
  "workspace_id":   "uuid",
  "title":          "",
  "caption":        "string",
  "platform_posts": [PlatformPostAnalyticsResponse, ...]
}
```

Drafts and scheduled posts return `analytics_available: true` with
`metric_tiles: []` and `captured_at: null` — a stable empty envelope so
polling loops have something to chew on before publish.

Platforms in the no-analytics set (`linkedin_personal`, `bluesky`,
`mastodon`) return `analytics_available: false` with a non-null
`unavailable_reason`. Don't retry these — the answer won't change.

---

### REST endpoints

All under `/api/v1/`. Every request needs
`Authorization: Bearer bb_studio_...`. HTTPS required in prod.

#### `GET /me/`

**Purpose:** Echo the key's scope. Use as the first call in a new
session to validate the token, learn the workspace, and discover
which accounts the key may target.

**Request body:** none

**Response 200:**
```json
{
  "api_key_id":           "uuid",
  "workspace_id":         "uuid",
  "workspace_name":       "string",
  "organization_id":      "uuid",
  "permissions":          ["create_posts", "publish_directly", ...],
  "allowlisted_accounts": [AccountSummary, ...]
}
```

**Errors:** 401 (bad / missing bearer, IP-throttled).

---

#### `GET /accounts/`

**Purpose:** List the connected accounts this key may act on. Same
content as `/me/`'s `allowlisted_accounts`, returned as a top-level
list — useful when you only need the accounts.

**Request body:** none

**Response 200:**
```json
{ "accounts": [AccountSummary, ...] }
```

**Errors:** 401.

---

#### `POST /posts/`

**Purpose:** Create a draft OR a scheduled post in one call.

**Request body:**

| Parameter           | Type                       | Req?                                | Notes |
|---------------------|----------------------------|-------------------------------------|-------|
| `social_account_id` | UUID                       | yes                                 | Must be in the key's allowlist. Determines the target platform implicitly. |
| `caption`           | string ≤ 10 000            | yes                                 | Per-platform character limits apply (see table above). |
| `action`            | `"draft"` \| `"schedule"`  | no (default `"draft"`)              | |
| `scheduled_at`      | ISO 8601 UTC               | required when `action="schedule"`   | E.g. `"2026-06-01T14:00:00Z"`. The publisher polls ~every 15s. Past timestamps fire on the next tick. |
| `title`             | string ≤ 255               | no                                  | Used by platforms that support a title (YouTube, LinkedIn articles); ignored elsewhere. |
| `first_comment`     | string ≤ 10 000            | no                                  | Posted as a reply right after the main post. Hashtag dump / link drop pattern. |
| `media_asset_ids`   | array of UUIDs             | no                                  | `MediaAsset` UUIDs already uploaded to the workspace's media library. Order = carousel order. |
| `idempotency_key`   | string ≤ 128               | recommended                         | Same key on retries replays the first response. Also accepted as the `Idempotency-Key` HTTP header. Body field wins when both are present. |

**Permission required:**
- `action="draft"` → `create_posts`
- `action="schedule"` → `create_posts` AND `publish_directly`

**Response 201:** `PostResponse`

**Errors:**
- **403** `forbidden` — missing permission OR `social_account_id` outside allowlist
- **422** `unprocessable_entity` — missing `scheduled_at` on schedule, disconnected account, workspace approval gate, idempotency-key body mismatch, missing media asset
- **409** `conflict` — a concurrent peer holds the same `idempotency_key` in flight
- **429** `rate_limited` — per-key / per-workspace / per-platform-quota — see [`reference/rate-limits.md`](reference/rate-limits.md)

**Worked example:**
```json
POST /api/v1/posts/
Authorization: Bearer bb_studio_...
Idempotency-Key: agent-launch-2026-06-01
Content-Type: application/json

{
  "social_account_id": "46332b33-21c9-4534-987f-ac1fb2daa906",
  "caption": "Launching today!",
  "action": "schedule",
  "scheduled_at": "2026-06-01T14:00:00Z",
  "first_comment": "Read the blog: https://example.com/launch",
  "media_asset_ids": ["a1b2c3d4-..."]
}
```

---

#### `GET /posts/{post_id}`

**Purpose:** Read a post + per-platform child state.

**Request body:** none

**Response 200:** `PostResponse`

**Errors:**
- **404** `not_found` — doesn't exist OR lives in another workspace OR has a child outside the key's allowlist. **All three are deliberately indistinguishable** so partial-scope keys can't enumerate foreign IDs.

---

#### `PATCH /posts/{post_id}`

**Purpose:** Update editable fields on a draft, or re-time a
scheduled post.

**Request body** (all fields optional):

| Parameter         | Type             | Notes |
|-------------------|------------------|-------|
| `caption`         | string ≤ 10 000  | Omit to leave unchanged. |
| `title`           | string ≤ 255     | |
| `first_comment`   | string ≤ 10 000  | |
| `media_asset_ids` | array of UUIDs   | Sending this **replaces** the whole attachment set (not append). |
| `scheduled_at`    | ISO 8601 UTC     | Re-times every currently-scheduled child. Drafts unaffected. |

**Permission required:** `create_posts`.

**Response 200:** `PostResponse`

**Errors:**
- **409** `conflict` — post not in an editable status (e.g. `published`)
- **404** — same opacity rule as GET
- **422** — bad media UUID; the entire PATCH rolls back atomically

---

#### `POST /posts/{post_id}/schedule`

**Purpose:** Promote every draft child of a Post to `scheduled` at
the same `scheduled_at`.

**Request body:**

| Parameter      | Type         | Req? |
|----------------|--------------|------|
| `scheduled_at` | ISO 8601 UTC | yes  |

**Permission required:** `create_posts` AND `publish_directly`.

**Response 200:** `PostResponse`

**Errors:**
- **409** — no draft children to schedule
- **422** — workspace requires approval, state-machine conflict
- **429** — per-account platform quota exceeded
- **404** — same opacity rule

---

#### `POST /posts/{post_id}/cancel`

**Purpose:** Transition every scheduled child back to `draft`.
`Post.scheduled_at` is cleared.

**Request body:** none (empty JSON object is also fine)

**Permission required:** `create_posts`.

**Response 200:** `PostResponse`

**Errors:**
- **409** — no scheduled children to cancel

---

#### `GET /analytics/accounts/{account_id}`

**Purpose:** Read channel-wide analytics over a rolling 7 / 30 / 90-day
window — hero KPIs, engagement card (where the platform exposes a denom),
follower growth, plus freshness signals so the agent knows when to poll
again.

**Request body:** none

**Query parameters:**

| Parameter | Type    | Req? | Notes |
|-----------|---------|------|-------|
| `days`    | integer | no (default `30`) | One of 7 / 30 / 90. Ninja enforces `7 ≤ days ≤ 90` and 422s on violation. |

**Permission required:** `view_analytics` (read-only).

**Response 200:** `AccountAnalyticsResponse`

**Errors:**
- **403** `forbidden` — missing `view_analytics`, or `account_id` outside the key's allowlist
- **422** `unprocessable_entity` — `days` out of range
- **401** — bad / missing bearer

**Worked example:**
```
GET /api/v1/analytics/accounts/40fc50eb-edb9-4c70-a217-e58ed9e4d93c?days=30
Authorization: Bearer bb_studio_...
```

---

#### `GET /analytics/posts/{post_id}`

**Purpose:** Read a post's analytics, broken down per platform. Pass the
parent `Post.id` you got from `schedule_post` / `create_draft`; the
response carries an entry per `PlatformPost` child with its own
`metric_tiles`, `captured_at`, and `next_sync_eta`.

**Request body:** none

**Permission required:** `view_analytics` (read-only).

**Response 200:** `PostAnalyticsResponse`

**Errors:**
- **403** `forbidden` — missing `view_analytics`
- **404** `not_found` — same opacity rule as `GET /posts/{id}` (doesn't
  exist OR lives in another workspace OR has a child outside the
  allowlist; all three are indistinguishable)

**Worked example:**
```
GET /api/v1/analytics/posts/73ffb281-0eba-4d0e-a06e-fdc6bcbd97e7
Authorization: Bearer bb_studio_...
```

Drafts and scheduled posts return an empty-but-valid envelope (each
child has `metric_tiles: []`, `captured_at: null`); platforms without
analytics (LinkedIn Personal, Bluesky, Mastodon) return
`analytics_available: false, unavailable_reason: "..."` per child.

---

### MCP tools

Mounted at `POST /api/v1/mcp/`. Same `Authorization: Bearer` header
as REST. Wire shape: JSON-RPC 2.0. Every tool call has the envelope:

```json
{"jsonrpc": "2.0", "id": <any>, "method": "tools/call",
 "params": {"name": "<tool>", "arguments": {...}}}
```

Tool results come back wrapped in `content`:

```json
{"jsonrpc": "2.0", "id": <any>, "result": {
  "content": [{"type": "text", "text": "<JSON-stringified payload>"}],
  "isError": false
}}
```

The `text` field is a JSON-stringified version of the payload — `JSON.parse` it.

The 8 tools mirror the REST surface 1:1.

#### `list_accounts`

**Purpose:** List the connected accounts this key may act on.
Equivalent to REST `GET /accounts/`.

**Arguments:** none (`{}`)

**Returns:** text content wrapping `{"accounts": [AccountSummary, ...]}`

---

#### `create_draft`

**Purpose:** Create a draft post against a connected account.
Equivalent to REST `POST /posts/ {action: "draft"}`.

**Arguments:**

| Argument            | Type            | Req? | Notes |
|---------------------|-----------------|------|-------|
| `social_account_id` | UUID            | yes  | Must be in allowlist. |
| `caption`           | string ≤ 10 000 | yes  | |
| `title`             | string ≤ 255    | no   | |
| `first_comment`     | string ≤ 10 000 | no   | |
| `media_asset_ids`   | array of UUIDs  | no   | |

**Permission required:** `create_posts`.

**Returns:** text content wrapping `PostResponse` (with `status: "draft"`).

**Errors:** JSON-RPC `-32602 INVALID_PARAMS` on schema-validation
failure (server enforces `inputSchema`), permission denied, allowlist
miss, or disconnected account.

---

#### `schedule_post`

**Purpose:** Create AND schedule a post in one call. Equivalent to
REST `POST /posts/ {action: "schedule"}`.

**Arguments:**

| Argument            | Type            | Req? | Notes |
|---------------------|-----------------|------|-------|
| `social_account_id` | UUID            | yes  | |
| `caption`           | string ≤ 10 000 | yes  | |
| `scheduled_at`      | ISO 8601 UTC    | yes  | E.g. `"2026-06-01T14:00:00Z"`. |
| `title`             | string ≤ 255    | no   | |
| `first_comment`     | string ≤ 10 000 | no   | |
| `media_asset_ids`   | array of UUIDs  | no   | |

**Permission required:** `create_posts` AND `publish_directly`.

**Returns:** text content wrapping `PostResponse` (with `status: "scheduled"`).

> **One-shot vs two-step:** `schedule_post` always creates a NEW post
> in `scheduled` state. To promote an EXISTING draft to scheduled
> (two-step "create_draft now, schedule later"), use the
> [`schedule_draft`](#schedule_draft) tool below.

---

#### `schedule_draft`

**Purpose:** Promote every draft child of an EXISTING post to
`scheduled`. Equivalent to REST `POST /posts/{post_id}/schedule`.

**Arguments:**

| Argument       | Type         | Req? | Notes |
|----------------|--------------|------|-------|
| `post_id`      | UUID         | yes  | The draft post to promote. |
| `scheduled_at` | ISO 8601 UTC | yes  | When the publisher should fire. |

**Permission required:** `create_posts` AND `publish_directly`.

**Returns:** text content wrapping `PostResponse` (with children now in `scheduled`).

**Errors:**
- `-32602 INVALID_PARAMS` `"No draft platform posts to schedule"` — post is already scheduled / cancelled / published
- `-32602 INVALID_PARAMS` with quota message — per-platform 24h cap
- `-32602 INVALID_PARAMS` `"Post not found"` — same opacity rule as `get_post`

Per-account 24h platform quota is checked before any mutation; if
over, the call fails atomically with no partial commit. The per-child
transition loop is wrapped in `transaction.atomic()`, mirroring REST.

---

#### `get_post`

**Purpose:** Read a post by ID. Equivalent to REST `GET /posts/{id}`.

**Arguments:**

| Argument  | Type | Req? |
|-----------|------|------|
| `post_id` | UUID | yes  |

**Returns:** text content wrapping `PostResponse`.

**Errors:** `-32602 INVALID_PARAMS` with `"Post not found"` —
indistinguishable from "exists but outside allowlist" or "exists in
another workspace" (same opacity rule as REST).

---

#### `cancel_post`

**Purpose:** Transition every scheduled child back to draft. Equivalent
to REST `POST /posts/{id}/cancel`.

**Arguments:**

| Argument  | Type | Req? |
|-----------|------|------|
| `post_id` | UUID | yes  |

**Permission required:** `create_posts`.

**Returns:** text content wrapping `PostResponse` (with children now
in `draft`).

**Errors:** `-32602 INVALID_PARAMS` with `"No scheduled platform posts to cancel"`.

---

#### `get_account_analytics`

**Purpose:** Read a channel's analytics over a rolling 7 / 30 / 90-day
window. Equivalent to REST `GET /analytics/accounts/{account_id}`.

**Arguments:**

| Argument     | Type    | Req? | Notes |
|--------------|---------|------|-------|
| `account_id` | UUID    | yes  | Must be in the key's allowlist. |
| `days`       | integer | no (default `30`) | One of 7 / 30 / 90. Validated server-side via JSON Schema; out-of-range returns `-32602 INVALID_PARAMS`. |

**Permission required:** `view_analytics` (read-only).

**Returns:** text content wrapping `AccountAnalyticsResponse`.

**Errors:** `-32602 INVALID_PARAMS` on schema-validation failure
(`days` outside 7-90), missing `view_analytics`, or `account_id` outside
the allowlist.

---

#### `get_post_analytics`

**Purpose:** Read a post's analytics, broken down per platform.
Equivalent to REST `GET /analytics/posts/{post_id}`. Use in a polling
loop after `schedule_post` / `create_draft` to see how a post is
performing — drafts and scheduled posts return an empty `metric_tiles`
array (not an error), so the loop is safe to call from day zero.

**Arguments:**

| Argument  | Type | Req? | Notes |
|-----------|------|------|-------|
| `post_id` | UUID | yes  | The parent `Post.id` returned by `schedule_post` / `create_draft`. |

**Permission required:** `view_analytics` (read-only).

**Returns:** text content wrapping `PostAnalyticsResponse`.

**Errors:** `-32602 INVALID_PARAMS` with `"Post not found"` —
indistinguishable from "exists but outside allowlist" or "exists in
another workspace" (same opacity rule as `get_post`); also
`"Permission denied: view_analytics"` when the key lacks the permission.

---

### MCP protocol methods (built-in)

The MCP runtime handles these for most clients — listed for
completeness so an agent rolling its own JSON-RPC over HTTP knows the
full surface.

| Method                        | Purpose                                          | Params                                  | Returns                                              |
|-------------------------------|--------------------------------------------------|-----------------------------------------|------------------------------------------------------|
| `initialize`                  | Handshake — declare protocol version + capabilities | `{protocolVersion, capabilities}`     | `{protocolVersion, capabilities, serverInfo}`        |
| `notifications/initialized`   | Client signals it's ready (notification, no reply)| none                                    | — (server returns HTTP 202)                          |
| `ping`                        | Liveness probe                                   | none                                    | `{}`                                                 |
| `tools/list`                  | Discover the tools above                         | none                                    | `{tools: [{name, description, inputSchema}, ...]}`    |
| `tools/call`                  | Invoke one of the 6 tools above                  | `{name: "<tool>", arguments: {...}}`    | `{content: [{type: "text", text: "<json>"}], isError: false}` |

Batched JSON-RPC is supported: send an array, get an array back.
Each message in the batch costs one rate-limit token (same accounting
as N separate POSTs).

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

### Analytics polling cadence

When the agent polls analytics in a loop, follow the freshness fields the
response carries — don't poll on a fixed wall clock and don't refresh
faster than the backend syncs.

- **`captured_at`** is the most recent snapshot timestamp the backend has
  for this account/post. `null` means the sync hasn't run yet (just-
  connected account, or a post still inside its first sync window) —
  treat it as "no data, check back soon".
- **`next_sync_eta`** is the backend's estimated next refresh. Wait at
  least until that timestamp before polling again. Polling earlier
  returns the same `captured_at` and burns rate-limit budget.
- The per-post sync ladder (mirrored from
  `apps/analytics/tasks.post_sync_interval`):

  | Post age            | Refresh interval |
  |---------------------|------------------|
  | < 24 h              | hourly           |
  | 1 – 7 days          | every 6 h        |
  | 7 – 30 days         | daily            |
  | 30 – 90 days        | weekly           |
  | > 90 days           | sync has stopped — `next_sync_eta: null` |

- Account-level analytics refresh once per day; for a just-connected
  account both fields are `null` and the API hints back with
  `next_sync_eta ≈ now + 5 min`.
- **`analytics_available: false` + `unavailable_reason: "..."`** means
  the platform itself doesn't expose aggregate analytics
  (`linkedin_personal`, `bluesky`, `mastodon`) **or** an admin has
  disabled the platform in `AnalyticsPlatformConfig`. Don't retry — the
  answer won't change without an operator action.
- The analytics surface is **read-only**. `view_analytics` does not
  unlock `cancel_post` / `schedule_post` / `create_draft`. If the agent
  decides (with the user) to act on what it observed, the mutation
  flows through the existing write tools and their own permissions.

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
  → cancel, schedule → reschedule, multi-account fan-out, schedule → poll
  for performance, channel-health check, learn from last N posts)
- `reference/analytics.md` — metrics catalog per platform, engagement-rate
  formula, freshness model, sync cadence ladder, unavailable platforms,
  admin-toggle gate

## MCP server configuration

If the user wants to wire Brightbean Studio into Claude Desktop, Cursor,
or any MCP-aware client, point them at the snippets in
`mcp/claude_desktop_config.json` and `mcp/cursor_config.json`. The
streamable-HTTP transport lives at `https://studio.brightbean.xyz/api/v1/mcp/`
(or the user's own host if self-hosted) and authenticates with the same
`bb_studio_...` bearer token.
