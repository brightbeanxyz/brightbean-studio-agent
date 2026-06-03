# REST API reference

Base URL: `https://studio.brightbean.xyz/api/v1/` (or your own host if you
self-host Brightbean Studio).

Auth: `Authorization: Bearer bb_studio_<random>_<lookup>` on every request.

## `GET /me/`

Echo what the bearer is scoped to.

Response 200:
```json
{
  "api_key_id": "uuid",
  "workspace_id": "uuid",
  "workspace_name": "string",
  "organization_id": "uuid",
  "permissions": ["create_posts", "publish_directly", ...],
  "allowlisted_accounts": [
    {
      "id": "uuid",
      "platform": "linkedin_personal",
      "account_name": "Acme on LinkedIn",
      "account_handle": "",
      "connection_status": "connected"
    }
  ]
}
```

Use this as the first call in a new session to validate the token and
learn which accounts the key may target.

## `GET /accounts/`

Same content as `/me/`'s `allowlisted_accounts`, returned as a top-level
list.

Response 200:
```json
{ "accounts": [ { "id": "uuid", "platform": "...", ... } ] }
```

## `POST /posts/`

Create a draft or a scheduled post.

Body:
```json
{
  "social_account_id": "uuid",        // REQUIRED, must be in the key's allowlist
  "caption": "string",                // REQUIRED, max 10000
  "title": "string",                  // optional, max 255
  "first_comment": "string",          // optional, max 10000 — posted as a comment after the main post
  "media_asset_ids": ["uuid"],        // optional, MediaAsset UUIDs already uploaded
  "action": "draft" | "schedule",     // default "draft"
  "scheduled_at": "2026-06-01T14:00:00Z",  // REQUIRED when action="schedule"
  "idempotency_key": "string"         // optional, recommended for retry-safety
}
```

Permission required:
- `action: "draft"` → `create_posts`
- `action: "schedule"` → `create_posts` AND `publish_directly`

