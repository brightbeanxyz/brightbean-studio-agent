# Common workflows

End-to-end patterns the agent will run into. Each is shown REST-first; the
MCP equivalents live in `examples/python/06_mcp_client.py`.

## 1. New session — what can I do?

```
1. GET /api/v1/me/
   → confirms the token, shows workspace, account list, permission set
2. (optional) GET /api/v1/accounts/
   → same content, top-level shape
```

Don't skip step 1 — agents that pick `social_account_id` from memory
without consulting `/me/` often pick a stale ID after the user re-issued
the key with a different allowlist.

## 2. Draft → user confirms → schedule

```
1. POST /api/v1/posts/
   body: { social_account_id, caption, action: "draft", idempotency_key: <fresh> }
   → 201, draft created
2. Talk to the user — iterate on copy, pick a time
3. POST /api/v1/posts/{id}/schedule
   body: { scheduled_at }
   → 200, status now "scheduled"
```

If the user changes their mind before step 3, you can simply PATCH the
draft caption — no scheduling state exists yet. The post stays on the
workspace's "drafts" list until someone explicitly schedules or deletes it.

## 3. Create-and-schedule in one shot

```
POST /api/v1/posts/
body: {
  social_account_id, caption, action: "schedule",
  scheduled_at, idempotency_key: <fresh>
}
→ 201, status "scheduled"
```

Use when:
- The user is confident about the copy and the time
- You're translating a higher-level instruction ("post this tomorrow at 9am")
- You're batch-importing

Requires both `create_posts` AND `publish_directly` on the key.

## 4. Reschedule (move the time)

PATCH on a scheduled post re-times every scheduled child to the new
`scheduled_at`:

```
PATCH /api/v1/posts/{id}
body: { scheduled_at: "2026-06-02T14:00:00Z" }
→ 200
```

Validation runs before any DB write — if you accidentally include a bad
media UUID alongside the new `scheduled_at`, the WHOLE patch rejects
(no half-applied state).

## 5. Cancel a scheduled post

```
POST /api/v1/posts/{id}/cancel
→ 200, every child transitions to "draft"
```

After cancel, `Post.scheduled_at` is cleared and the post falls off the
publisher's poll. You can later re-schedule it via `POST /posts/{id}/schedule`.

## 6. Retry-safe writes

Wrap every POST you'd retry on transient failure with a fresh
`idempotency_key`:

```python
import uuid

idem = f"agent-{session_id}-create-{uuid.uuid4()}"
for attempt in range(3):
    r = requests.post(url, json={**body, "idempotency_key": idem}, timeout=10)
    if r.status_code == 201:
        return r.json()
    if r.status_code == 409:  # in-flight peer, brief backoff
        time.sleep(0.5)
        continue
    if r.status_code == 422 and "different request body" in r.text:
        # Programming error — your key/body got out of sync
        raise
    if r.status_code == 429:
        time.sleep(int(r.headers.get("Retry-After", 1)))
        continue
    r.raise_for_status()
```

The first call with a given `idempotency_key` creates the row; retries
with the same key + body return the same row. Retries with the same key
+ different body return 422 (a clear "you reused a key for a different
intent" signal).

## 7. Handling approval workflows

If the workspace has `approval_workflow_mode = required_internal*`, you
cannot schedule directly. The right pattern:

```
1. POST /api/v1/posts/ { action: "draft", ... }
2. Tell the user: "I drafted it. To publish it, please route it through
   the approval workflow in the Brightbean Studio UI: Workspace →
   Drafts → <this post> → Submit for review."
```

There's no API-only path to submit for review or approve in v1. The
agent surface deliberately stays on the "ready to schedule" side of the
approval gate.

## 8. Inspect status

```
GET /api/v1/posts/{id}
```

You'll get `status` (derived aggregate) and the `platform_posts` array.
For a single-account key the `platform_posts` array has exactly one
entry; reading its `status` is the authoritative state. `platform_post_id`
is the upstream platform's post ID after a successful publish — useful if
you want to surface a deep link back to the user.

## 9. Discover what failed

A `published_at: null` plus `status: "failed"` PlatformPost means the
publisher attempted to fire and the platform rejected. The Agent API
doesn't surface the platform's error message; the user has to inspect
the Brightbean Studio UI's publish log to see why. Tell them so — don't
invent a reason.

---

## Analytics recipes (read-only)

> Analytics is **observation-only**: `view_analytics` does not unlock
> `cancel_post`, `schedule_post`, or `create_draft`. Use these recipes
> to inform the user, then let the existing write workflows (#2, #3, #5)
> carry out any action the user confirms.

## 10. Schedule then poll for performance

The killer workflow. Schedule a post, record the `post_id`, then poll
analytics on the cadence the response hints back. Surface deltas to the
user — let *them* decide whether to follow up.

```
1. POST /api/v1/posts/  { action: "schedule", ... }  → returns post_id
2. Loop:
   a. GET /api/v1/analytics/posts/{post_id}
   b. Parse `platform_posts[*].captured_at` and `next_sync_eta`
   c. If captured_at is None and the post isn't published yet, sleep
      ~5 minutes and try again
   d. Otherwise, sleep until `max(next_sync_eta)` for the children you
      care about
   e. Surface the most recent metric tile values + delta to the user
3. If the user asks for a follow-up post, use `create_draft` /
   `schedule_post` — those mutations need `create_posts` and
   `publish_directly`, not `view_analytics`.
```

A `view_analytics`-only key can run the loop but cannot act on it; pair
the permission with the write permissions if you want a single key to do
both.

## 11. Channel-health check before scheduling

Before drafting the next post, peek at the channel's recent trend so the
agent can flag a stale or declining account.

```
1. GET /api/v1/analytics/accounts/{account_id}?days=30
2. If `analytics_available` is false, skip (platform doesn't expose
   analytics, or admin disabled it) — proceed with the draft normally.
3. If the engagement rate's `delta` is meaningfully negative, surface a
   line like: "Your engagement rate has dropped 18% over the last 30
   days. Want me to draft something more in the style of <top post> or
   should I keep your usual angle?"
4. Let the user decide. The agent does not change course on its own.
```

## 12. Learn from the last N posts when drafting

When the user asks for "another LinkedIn post about <topic>", check
which previous posts won and offer the user the chance to mimic the
best ones.

```
1. GET /api/v1/analytics/accounts/{account_id}?days=30
   → note the platform's primary hero metric (views / reach / impressions)
2. For each post_id you've been tracking (e.g. from prior conversations):
     GET /api/v1/analytics/posts/{post_id}
3. Sort by the platform's primary metric, surface the top 1-3 posts'
   captions and key numbers
4. Suggest: "Your top post used a question hook and dropped a stat in
   the first sentence. Want me to draft the new one in that style?"
5. Drafting still goes through `create_draft` — which has its own
   permission. The agent surfaces; the user (and the write tools)
   acts.
```

Both #11 and #12 are **suggestion-only**. The agent should not silently
cancel or re-schedule a scheduled post in response to a bad metric —
that's a user decision, and acting on it requires permissions
`view_analytics` doesn't grant.
