#!/usr/bin/env bash
# Shared setup for the shell examples.
#
# Source this from any example: ``source ./_common.sh``
# Expects two env vars:
#   BRIGHTBEAN_BASE_URL — e.g. https://studio.example.com
#   BRIGHTBEAN_TOKEN    — the bb_studio_... bearer
#
# Provides:
#   ${BASE}            — base URL without trailing slash
#   ${API}             — ${BASE}/api/v1
#   ${MCP}             — ${BASE}/api/v1/mcp/
#   curl_api METHOD PATH [BODY] — convenience wrapper

set -euo pipefail

if [[ -z "${BRIGHTBEAN_BASE_URL:-}" || -z "${BRIGHTBEAN_TOKEN:-}" ]]; then
    echo "Set BRIGHTBEAN_BASE_URL and BRIGHTBEAN_TOKEN before running." >&2
    echo "  export BRIGHTBEAN_BASE_URL=https://studio.example.com" >&2
    echo "  export BRIGHTBEAN_TOKEN=bb_studio_..." >&2
    exit 1
fi

BASE="${BRIGHTBEAN_BASE_URL%/}"
API="${BASE}/api/v1"
MCP="${BASE}/api/v1/mcp/"

curl_api() {
    local method="$1"
    local path="$2"
    local body="${3:-}"
    local args=(
        -sS
        -X "${method}"
        -H "Authorization: Bearer ${BRIGHTBEAN_TOKEN}"
        -H "Content-Type: application/json"
        -w "\n[HTTP %{http_code}]\n"
    )
    if [[ -n "${body}" ]]; then
        args+=(-d "${body}")
    fi
    curl "${args[@]}" "${API}${path}"
}
