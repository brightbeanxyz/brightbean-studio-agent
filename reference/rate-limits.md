# Rate limits

Six tiers stack on every write. Reads only go through tiers 1 + 2 + 5.

## Tier 1 — Per-key writes (`120/minute`)

Burned by `POST /posts/*`, `PATCH /posts/*`, MCP `tools/call` (non-read).

Override per key: an admin can set `ApiKey.rate_override_writes` to a
non-null integer (including `0` for a freeze).

## Tier 2 — Per-key reads (`300/minute`)

Burned by `GET /me/`, `GET /accounts/`, `GET /posts/{id}`, MCP
`list_accounts` / `get_post`.

Override per key: `ApiKey.rate_override_reads`.

## Tier 3 — Per-key publish-hop (`1 per 5 seconds per SocialAccount`)

Specifically gates the moment a `PlatformPost` flips to `scheduled`.
Prevents an agent from rapid-firing many schedules at one account that
would all converge on the same publisher poll window and trip the
platform's own quota.

## Tier 4 — Per-workspace writes (`1000/minute aggregate`)

Sum of all writes from every key in the workspace. Stops one runaway
key from starving siblings.

## Tier 5 — Per-IP failed auth (`10/minute`)

Counts failed `verify_token` calls per source IP. Bad bearer + plain
HTTP (which also gets a 401) both count. At 10 failures the next call
short-circuits with another 401 before any HMAC work — opaque to
attackers, free for the server.

If you run Brightbean behind a trusted proxy, set
`BB_TRUSTED_PROXIES` in the env to the list of proxy IPs you trust to
set `X-Forwarded-For`. Otherwise the throttle keys off the direct
socket peer.

## Tier 6 — Per-platform 24h cap (rolling)

Matches each platform's published posting cap. Computed across all
`PlatformPost` rows for the target `SocialAccount` whose `updated_at`
falls within the last 24 hours AND whose status is in
`{scheduled, publishing, published, failed}` (drafts excluded —
they haven't reached the platform).

Default caps:

| Platform              | Cap / 24h |
|-----------------------|-----------|
| linkedin_personal     | 100       |
| linkedin_company      | 100       |
| facebook              | 200       |
| instagram             | 25        |
| instagram_login       | 25        |
| tiktok                | 15        |
| youtube               | 50        |
| pinterest             | 100       |
| threads               | 250       |
| mastodon              | 200       |
| bluesky               | 200       |
| google_business       | 50        |
| _unknown_             | 50        |

Override per account: `SocialAccount.daily_post_limit_override`.
Setting `0` is honored as a per-account freeze (do not fall through
to the platform default).

## 429 body and headers

```
HTTP/1.1 429 Too Many Requests
Retry-After: 4271
X-RateLimit-Limit: 25
X-RateLimit-Remaining: 0
Content-Type: application/json

{
  "error": "rate_limited",
  "tier":         "platform_quota:instagram",
  "limit":        25,
  "remaining":    0,
  "retry_after":  4271
}
```

Always honor `Retry-After`. For `platform_quota:*` you don't have to
back off the API itself — try a different account or move the schedule
to tomorrow. For `per_key_writes` / `per_workspace_writes`, real backoff
is the right move.

## Agent strategy

| Tier hit                  | Right reaction                            |
|---------------------------|-------------------------------------------|
| per_key_writes            | Sleep `retry_after` seconds, then retry   |
| per_key_reads             | Same                                      |
| per_key_publish_hop       | 5s backoff per `SocialAccount`            |
| per_workspace_writes      | Same as per_key_writes                    |
| per_ip_failed_auth        | Don't retry the same bad token; surface the auth failure |
| platform_quota:*          | Suggest a different account or tomorrow   |
| global                    | Sleep, then retry                         |
