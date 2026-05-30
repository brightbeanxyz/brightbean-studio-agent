#!/usr/bin/env bash
# Idempotent POST with shell-level retry on 409 / 429.
source "$(dirname "$0")/_common.sh"

SOCIAL_ACCOUNT_ID="${1:-${BRIGHTBEAN_SOCIAL_ACCOUNT_ID:-}}"
[[ -z "${SOCIAL_ACCOUNT_ID}" ]] && { echo "Usage: $0 <social_account_id>"; exit 1; }

IDEM_KEY="agent-$(uuidgen 2>/dev/null || python3 -c 'import uuid; print(uuid.uuid4())')"
BODY=$(cat <<EOF
{
  "social_account_id": "${SOCIAL_ACCOUNT_ID}",
  "caption": "Retry-safe write with idempotency key.",
  "action": "draft",
  "idempotency_key": "${IDEM_KEY}"
}
EOF
)

for attempt in 1 2 3 4; do
    response=$(curl -sS -o /tmp/bb_resp.json -w "%{http_code}" \
        -X POST "${API}/posts/" \
        -H "Authorization: Bearer ${BRIGHTBEAN_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "${BODY}")
    case "${response}" in
        201)
            echo "Created on attempt ${attempt}:"
            cat /tmp/bb_resp.json | python3 -m json.tool
            exit 0
            ;;
        409)
            sleep "$(( attempt ))"
            echo "409 in-flight peer, retrying (attempt ${attempt})..." >&2
            ;;
        429)
            sleep 2
            echo "429 rate limited, sleeping (attempt ${attempt})..." >&2
            ;;
        *)
            echo "FAILED ${response}:" >&2
            cat /tmp/bb_resp.json >&2
            exit 1
            ;;
    esac
done

echo "Giving up after 4 attempts." >&2
exit 1
