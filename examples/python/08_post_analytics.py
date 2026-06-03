"""Read a post's analytics, broken down per platform.

Equivalent to MCP ``get_post_analytics``. Requires the ``view_analytics``
permission on the key.

Pass the parent ``Post.id`` (the same UUID ``POST /posts/`` returned).
Multi-platform posts get one entry per ``PlatformPost`` child; each
child has its own ``analytics_available`` flag, metric tiles, and
freshness fields.

Drafts and scheduled posts return ``metric_tiles: []`` and
``captured_at: null`` — a valid empty envelope so polling loops can
start safely before publish.
"""

import json
import os
import sys

from client import BrightbeanClient

POST_ID = os.environ.get("BRIGHTBEAN_POST_ID") or input(
    "Paste a Post id (run 03_schedule_post.py or 02_create_draft.py first): "
).strip()


def _fmt(v: float, kind: str) -> str:
    if kind == "percent":
        return f"{v:.2f}%"
    if kind == "minutes":
        return f"{v:.1f} min"
    return f"{v:,.0f}"


def main() -> None:
    bb = BrightbeanClient()
    r = bb.get(f"/analytics/posts/{POST_ID}")
    if r.status_code != 200:
        print(f"FAILED {r.status_code}: {json.dumps(r.json(), indent=2)}")
        sys.exit(1)
    data = r.json()

    print(f"Post {data['post_id']}")
    print(f"  title:   {data['title']!r}")
    print(f"  caption: {data['caption'][:60]!r}")
    print(f"  platform_posts: {len(data['platform_posts'])}")
    print()

    for child in data["platform_posts"]:
        print(f"  ── {child['platform']} ({child['status']}) ──")
        print(f"     platform_post_id:   {child['platform_post_id']}")
        print(f"     published_at:       {child['published_at']}")
        print(f"     analytics_available: {child['analytics_available']}")
        if not child["analytics_available"]:
            print(f"     unavailable_reason: {child['unavailable_reason']}")
            continue
        print(f"     captured_at:        {child['captured_at']}")
        print(f"     next_sync_eta:      {child['next_sync_eta']}")
        if not child["metric_tiles"]:
            print("     (no metric tiles yet — not published or sync hasn't run)")
            continue
        print("     metric tiles:")
        for tile in child["metric_tiles"]:
            star = " *" if tile["is_primary"] else "  "
            print(
                f"      {star} {tile['label']:14}  {_fmt(tile['value'], tile['kind']):>10}"
                f"  series_len={len(tile['series'])}"
            )


if __name__ == "__main__":
    main()