Responses:
- **201** — created (success). Body: see [PostResponse](#postresponse).
- **403** `forbidden` — missing permission OR `social_account_id` outside
  allowlist.
- **422** `unprocessable_entity` —
  - `scheduled_at is required when action='schedule'`
  - `social_account is in connection_status 'disconnected'` — reconnect
    needed
  - `Workspace requires approval before scheduling` — route through approval
  - `idempotency_key reused with different body`
  - `Media asset(s) not found in workspace: [...]`
- **429** `rate_limited` — see [rate-limits.md](rate-limits.md).
- **409** `conflict` — a concurrent peer with the same `idempotency_key`
  is still in flight. Retry in a moment.

## `GET /posts/{post_id}`

Fetch a post + per-platform state.

Responses:
- **200** — see [PostResponse](#postresponse).
- **404** `not_found` — doesn't exist, lives in another workspace, or has a
  child outside the key's allowlist. **The three cases are deliberately
  indistinguishable**, so a partial-scope key can't enumerate foreign IDs.

## `PATCH /posts/{post_id}`

Update a draft or re-time a scheduled post.

Body (all fields optional):
```json
{
  "caption": "string",
  "title": "string",
  "first_comment": "string",
  "media_asset_ids": ["uuid"],            // replaces the whole attachment set
  "scheduled_at": "2026-06-01T14:00:00Z"  // re-times every currently-scheduled child
}
```

Validation runs before any DB write — a bad media UUID rejects the whole
PATCH atomically (no partial schedule re-time).

Responses:
- **200** — see [PostResponse](#postresponse).
- **409** `conflict` — the post is not in an editable status (e.g.
  `published`).
- **404** — same opacity rule as GET.

## `POST /posts/{post_id}/schedule`

Transition every draft child to `scheduled` at `scheduled_at`.

Body:
```json
{ "scheduled_at": "2026-06-01T14:00:00Z" }
```

Permission required: `create_posts` AND `publish_directly`.

Responses:
- **200** — see [PostResponse](#postresponse).
- **409** — no draft children to schedule.
- **422** — per-platform quota exceeded (rare on this path; mostly fires
  from the `POST /posts/` path).
- **404** — same opacity rule.

## `POST /posts/{post_id}/cancel`

Transition every scheduled child back to `draft`. Useful for "the user
changed their mind" or "I scheduled the wrong time."

No body needed.

Responses:
- **200** — see [PostResponse](#postresponse).
- **409** — no scheduled children to cancel.

## Analytics endpoints

Read-only. Both endpoints require the `view_analytics` permission on the
key. Allowlist rules match the corresponding post endpoints: a key only
sees analytics for accounts it could already post to.

### `GET /analytics/accounts/{account_id}`

Channel-wide analytics over a rolling 7 / 30 / 90-day window — hero KPIs,
engagement card (where the platform exposes a denom), follower growth,
plus freshness signals.

Query parameters:

| Parameter | Type    | Default | Constraint |
|-----------|---------|---------|------------|
| `days`    | integer | `30`    | `7 ≤ days ≤ 90` (Ninja Query, 422 on violation) |

Permission required: `view_analytics`.

Responses:
- **200** — see [`AccountAnalyticsResponse`](#accountanalyticsresponse).
- **403** `forbidden` — missing `view_analytics`, or `account_id`
  outside the key's allowlist.
- **422** `unprocessable_entity` — `days` out of range.

Examples:
```
GET /api/v1/analytics/accounts/40fc50eb-edb9-4c70-a217-e58ed9e4d93c?days=30
GET /api/v1/analytics/accounts/40fc50eb-edb9-4c70-a217-e58ed9e4d93c?days=7
```

### `GET /analytics/posts/{post_id}`

Per-post analytics, with one envelope per `PlatformPost` child. The
`post_id` argument is the parent `Post.id` (the same ID `POST /posts/`
returned). For a single-account key the response carries one child; for
multi-platform posts there is one entry per platform with its own
`analytics_available` flag.

Permission required: `view_analytics`.

Responses:
- **200** — see [`PostAnalyticsResponse`](#postanalyticsresponse).
- **403** `forbidden` — missing `view_analytics`.
- **404** `not_found` — same opacity rule as `GET /posts/{post_id}`
  (doesn't exist, lives in another workspace, or has a child outside the
  allowlist — all three are indistinguishable).

Drafts and scheduled posts return `metric_tiles: []` and
`captured_at: null` for each child (the envelope is valid, just empty,
so polling loops don't have to special-case pre-publish state).

Examples:
```
GET /api/v1/analytics/posts/73ffb281-0eba-4d0e-a06e-fdc6bcbd97e7
```

### `AccountAnalyticsResponse`

```json
{
  "account_id":           "uuid",
  "platform":             "youtube",
  "account_name":         "PinkLion",
  "connection_status":    "connected",
  "days":                 30,
  "analytics_available":  true,
  "unavailable_reason":   null,
  "hero_metrics":         [DerivedMetric, ...],
  "engagement":           {
    "rate":  DerivedMetric,
    "parts": [DerivedMetric, ...]
  } | null,
  "follower_growth":      DerivedMetric | null,
  "captured_at":          "2026-06-02T08:43:22Z" | null,
  "next_sync_eta":        "2026-06-03T08:43:22Z" | null
}
```

### `PostAnalyticsResponse`

```json
{
  "post_id":        "uuid",
  "workspace_id":   "uuid",
  "title":          "",
  "caption":        "string",
  "platform_posts": [
    {
      "platform_post_id":    "uuid",
      "social_account_id":   "uuid",
      "platform":            "linkedin_company",
      "status":              "published",
      "published_at":        "2026-05-30T08:43:22Z" | null,
      "analytics_available": true,
      "unavailable_reason":  null,
      "metric_tiles": [
        {
          "key":        "impressions",
          "label":      "Impressions",
          "kind":       "count",
          "value":      2418,
          "series":     [/* daily values since publish */],
          "is_primary": true
        }
      ],
      "captured_at":  "2026-06-02T08:43:22Z" | null,
      "next_sync_eta": "2026-06-02T14:43:22Z" | null
    }
  ]
}
```

### `DerivedMetric`

```json
{
  "key":    "views",
  "label":  "Views",
  "kind":   "count",       // "count" | "percent" | "minutes"
  "value":  32411.33,      // aggregate over the window (sum for counts, avg for rates)
  "delta":  -8.8,          // % change vs. the prior equal-length window
  "series": [970.1, /* … */]
}
```

### Polling cadence

Use `next_sync_eta` to decide when to poll again. The per-post ladder:

| Post age            | Refresh interval |
|---------------------|------------------|
| < 24 h              | hourly           |
| 1 – 7 days          | every 6 h        |
| 7 – 30 days         | daily            |
| 30 – 90 days        | weekly           |
| > 90 days           | sync has stopped — `next_sync_eta: null` |

Account-level analytics refresh once per day. A just-connected account
has `captured_at: null` and `next_sync_eta ≈ now + 5 min`.

### Unavailable platforms

`linkedin_personal`, `bluesky`, and `mastodon` don't expose aggregate
analytics; their responses set `analytics_available: false` and
`unavailable_reason: "<message>"`. An admin can also disable a platform
globally in `AnalyticsPlatformConfig`; that produces the same shape
with `"Analytics is not currently enabled for this platform."`.

## `PostResponse`

The shape every post-returning endpoint emits:

```json
{
  "id": "uuid",
  "workspace_id": "uuid",
  "title": "",
  "caption": "Hello from agents.",
  "first_comment": "",
  "scheduled_at": "2026-06-01T14:00:00Z" | null,
  "published_at": "2026-06-01T14:00:00Z" | null,
  "status": "draft" | "scheduled" | "publishing" | "published" | "failed" | ...,
  "platform_posts": [
    {
      "id": "uuid",
      "social_account_id": "uuid",
      "platform": "linkedin_personal",
      "status": "draft" | ...,
      "scheduled_at": "..." | null,
      "published_at": "..." | null,
      "platform_post_id": ""  // filled by the publisher after success
    }
  ],
  "created_at": "iso-8601",
  "updated_at": "iso-8601"
}
```

The top-level `status` is **derived** from the children: if every child
is `published`, the post is `published`; if some are still scheduled, the
post is `partially_published` or `scheduled`, etc. Don't rely on the
top-level `status` to mutate state — drive transitions from individual
`platform_posts`.

## OpenAPI

The live spec is at `GET /api/v1/openapi.json` and a Swagger UI at
`GET /api/v1/docs`. A snapshot of the spec lives at `docs/openapi.json`
in this repo so agents can answer "what's the exact shape of X" without
hitting the server.
