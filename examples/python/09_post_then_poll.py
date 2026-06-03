"""End-to-end demo of the closed loop: schedule a post, then poll its
analytics on the cadence the API hints back.

This is the workflow the new analytics surface unlocks. The script:

  1. Lists accounts (so the user knows what's targetable).
  2. Schedules a post a few minutes out — requires ``create_posts`` AND
     ``publish_directly``.
  3. Loops on ``GET /analytics/posts/{id}`` until the post has been
     synced once, then exits — a real agent would keep going.

The polling loop honours the ``next_sync_eta`` field; it never polls
faster than the backend syncs.

Run with:

    export BRIGHTBEAN_BASE_URL=https://studio.brightbean.xyz
    export BRIGHTBEAN_TOKEN=bb_studio_...
    python 09_post_then_poll.py
"""

import datetime as dt
import json
import os
import sys
import time
import uuid

from client import BrightbeanClient

# Maximum wall-clock time to keep polling. The example exits long before
# this in normal use; the cap is a safety net.
MAX_TOTAL_SECONDS = 60 * 60  # 1 hour
# Minimum sleep between polls — even if next_sync_eta is in the past, we
# don't pound the API. The backend's hot-window cadence is 1 hour anyway.
MIN_SLEEP_SECONDS = 60


def _iso_to_dt(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def main() -> None:
    bb = BrightbeanClient()

    accounts = bb.get("/accounts/").json()["accounts"]
    if not accounts:
        sys.exit("This key has no allowlisted accounts. Reissue with --accounts.")
    account_id = os.environ.get("BRIGHTBEAN_ACCOUNT_ID") or accounts[0]["id"]
    print(f"Targeting account_id={account_id}")

    when = (dt.datetime.now(dt.UTC) + dt.timedelta(minutes=2)).isoformat()
    body = {
        "social_account_id": account_id,
        "caption": "Demo post from 09_post_then_poll.py — agent-driven closed loop.",
        "action": "schedule",
        "scheduled_at": when,
        "idempotency_key": f"closed-loop-{uuid.uuid4()}",
    }
    r = bb.post("/posts/", body)
    if r.status_code not in (200, 201):
        print(f"Schedule FAILED {r.status_code}:")
        print(json.dumps(r.json(), indent=2))
        sys.exit(1)
    post = r.json()
    post_id = post["id"]
    print(f"Scheduled Post {post_id} for {when}")
    print()

    started = time.monotonic()
    poll_n = 0
    while time.monotonic() - started < MAX_TOTAL_SECONDS:
        poll_n += 1
        r = bb.get(f"/analytics/posts/{post_id}")
        if r.status_code != 200:
            print(f"Poll #{poll_n} FAILED {r.status_code}: {r.text[:200]}")
            break
        data = r.json()
        child = data["platform_posts"][0]
        captured = child["captured_at"]
        next_eta = child["next_sync_eta"]
        tiles = child["metric_tiles"]
        print(
            f"Poll #{poll_n}: status={child['status']} "
            f"captured_at={captured} next_sync_eta={next_eta} "
            f"tiles={len(tiles)}"
        )
        if tiles:
            top = tiles[0]
            print(f"  primary metric → {top['label']}={top['value']}")
            print("First successful sync received; a real agent would keep polling.")
            break

        # Decide how long to sleep. Prefer next_sync_eta when present;
        # otherwise fall back to MIN_SLEEP_SECONDS.
        sleep_s = MIN_SLEEP_SECONDS
        next_dt = _iso_to_dt(next_eta)
        if next_dt is not None:
            remaining = (next_dt - dt.datetime.now(dt.UTC)).total_seconds()
            sleep_s = max(MIN_SLEEP_SECONDS, int(remaining))
        print(f"  → sleeping {sleep_s}s before next poll …")
        time.sleep(sleep_s)


if __name__ == "__main__":
    main()
