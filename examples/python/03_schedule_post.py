"""Schedule a draft for publishing.

Two ways to schedule:

  (A) Pre-existing draft — POST /posts/{id}/schedule (this example)
  (B) Create + schedule in one shot — see the commented block below

Requires ``publish_directly`` on the key. The publisher polls every
~15s, so a ``scheduled_at`` of "30 seconds from now" will fire on the
next tick after that mark — give it a minute of headroom in testing.
"""

import datetime as dt
import json
import os
import sys

from client import BrightbeanClient

POST_ID = os.environ.get("BRIGHTBEAN_POST_ID") or input(
    "Paste the Post id from 02_create_draft.py: "
).strip()
WHEN = os.environ.get("BRIGHTBEAN_SCHEDULED_AT") or (
    dt.datetime.now(dt.UTC) + dt.timedelta(minutes=5)
).isoformat()


def main() -> None:
    bb = BrightbeanClient()
    r = bb.post(f"/posts/{POST_ID}/schedule", {"scheduled_at": WHEN})
    if r.status_code != 200:
        print(f"FAILED {r.status_code}:")
        print(json.dumps(r.json(), indent=2))
        sys.exit(1)
    post = r.json()
    print(f"Scheduled Post {post['id']} at {post['scheduled_at']}")
    print(
        f"  platform_post: {post['platform_posts'][0]['platform']} "
        f"status={post['platform_posts'][0]['status']} "
        f"scheduled_at={post['platform_posts'][0]['scheduled_at']}"
    )

    # ---- Alternative: create + schedule in one shot --------------------
    #
    # import uuid
    # r = bb.post("/posts/", {
    #     "social_account_id": "<account-uuid>",
    #     "caption": "Going out at 9 tomorrow.",
    #     "action": "schedule",
    #     "scheduled_at": WHEN,
    #     "idempotency_key": f"oneshot-{uuid.uuid4()}",
    # })
    # post = r.json()


if __name__ == "__main__":
    main()
