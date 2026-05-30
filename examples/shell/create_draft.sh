#!/usr/bin/env bash
# Create a draft. Substitute SOCIAL_ACCOUNT_ID with a UUID from list_accounts.
source "$(dirname "$0")/_common.sh"

SOCIAL_ACCOUNT_ID="${1:-${BRIGHTBEAN_SOCIAL_ACCOUNT_ID:-}}"
if [[ -z "${SOCIAL_ACCOUNT_ID}" ]]; then
    echo "Usage: $0 <social_account_id>" >&2
    exit 1
fi

# uuidgen exists on macOS; on Linux use `python -c 'import uuid; print(uuid.uuid4())'`.
IDEM_KEY="example-draft-$(uuidgen 2>/dev/null || python3 -c 'import uuid; print(uuid.uuid4())')"

curl_api POST /posts/ "$(cat <<EOF
{
  "social_account_id": "${SOCIAL_ACCOUNT_ID}",
  "caption": "Drafted via shell example.",
  "action": "draft",
  "idempotency_key": "${IDEM_KEY}"
}
EOF
)"
