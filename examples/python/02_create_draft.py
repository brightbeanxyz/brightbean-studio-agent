"""Create a draft post.

Run after ``01_list_accounts.py`` and substitute one of the printed
account IDs into ``SOCIAL_ACCOUNT_ID`` below. The draft sits on the
workspace's drafts list until you either schedule it via
``03_schedule_post.py`` / a separate ``POST /posts/{id}/schedule`` call,
or until the user routes it through the approval workflow in the UI.
"""

import json
import os
import uuid

from client import BrightbeanClient

SOCIAL_ACCOUNT_ID = os.environ.get("BRIGHTBEAN_SOCIAL_ACCOUNT_ID") or input(
    "Paste a social_account_id from list_accounts: "
).strip()


def main() -> None:
    bb = BrightbeanClient()
    body = {
        "social_account_id": SOCIAL_ACCOUNT_ID,
        "caption": (
            "Hello from the Brightbean Studio Agent API example. "
            "I'm a draft — nothing is queued for publishing yet."
        ),
        "action": "draft",
        # Always include a fresh idempotency_key on writes you might retry.
        "idempotency_key": f"example-create-{uuid.uuid4()}",
    }
    r = bb.post("/posts/", body)
    if r.status_code != 201:
        print(f"FAILED {r.status_code}:")
        print(json.dumps(r.json(), indent=2))
        return
    post = r.json()
    print(f"Created draft Post {post['id']}")
    print(f"  caption: {post['caption']!r}")
    print(f"  platform_post status: {post['platform_posts'][0]['status']}")
    print()
    print("Save this ID — you'll need it for 03_schedule_post.py:")
    print(post["id"])


if __name__ == "__main__":
    main()
