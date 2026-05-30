#!/usr/bin/env bash
# Schedule an existing draft. Pass the Post id from create_draft.sh.
source "$(dirname "$0")/_common.sh"

POST_ID="${1:-${BRIGHTBEAN_POST_ID:-}}"
if [[ -z "${POST_ID}" ]]; then
    echo "Usage: $0 <post_id> [scheduled_at_iso]" >&2
    exit 1
fi

# Default: 5 minutes from now in UTC.
WHEN="${2:-$(date -u -v+5M +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u -d '+5 minutes' +"%Y-%m-%dT%H:%M:%SZ")}"

curl_api POST "/posts/${POST_ID}/schedule" "{\"scheduled_at\": \"${WHEN}\"}"
