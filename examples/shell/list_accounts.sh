#!/usr/bin/env bash
# List the social accounts this API key may target.
source "$(dirname "$0")/_common.sh"

echo "=== /me/ ==="
curl_api GET /me/

echo
echo "=== /accounts/ ==="
curl_api GET /accounts/
