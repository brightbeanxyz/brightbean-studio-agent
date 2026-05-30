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
