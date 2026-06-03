#!/usr/bin/env bash
# Read a post's analytics, broken down per platform.
# Equivalent to MCP get_post_analytics.
#
# Requires view_analytics permission on the key.
#
# Usage:
#   BRIGHTBEAN_POST_ID=<uuid> ./post_analytics.sh
source "$(dirname "$0")/_common.sh"

if [[ -z "${BRIGHTBEAN_POST_ID:-}" ]]; then
    echo "Set BRIGHTBEAN_POST_ID (run create_draft.sh / schedule_post.sh first)." >&2
    exit 1
fi

echo "=== /analytics/posts/${BRIGHTBEAN_POST_ID} ==="
curl_api GET "/analytics/posts/${BRIGHTBEAN_POST_ID}"
