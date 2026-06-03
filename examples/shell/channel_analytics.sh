#!/usr/bin/env bash
# Read a channel's analytics — hero KPIs, engagement, follower growth.
# Equivalent to MCP get_account_analytics.
#
# Requires view_analytics permission on the key.
#
# Usage:
#   BRIGHTBEAN_ACCOUNT_ID=<uuid> BRIGHTBEAN_DAYS=30 ./channel_analytics.sh
source "$(dirname "$0")/_common.sh"

if [[ -z "${BRIGHTBEAN_ACCOUNT_ID:-}" ]]; then
    echo "Set BRIGHTBEAN_ACCOUNT_ID (run list_accounts.sh first)." >&2
    exit 1
fi
DAYS="${BRIGHTBEAN_DAYS:-30}"

echo "=== /analytics/accounts/${BRIGHTBEAN_ACCOUNT_ID}?days=${DAYS} ==="
curl_api GET "/analytics/accounts/${BRIGHTBEAN_ACCOUNT_ID}?days=${DAYS}"
