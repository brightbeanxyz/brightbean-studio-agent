# Error envelope reference

Every Agent API error response — REST and the JSON-RPC equivalents — uses
the same wire shape so agents can parse the `error` field and branch
mechanically instead of regexing free-text.

## REST shape

```json
{
  "error": "rate_limited|forbidden|not_found|unprocessable_entity|conflict|bad_request|unauthorized",
  "detail": "Human-readable explanation",

  "tier":         "...",           // present on 429s only
  "limit":        0,               // present on 429s only
  "remaining":    0,               // present on 429s only
  "retry_after":  0,               // present on 429s only — seconds
  "reset_at":     null             // present on some 429s — ISO timestamp
}
```

On 429s, the matching HTTP `Retry-After` header is also set.

## JSON-RPC shape (MCP)

Standard JSON-RPC 2.0 error envelope:

```json
{
  "jsonrpc": "2.0",
  "id": <request_id>,
  "error": { "code": -32602, "message": "..." }
}
```

Codes:

| Code   | Name              | When                                       |
|--------|-------------------|--------------------------------------------|
| -32700 | PARSE_ERROR       | Invalid JSON                               |
| -32600 | INVALID_REQUEST   | Missing `jsonrpc`/`method` etc.            |
| -32601 | METHOD_NOT_FOUND  | Unknown method                             |
| -32602 | INVALID_PARAMS    | Tool arg validation, missing required, etc.|
| -32603 | INTERNAL_ERROR    | Last-ditch — bug in the server             |

Application-layer errors (permission denied, allowlist, quota, approval
gate) are carried via `-32602 INVALID_PARAMS` with a descriptive message
because that's the closest fit in the JSON-RPC scheme.

## Common errors and how to recover

| What you'll see                                          | Cause                                            | Recovery                                     |
|----------------------------------------------------------|--------------------------------------------------|----------------------------------------------|
| HTTP 401 (no body, or `{"error": "unauthorized"}`)       | Missing/bad bearer, expired, revoked, issuer offboarded, or IP-throttled | Re-issue the token. If retrying — back off; the IP may be throttled |
| HTTP 403 `forbidden` `detail: "Permission denied: ..."`  | Key lacks the permission the route needs         | Ask the user to re-issue with the missing perm (commonly `publish_directly` for schedule) |
| HTTP 403 `forbidden` `detail: "SocialAccount is not in this key's allowlist."` | `social_account_id` not in the allowlist | Pick a different account, or have the user re-issue a key with that account included |
| HTTP 404 `not_found`                                     | Post doesn't exist, lives in another workspace, OR has a child outside this key's allowlist | The three are deliberately indistinguishable — don't probe, ask the user |
| HTTP 409 `conflict` `detail: "...idempotency_key is still in flight..."` | A peer holds the slot | Retry after a brief backoff (100ms-1s)        |
| HTTP 409 `conflict` `detail: "Post is not editable in status published."` | Trying to PATCH a published post     | Can't unpublish via API — create a new post  |
| HTTP 409 `conflict` `detail: "No draft platform posts to schedule."` | Tried to schedule a post that's already scheduled or canceled | Use the right transition for the current state |
| HTTP 422 `unprocessable_entity` `detail: "scheduled_at is required when action='schedule'"` | Body missing required field for that action | Add the field |
| HTTP 422 `unprocessable_entity` `detail: "SocialAccount ... is in connection_status 'disconnected'..."` | User's OAuth token expired | Ask user to reconnect the account in the studio UI |
| HTTP 422 `unprocessable_entity` `detail: "Workspace requires approval before scheduling..."` | Workspace approval gate | Create as draft, route through the studio's approval workflow manually |
| HTTP 422 `unprocessable_entity` `detail: "idempotency_key reused with a different request body..."` | Same idempotency key, different intent | Use a fresh idempotency_key for the new intent |
| HTTP 422 `unprocessable_entity` `detail: "Media asset(s) not in workspace: [...]"` | `media_asset_ids` referencing wrong workspace, or typo | Verify the IDs come from the same workspace as the key |
| HTTP 429 `rate_limited` `tier: "per_key_writes"` | Slow your writes | Honor `retry_after` (seconds) |
| HTTP 429 `rate_limited` `tier: "per_workspace_writes"` | Another key in the workspace is using budget | Same — honor `retry_after` |
| HTTP 429 `rate_limited` `tier: "platform_quota:<platform>"` | Hit the platform's 24h cap | Try a different account, or wait until tomorrow |
| HTTP 429 `rate_limited` `tier: "per_key_publish_hop"` | Triggering many schedules for one account too fast | 5-second backoff per account |
| HTTP 429 `rate_limited` `tier: "global"` | Operator's instance-wide cap | Wait, then retry |
| MCP `-32602` `"... tier=platform_quota:..."`             | Same as the 429 family but via MCP | Same recovery — extract `tier` from the message and respond |

## Authoring tip — show, don't summarize

When something fails, surface the `detail` field verbatim to the user.
Brightbean's error messages are written to be self-explanatory. Inventing
your own summary risks losing critical context (which permission was
missing, which platform's quota was hit).
