"""Read a channel's analytics — hero KPIs, engagement, follower growth.

Equivalent to MCP ``get_account_analytics``. Requires the
``view_analytics`` permission on the key.

The ``days`` query param must be 7, 30, or 90; the server enforces
``7 <= days <= 90`` and 422s on violation.
"""

import json
import os
import sys

from client import BrightbeanClient

ACCOUNT_ID = os.environ.get("BRIGHTBEAN_ACCOUNT_ID") or input(
    "Paste a social_account_id (run 01_list_accounts.py first): "
).strip()
DAYS = int(os.environ.get("BRIGHTBEAN_DAYS", "30"))


def _fmt(v: float, kind: str) -> str:
    if kind == "percent":
        return f"{v:.2f}%"
    if kind == "minutes":
        return f"{v:.1f} min"
    return f"{v:,.0f}"


def main() -> None:
    bb = BrightbeanClient()
    r = bb.get(f"/analytics/accounts/{ACCOUNT_ID}?days={DAYS}")
    if r.status_code != 200:
        print(f"FAILED {r.status_code}: {json.dumps(r.json(), indent=2)}")
        sys.exit(1)
    data = r.json()

    print(f"Account: {data['account_name']} ({data['platform']})")
    print(f"  connection_status:    {data['connection_status']}")
    print(f"  analytics_available:  {data['analytics_available']}")
    if not data["analytics_available"]:
        print(f"  unavailable_reason:   {data['unavailable_reason']}")
        return
    print(f"  window:               last {data['days']} days")
    print(f"  captured_at:          {data['captured_at']}")
    print(f"  next_sync_eta:        {data['next_sync_eta']}")
    print()

    print("Hero metrics:")
    for m in data["hero_metrics"]:
        print(
            f"  - {m['label']:18}  {_fmt(m['value'], m['kind']):>12}  "
            f"({m['delta']:+}% vs. prior {data['days']}d)"
        )

    if data["engagement"]:
        rate = data["engagement"]["rate"]
        print()
        print(f"Engagement rate: {_fmt(rate['value'], rate['kind'])} "
              f"({rate['delta']:+}% vs. prior)")
        for p in data["engagement"]["parts"]:
            print(f"  · {p['label']:14}  {_fmt(p['value'], p['kind']):>10}")

    if data["follower_growth"]:
        g = data["follower_growth"]
        print()
        print(f"Follower growth ({g['label']}): {_fmt(g['value'], g['kind'])} "
              f"({g['delta']:+}% vs. prior)")


if __name__ == "__main__":
    main()
