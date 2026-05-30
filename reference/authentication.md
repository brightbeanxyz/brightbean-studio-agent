# Authentication

## Token format

```
bb_studio_<random32>_<lookup8>
   ─┬──    ─┬──         ─┬──
    │       │            └── 8-hex-char content hash of random32 (lookup index)
    │       └────────────── url-safe random; ~256 bits of entropy; secret part
    └────────────────────── environment prefix (bb_test_ on staging)
```

The `bb_studio_` prefix exists so GitHub's secret-scanning and similar
tools can pick the token up if it ever lands in a public repo. Keep
tokens out of source — read them from environment variables.

## Wire format

Every request:

```
Authorization: Bearer bb_studio_<random>_<lookup>
```

That's it. No `Mcp-Session-Id`, no CSRF, no cookies. The token IS the
session.

## What's stored where

| What                 | Where                  | Why                                  |
|----------------------|------------------------|--------------------------------------|
| Plaintext token      | Nowhere (one-time)     | Brightbean shows it once at issuance |
| `lookup_prefix`      | DB, indexed plaintext  | O(1) row lookup                      |
| HMAC of random part  | DB                     | Server-side compare; defends DB leak |
| `workspace_id`       | FK on the key          | Scope ceiling                        |
| Allowlisted accounts | M2M                    | Per-account scope                    |
| Permissions          | JSONField list         | Subset of issuer's grantable perms   |
| `last_used_at` / `_ip` | Debounced (60s)      | Observability                        |

## Defense-in-depth checks on every request

The auth class verifies (in order, all on every call):

1. **IP throttle** — if the source IP has accumulated ≥10 failed-auth
   attempts in the last 60 seconds, return 401 without checking the token.
2. **HTTPS guard** — if the request isn't HTTPS and DEBUG is off, return
   401 and count it toward the IP throttle.
3. **Token parse + HMAC compare** — constant-time.
4. **Key state** — not revoked, not expired.
5. **Issuer membership** — the user who issued the key must still have
   `WorkspaceMembership` in the key's workspace. Revoke a user's
   membership and their key dies on the next request.
6. **Permission intersection** — recomputed per request from the issuer's
   current effective permissions ∩ the key's granted set.

## HTTPS / DEBUG behavior

In production (`DEBUG=False`), the API refuses plain HTTP with a generic
401 (no `"Agent API requires HTTPS"` message — that would be a product
fingerprint). In local dev with `DEBUG=True`, `http://127.0.0.1:8000`
works for testing.

## Failed-auth IP throttle

After 10 consecutive failures from the same IP within 60 seconds, the
throttle short-circuits subsequent attempts. The response is still 401
(opaque to attackers), but the HMAC check is skipped — so a brute-force
script can't even pay the CPU cost.

If you operate Brightbean behind a trusted proxy (Cloudflare, ALB, nginx),
set `BB_TRUSTED_PROXIES` in the Brightbean Studio env to the list of
proxy IPs you trust to set `X-Forwarded-For` honestly. Without that, the
throttle uses the direct socket peer.

## Revocation

Two ways:

1. Org admin clicks **Revoke** in `Organization Settings → API Keys`.
2. Server-side: `services.revoke_api_key(api_key)`.

Either path busts the in-process auth cache instantly via the
`apps.api_keys.signals` handlers. The agent gets a 401 on its very next
request — there is no 30-second grace period.

## Per-key rate-limit overrides

An admin can override the per-key write or read rate by setting
`ApiKey.rate_override_writes` / `rate_override_reads` to a per-minute
integer. **0 is honoured as a freeze**, not as "no override" — useful
to put a misbehaving key on a one-day timeout without revoking it.
