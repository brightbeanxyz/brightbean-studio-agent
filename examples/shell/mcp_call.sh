#!/usr/bin/env bash
# Demo: speak MCP JSON-RPC to /api/v1/mcp/ with plain curl.
source "$(dirname "$0")/_common.sh"

post_mcp() {
    local body="$1"
    curl -sS -X POST "${MCP}" \
        -H "Authorization: Bearer ${BRIGHTBEAN_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "${body}"
}

echo "=== initialize ==="
post_mcp '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{}}}'
echo

echo "=== tools/list ==="
post_mcp '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
echo

echo "=== tools/call list_accounts ==="
post_mcp '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"list_accounts","arguments":{}}}'
