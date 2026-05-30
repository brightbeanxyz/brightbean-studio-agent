"""Cancel a scheduled post (transition back to draft).

Useful when the user changes their mind before the publisher fires the
post. After cancel, the Post's ``scheduled_at`` is cleared and every
child platform-post drops back to ``draft``. You can later re-schedule
via ``POST /posts/{id}/schedule``.
"""

import json
import os
import sys

from client import BrightbeanClient

POST_ID = os.environ.get("BRIGHTBEAN_POST_ID") or input("Paste the Post id to cancel: ").strip()


def main() -> None:
    bb = BrightbeanClient()
    r = bb.post(f"/posts/{POST_ID}/cancel", {})
    if r.status_code != 200:
        print(f"FAILED {r.status_code}:")
        print(json.dumps(r.json(), indent=2))
        sys.exit(1)
    post = r.json()
    print(f"Canceled Post {post['id']}")
    print(f"  Post.scheduled_at = {post['scheduled_at']}")
    for pp in post["platform_posts"]:
        print(f"  platform_post {pp['platform']}: status={pp['status']}")


if __name__ == "__main__":
    main()
