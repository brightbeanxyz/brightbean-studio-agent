#!/usr/bin/env bash
# Cancel a scheduled post.
source "$(dirname "$0")/_common.sh"

POST_ID="${1:-${BRIGHTBEAN_POST_ID:-}}"
if [[ -z "${POST_ID}" ]]; then
    echo "Usage: $0 <post_id>" >&2
    exit 1
fi

curl_api POST "/posts/${POST_ID}/cancel" "{}"
