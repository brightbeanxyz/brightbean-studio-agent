# MCP tools reference

Transport: Streamable HTTP at `https://<your-studio-host>/api/v1/mcp/`.
Auth: same `Authorization: Bearer bb_studio_...` header as REST.

## Protocol version

Brightbean implements MCP `2025-03-26`. The server doesn't issue
`Mcp-Session-Id` headers — the bearer is the session.

## Built-in methods

| Method                          | Purpose                                       |
|---------------------------------|-----------------------------------------------|
| `initialize`                    | Handshake; returns serverInfo + capabilities  |
| `notifications/initialized`     | Notification (no reply) after init            |
| `ping`                          | Keepalive / liveness                          |
| `tools/list`                    | List available tools (5 today)                |
| `tools/call`                    | Invoke one tool                               |

Batched JSON-RPC is supported. A batch of N messages costs N rate-limit
tokens (not N+1) — same accounting as N separate POSTs.

## Tools

Each tool's `inputSchema` is validated server-side via JSON Schema (Draft
2020-12). Type mismatches, missing required fields, and unknown fields
return `-32602 INVALID_PARAMS` with a path-pointed error message:
`tools/call 'create_draft': caption: {'x': 1} is not of type 'string'`.

Successful tool calls return:
```json
{
  "content": [{"type": "text", "text": "<json-stringified payload>"}],
  "isError": false
}
```

The `text` field is a JSON-stringified version of the same payload the
REST endpoint would return. Parse it with `JSON.parse` / `json.loads`.

### `list_accounts`

No arguments. Returns the allowlist (equivalent to `GET /api/v1/accounts/`).

Use this first in any new session to learn valid `social_account_id` values.

### `create_draft`

```json
{
  "name": "create_draft",
  "arguments": {
    "social_account_id": "uuid",       // required
    "caption": "string",               // required, max 10000
    "title": "",                       // optional, max 255
    "first_comment": "",               // optional
    "media_asset_ids": []              // optional
  }
}
```

Permission required: `create_posts`. Returns the freshly-created `Post`
in draft state.

### `schedule_post`

```json
{
  "name": "schedule_post",
  "arguments": {
    "social_account_id": "uuid",       // required
    "caption": "string",               // required
    "scheduled_at": "ISO 8601 UTC",    // required
    "title": "",
    "first_comment": "",
    "media_asset_ids": []
  }
}
```

Permission required: `create_posts` AND `publish_directly`. Creates the
post directly in `scheduled` state. Checks per-platform 24h quota before
creating; if over, raises an INVALID_PARAMS with a message that includes
the platform name.

### `get_post`

```json
{
  "name": "get_post",
  "arguments": { "post_id": "uuid" }
}
```

Returns the post payload as in `GET /api/v1/posts/{id}`. Same allowlist
opacity: "not in workspace" / "outside allowlist" / "doesn't exist" all
return the same `Post not found` error.

### `cancel_post`

```json
{
  "name": "cancel_post",
  "arguments": { "post_id": "uuid" }
}
```

Permission required: `create_posts`. Transitions every scheduled child
back to `draft`. Errors if there are no scheduled children.

## Error code mapping (server-side audit)

For your forensic queries, the server maps JSON-RPC error codes to HTTP
status codes when logging:

| JSON-RPC code | HTTP equivalent |
|---------------|-----------------|
| -32700 PARSE_ERROR | 400 |
| -32600 INVALID_REQUEST | 400 |
| -32601 METHOD_NOT_FOUND | 404 |
| -32602 INVALID_PARAMS | 422 |
| -32603 INTERNAL_ERROR | 500 |

`tools/call` invocations are audit-logged as
`mcp.tools/call:<tool_name>` with the derived status code.

## Sample MCP client configurations

See `mcp/claude_desktop_config.json` for a Claude Desktop snippet and
`mcp/cursor_config.json` for a Cursor snippet. Both wire the bearer token
through the `headers` field of a Streamable HTTP transport.
