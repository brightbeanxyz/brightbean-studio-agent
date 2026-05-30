"""Retry-safe POST with idempotency.

Demonstrates the right way to wrap a create call so that:
  * Transient network errors trigger retry without duplicating the post.
  * A 409 ("peer is mid-flight on the same key") backs off briefly.
  * A 429 honors ``Retry-After``.
  * A 422 that complains about "different request body" is a programming
    error — don't retry, surface it.

The same pattern works for ``/posts/{id}/schedule`` and
``/posts/{id}/cancel``.
"""

import json
import os
import time
import uuid

import requests

from client import BrightbeanClient


def post_with_retry(
    bb: BrightbeanClient,
    body: dict,
    *,
    max_attempts: int = 4,
) -> dict:
    """POST /api/v1/posts/ with idempotency + retry. Returns the JSON body.

    Mutates ``body`` to add a fresh ``idempotency_key`` if missing.
    """
    body.setdefault("idempotency_key", f"agent-{uuid.uuid4()}")
    for attempt in range(1, max_attempts + 1):
        try:
            r = bb.post("/posts/", body)
        except requests.RequestException as exc:
            if attempt == max_attempts:
                raise
            wait = min(2**attempt, 30)
            print(f"transport error attempt={attempt} sleeping {wait}s ({exc})")
            time.sleep(wait)
            continue

        if r.status_code == 201:
            return r.json()
        if r.status_code == 409:
            wait = 0.5 * attempt
            print(f"409 in-flight peer attempt={attempt} sleeping {wait:.1f}s")
            time.sleep(wait)
            continue
        if r.status_code == 429:
            wait = int(r.headers.get("Retry-After", "1"))
            tier = r.json().get("tier")
            print(f"429 tier={tier!r} sleeping {wait}s")
            time.sleep(wait)
            continue
        if r.status_code == 422:
            err = r.json()
            if "different request body" in err.get("detail", ""):
                raise RuntimeError(
                    "idempotency_key collision with different intent — "
                    "this is a programming error, refusing to retry"
                )
        r.raise_for_status()
    raise RuntimeError(f"giving up after {max_attempts} attempts")


def main() -> None:
    bb = BrightbeanClient()
    sa = os.environ.get("BRIGHTBEAN_SOCIAL_ACCOUNT_ID") or input(
        "Paste a social_account_id: "
    ).strip()
    body = {
        "social_account_id": sa,
        "caption": "Retry-safe write with idempotency key.",
        "action": "draft",
    }
    result = post_with_retry(bb, body)
    print("Created:", result["id"])


if __name__ == "__main__":
    main()
