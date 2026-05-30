# brightbean-studio-agent

Everything an AI agent — Claude Code, Cursor, Codex, OpenClaw, or a
plain LLM-driven script — needs to schedule and manage social-media
posts via [Brightbean Studio](https://github.com/brightbeanxyz/brightbean-studio)'s
Agent API.

## Quick links

| Want                                | Look at                                  |
|-------------------------------------|------------------------------------------|
| Drop-in Anthropic Skill             | [`SKILL.md`](SKILL.md)                   |
| Surface map (orgs / accounts / posts) | [`reference/overview.md`](reference/overview.md) |
| Bearer-token auth details           | [`reference/authentication.md`](reference/authentication.md) |
| Full REST API reference             | [`reference/rest-api.md`](reference/rest-api.md) |
| MCP tools reference                 | [`reference/mcp-tools.md`](reference/mcp-tools.md) |
| Every error you can hit             | [`reference/errors.md`](reference/errors.md) |
| Six-tier rate-limit model           | [`reference/rate-limits.md`](reference/rate-limits.md) |
| Common workflows                    | [`reference/workflows.md`](reference/workflows.md) |
| OpenAPI 3.1 spec snapshot           | [`docs/openapi.json`](docs/openapi.json) |
| Working Python examples             | [`examples/python/`](examples/python/)   |
| Working shell examples              | [`examples/shell/`](examples/shell/)     |
| MCP client configs (Claude / Cursor)| [`mcp/`](mcp/)                           |

## 60-second tour

1. Ask the user to mint a bearer token in their Brightbean Studio app:
   **Organization Settings → API Keys → Issue new key**, then pick the
   workspace and the social accounts the agent should act on. The token
   is shown **once** at issuance — the agent (or the user) must save
   it immediately.
2. Set two env vars (use your own host if self-hosted):
   ```bash
   export BRIGHTBEAN_BASE_URL=https://studio.brightbean.xyz
   export BRIGHTBEAN_TOKEN=bb_studio_...
   ```
3. Discover available accounts:
   ```bash
   bash examples/shell/list_accounts.sh
   ```
4. Draft + schedule a post:
   ```bash
   bash examples/shell/create_draft.sh <social_account_id>
   bash examples/shell/schedule_post.sh <post_id>
   ```

Same paths in Python:

```bash
cd examples/python
pip install -r requirements.txt
python 01_list_accounts.py
python 02_create_draft.py
python 03_schedule_post.py
```

For MCP-aware clients (Claude Desktop, Cursor), copy the snippets in
[`mcp/`](mcp/) into your client config.

## Why both REST and MCP?

Brightbean Studio exposes the **same capability set** via two transports:

- **REST** — Plain HTTP / JSON, works anywhere a request library does.
  Great for backends, scripts, Make/Zapier, agents without MCP support.
- **MCP** — JSON-RPC 2.0 over Streamable HTTP at `/api/v1/mcp/`. Same
  auth, same business logic, but the tool calls are type-checked
  server-side against the published `inputSchema` so clients get
  structured feedback on bad arguments.

Pick whichever your agent runtime prefers. The two surfaces share the
audit log, rate limits, idempotency, and platform quotas — there's no
"REST is faster, MCP is safer" tradeoff to worry about.

## Repo layout

```
.
├── SKILL.md                            ← Anthropic Skill entry point
├── README.md                           ← this file
├── reference/                          ← deep-dive docs
│   ├── overview.md
│   ├── authentication.md
│   ├── rest-api.md
│   ├── mcp-tools.md
│   ├── errors.md
│   ├── rate-limits.md
│   └── workflows.md
├── examples/
│   ├── python/                         ← reusable client + 6 scripts
│   └── shell/                          ← 7 curl scripts
├── mcp/                                ← Claude Desktop & Cursor configs
└── docs/
    └── openapi.json                    ← snapshot of /api/v1/openapi.json
```

## Versioning

The repo tracks Brightbean Studio's API version. The current spec is
**1.0.0** (see `info.version` in `docs/openapi.json`). Any breaking
change to the API would bump the major version and be accompanied by a
new branch / tag here.

## Contributing

Issues and PRs welcome — especially:

- Example scripts in other languages (Go, Node, Ruby, …)
- MCP client configs for less-common runtimes
- Translations of `SKILL.md` for non-English agent surfaces

## License

[MIT](LICENSE).
