# Analytics reference

Everything the agent needs to interpret the channel and per-post
analytics surfaces (`GET /analytics/accounts/{id}`,
`GET /analytics/posts/{id}`, and the matching `get_account_analytics` /
`get_post_analytics` MCP tools).

This page is the deep dive: which metrics each platform reports, how
the engagement rate is computed, what the freshness fields mean, and
the per-post sync cadence so the agent polls at the right interval.

## Metrics catalog

Mirrors `apps/analytics/metrics.PLATFORM_METRICS` in the studio repo.
Each platform reports a subset of the catalog below; missing metrics
simply don't appear in `hero_metrics` / `metric_tiles`.

| Metric          | Kind     | Label              | What it means                                       |
|-----------------|----------|--------------------|-----------------------------------------------------|
| `impressions`   | count    | Impressions        | Times the post was displayed                        |
| `reach`         | count    | Reach              | Distinct accounts that saw the post                 |
| `views`         | count    | Views              | Plays (video) or views (post)                       |
| `plays`         | count    | Plays              | Video plays (platform-specific synonym for views)   |
| `likes`         | count    | Likes              | Like / favourite / heart                            |
| `reactions`     | count    | Reactions          | LinkedIn-style multi-emoji reactions                |
| `comments`      | count    | Comments           |                                                     |
| `replies`       | count    | Replies            | Threads / Mastodon synonym for comments             |
| `shares`        | count    | Shares             | Native share / repost / reblog                      |
| `reposts`       | count    | Reposts            | LinkedIn / Threads / Mastodon synonym for shares    |
| `saves`         | count    | Saves              | Bookmark / save                                     |
| `clicks`        | count    | Link clicks        |                                                     |
| `outbound`      | count    | Outbound clicks    | Pinterest off-site clicks                           |
| `profile_visits`| count    | Profile visits     |                                                     |
| `follows`       | count    | New follows        | Account-only (never on individual posts)            |
| `subscribers`   | count    | Subscribers        | YouTube account-only                                |
| `watch_time`    | minutes  | Watch time         | YouTube / TikTok per-post                           |
| `avg_view_pct`  | percent  | Avg view %         | YouTube average percentage viewed                   |
| `engagement`    | percent  | Engagement rate    | Derived; never a raw metric — see below             |

Per-platform availability:

| Platform           | Reports                                                                       |
|--------------------|-------------------------------------------------------------------------------|
| `instagram`        | reach, views, likes, comments, saves, shares, follows, engagement             |
| `instagram_login`  | reach, views, likes, comments, saves, shares, follows, engagement             |
| `facebook`         | impressions, reach, reactions, comments, shares, clicks, follows, engagement  |
| `linkedin_company` | impressions, reactions, comments, reposts, clicks, follows, engagement        |
| `linkedin_personal`| likes, comments, shares *(no analytics surface — see below)*                  |
| `youtube`          | views, watch_time, avg_view_pct, likes, comments, shares, subscribers         |
| `tiktok`           | views, likes, comments, shares, watch_time, follows, engagement               |
| `bluesky`          | likes, reposts, replies, follows *(no analytics surface — see below)*         |
| `threads`          | views, likes, replies, reposts, follows                                       |
| `pinterest`        | impressions, saves, clicks, outbound, engagement                              |
| `google_business`  | impressions, clicks                                                           |
| `mastodon`         | likes, reposts, replies *(no analytics surface — see below)*                  |

## Engagement rate formula

When the platform reports both engagement components AND a reach-like
denominator, the API computes an engagement rate and returns it as the
top-level `engagement.rate`. The formula:

```
rate = (sum of engagement parts over the window) / denom * 100
```

- **Numerator** is the sum of every value in `ENGAGEMENT_PARTS`:
  likes, reactions, comments, replies, shares, reposts, saves, clicks,
  outbound. (Each platform contributes whichever of these it reports.)
- **Denominator** is the first available of `reach, impressions, views,
  plays` (in that priority order). If none of those exist, the API
  falls back to `account.follower_count`.

