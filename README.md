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

## Install for AI agents

There's no universal "install a skill" command yet — each agent
runtime has its own discovery mechanism. The four realistic install
paths are listed below, ranked roughly by how seamless they are.
**Every path needs the same prerequisite**: the user must have minted a
bearer token in Brightbean Studio (Organization Settings → API Keys →
Issue new key) and saved it somewhere the agent can read.

### 1. Claude Desktop / Cursor / any MCP-aware client (most seamless)

Point the MCP client at the hosted endpoint. The agent learns the 5
Brightbean tools automatically through MCP's `tools/list` — no clone
required.

**Claude Desktop** — edit `~/Library/Application Support/Claude/claude_desktop_config.json`
(macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```jsonc
{
  "mcpServers": {
    "brightbean-studio": {
      "transport": {
        "type": "http",
        "url": "https://studio.brightbean.xyz/api/v1/mcp/",
        "headers": { "Authorization": "Bearer bb_studio_..." }
      }
    }
  }
}
```

**Cursor** — edit `~/.cursor/mcp.json` or `<repo>/.cursor/mcp.json`:

```jsonc
{
  "mcpServers": {
    "brightbean-studio": {
      "url": "https://studio.brightbean.xyz/api/v1/mcp/",
      "headers": { "Authorization": "Bearer bb_studio_..." }
    }
  }
}
```

Restart the client. The tools appear in the tool picker and the agent
can use them immediately. The `SKILL.md` body and `reference/*.md`
files do NOT auto-load — only the `inputSchema` + per-tool
descriptions are visible to the model. That's enough for basic use,
but if you want the agent to make smarter scheduling decisions (handle
rate limits, retry idempotently, etc.), also drop a clone of this repo
into the project's context so it can read the references.

Pre-canned snippets live in [`mcp/`](mcp/).

### 2. Claude Code (the CLI)

Claude Code auto-discovers skills in `~/.claude/skills/`:

```bash
git clone https://github.com/brightbeanxyz/brightbean-studio-agent ~/.claude/skills/brightbean-studio
```

The `SKILL.md` frontmatter triggers on phrases like *"schedule a
LinkedIn post"* or *"draft a Brightbean post."* For the MCP tool
surface on top, add the snippet from option 1 to Claude Code's MCP
settings file as well.

### 3. Codex / OpenClaw / OpenAI Agents SDK

These don't have a skill abstraction, so the install is two steps:

```bash
# 1) MCP server — add to your agent SDK's MCP config (same shape as
#    Cursor's snippet above).

# 2) Docs as context — clone the repo and either include the
#    SKILL.md + reference/*.md in your system prompt, or mount the
#    folder into the agent's file-reading scope.
git clone https://github.com/brightbeanxyz/brightbean-studio-agent
```

### 4. Generic REST consumer (Zapier, n8n, cron + curl, custom script)

No agent involved — just use the REST API. This is the 60-second tour
below.

---

## 60-second tour (REST consumer)

1. Mint a bearer token: **Brightbean Studio → Organization Settings →
   API Keys → Issue new key**. Pick the workspace and the social
   accounts the agent should act on. The token is shown **once** —
   save it immediately.
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
