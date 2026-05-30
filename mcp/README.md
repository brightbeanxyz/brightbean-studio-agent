# MCP client configurations

Sample snippets for wiring Brightbean Studio's MCP server into popular
AI clients. **Replace `bb_studio_REPLACE_WITH_REAL_TOKEN` and the URL
with real values** before copying any of these into your client config.

## Claude Desktop

File location:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

Use the snippet in `claude_desktop_config.json`.

## Cursor

File locations:
- Global: `~/.cursor/mcp.json`
- Per-project: `<repo>/.cursor/mcp.json`

Use the snippet in `cursor_config.json`.

## OpenAI / Codex / OpenClaw / agent SDKs

Most MCP-aware agent frameworks accept the same Streamable HTTP transport
shape: an HTTPS URL + an `Authorization: Bearer ...` header. Point your
framework at `https://<your-studio-host>/api/v1/mcp/` and pass the
bearer in whatever header field your framework uses for static auth
headers.

## Why HTTP and not stdio?

Brightbean's MCP server is hosted (it lives inside the Django app, not
as a local subprocess), so the only transport the server speaks is
Streamable HTTP. Clients that only support stdio can either:

1. Use the REST API directly (everything MCP can do is also reachable
   via `/api/v1/posts/*`), or
2. Run a stdio→HTTP proxy locally — see Anthropic's `mcp-proxy` for an
   example.