The companion `engagement.parts` array surfaces each numerator
component as its own `DerivedMetric` so the agent can explain *why* the
rate moved (e.g., "comments are up 40% while reach is flat").

Platforms without any of the four denominators
(`linkedin_personal`, `bluesky`, `mastodon`) get `engagement: null` —
the studio doesn't show a rate it can't compute. Same for
`google_business` once you drop into count-only territory.

## Freshness model

Every analytics response has two timestamp fields:

- **`captured_at`** — the most recent snapshot the backend has for this
  account / post. `null` means the sync hasn't run yet (just-connected
  account, freshly published post). Treat `null` as "no data yet, check
  back soon".
- **`next_sync_eta`** — the backend's estimated next refresh. Wait at
  least until this timestamp before polling again; polling earlier
  returns the same `captured_at` and burns rate-limit budget.

For mixed-platform posts each `PlatformPost` child has its own pair —
use `max(next_sync_eta)` if you care about all children, or read them
individually if you only care about one platform.

A `next_sync_eta` of `null` on a published post means the sync has
stopped (the post is over 90 days old). The numbers won't change
further; stop polling.

## Sync cadence ladder

The per-post refresh schedule, mirrored from
`apps/analytics/tasks.post_sync_interval` in the studio repo:

| Post age            | Refresh interval | Notes                                                   |
|---------------------|------------------|---------------------------------------------------------|
| < 24 h              | every 1 h        | Hot window — most growth happens here                    |
| 1 – 7 days          | every 6 h        | Slowing                                                  |
| 7 – 30 days         | every 24 h       | Tail                                                     |
| 30 – 90 days        | every 7 days     | Cold                                                     |
| > 90 days           | none             | `next_sync_eta: null`; numbers are final                 |

Account-level analytics refresh **once per day** regardless of the
account's age. A just-connected account has `captured_at: null` and
`next_sync_eta ≈ now + 5 min` — poll back shortly to see the first
snapshot land.

## Unavailable platforms

Three platforms expose no aggregate analytics API at all:

| Platform            | Why                                                                                        |
|---------------------|--------------------------------------------------------------------------------------------|
| `linkedin_personal` | LinkedIn only exposes share statistics for Organization URNs, not personal Person URNs.    |
| `bluesky`           | The AT Protocol surfaces individual like/repost counts but no aggregate insights API.       |
| `mastodon`          | The Mastodon API doesn't expose aggregate post analytics beyond per-status favourites/reblogs. |

For these, the analytics endpoints respond with:

```json
{
  ...,
  "analytics_available": false,
  "unavailable_reason":  "<the why-message above>",
  "hero_metrics":        [],
  "engagement":          null,
  "follower_growth":     null,
  "captured_at":         null,
  "next_sync_eta":       null
}
```

Don't retry — the answer won't change without an upstream API change.

## Admin-toggle gate

A workspace admin can also disable analytics for an otherwise-supported
platform via the `AnalyticsPlatformConfig` model (e.g., while provider
app-review for the analytics scopes is still pending). When a platform
is admin-disabled, the same shape as above is returned, but with:

```json
"unavailable_reason": "Analytics is not currently enabled for this platform."
```

If the agent gets this on a platform that *should* have analytics,
suggest the user check the studio's analytics admin page — there's
nothing the agent can do to flip the switch from the API.

## Read-only boundary

The analytics surface is **observation-only**. The `view_analytics`
permission lets the agent SEE numbers but cannot mutate any state — no
cancellation, no re-scheduling, no new drafts. If the user decides
(based on what the agent shows them) that a scheduled post should be
cancelled or re-scheduled, the action still goes through `cancel_post`
or `schedule_post`, each of which requires its own permission. This is
intentional: the workspace owner can grant *observe* to an agent
without granting *act*.

See [`workflows.md`](workflows.md) recipes #10–#12 for end-to-end
patterns that respect this boundary.
