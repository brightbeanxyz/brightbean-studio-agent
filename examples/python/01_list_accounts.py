"""List the social accounts this API key may target.

Always run this in a fresh session — it tells you what
``social_account_id`` values the rest of the API will accept.
"""

import json

from client import BrightbeanClient


def main() -> None:
    bb = BrightbeanClient()
    r = bb.get("/accounts/")
    r.raise_for_status()
    accounts = r.json()["accounts"]
    print(f"Allowlisted accounts ({len(accounts)}):")
    for a in accounts:
        print(
            f"  - {a['id']}  {a['platform']:20}  {a['account_name']:30}  "
            f"status={a['connection_status']}"
        )
    # And the full /me/ payload — useful to confirm permissions.
    me = bb.get("/me/").json()
    print()
    print("Workspace:", me["workspace_name"], "/", me["workspace_id"])
    print("Permissions:", ", ".join(me["permissions"]) or "(none)")


if __name__ == "__main__":
    main()
