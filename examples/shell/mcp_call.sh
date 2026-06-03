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

# The analytics tools require view_analytics on the key. Set
# BRIGHTBEAN_ACCOUNT_ID / BRIGHTBEAN_POST_ID before sourcing this file
# to also exercise them.
if [[ -n "${BRIGHTBEAN_ACCOUNT_ID:-}" ]]; then
    echo
    echo "=== tools/call get_account_analytics ==="
    post_mcp "{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":{\"name\":\"get_account_analytics\",\"arguments\":{\"account_id\":\"${BRIGHTBEAN_ACCOUNT_ID}\",\"days\":30}}}"
fi

if [[ -n "${BRIGHTBEAN_POST_ID:-}" ]]; then
    echo
    echo "=== tools/call get_post_analytics ==="
    post_mcp "{\"jsonrpc\":\"2.0\",\"id\":5,\"method\":\"tools/call\",\"params\":{\"name\":\"get_post_analytics\",\"arguments\":{\"post_id\":\"${BRIGHTBEAN_POST_ID}\"}}}"
fi
