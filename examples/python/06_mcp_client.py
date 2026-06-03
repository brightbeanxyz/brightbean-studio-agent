"""Minimal MCP-over-HTTP client — no SDK required.

The Brightbean Studio MCP transport is plain JSON-RPC over POST. You can
talk to it with ``requests`` directly: same bearer token as the REST
API, same endpoint host, but ``/api/v1/mcp/`` instead of ``/api/v1/posts/``.

This example mirrors ``01_list_accounts.py`` and ``02_create_draft.py``
via the MCP tool surface so you can compare side by side.
"""

import json
import os
import uuid

import requests

BASE = os.environ.get("BRIGHTBEAN_BASE_URL", "").rstrip("/")
TOKEN = os.environ.get("BRIGHTBEAN_TOKEN", "")
if not BASE or not TOKEN:
    raise SystemExit("Set BRIGHTBEAN_BASE_URL and BRIGHTBEAN_TOKEN first.")

ENDPOINT = f"{BASE}/api/v1/mcp/"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}


def call(method: str, params: dict | None = None) -> dict:
    msg = {"jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": method}
    if params is not None:
        msg["params"] = params
    r = requests.post(ENDPOINT, headers=HEADERS, json=msg, timeout=10)
    r.raise_for_status()
    body = r.json()
    if "error" in body:
        raise RuntimeError(f"MCP {method} failed: {body['error']}")
    return body["result"]


def call_tool(name: str, arguments: dict) -> dict:
    """``tools/call`` wrapper that unwraps the ``content[0].text`` envelope.

    Brightbean's tools return their structured payload as
    ``{"content": [{"type": "text", "text": "<json>"}], "isError": false}``
    so this helper json-parses the text back into a dict for callers.
    """
    result = call("tools/call", {"name": name, "arguments": arguments})
    if result.get("isError"):
        raise RuntimeError(f"tool {name} returned isError=True: {result}")
    text_block = next(c for c in result["content"] if c["type"] == "text")
    return json.loads(text_block["text"])


def main() -> None:
    print("=== initialize ===")
    init = call(
        "initialize",
        {"protocolVersion": "2025-03-26", "capabilities": {}},
    )
    print(json.dumps(init, indent=2))

    print("\n=== tools/list ===")
    tools = call("tools/list")
    for t in tools["tools"]:
        print(f"  - {t['name']}: {t['description'][:80]}")

    print("\n=== list_accounts ===")
    accounts = call_tool("list_accounts", {})
    for a in accounts["accounts"]:
        print(f"  - {a['id']}  {a['platform']:20}  {a['account_name']}")

    if accounts["accounts"]:
        sa_id = accounts["accounts"][0]["id"]
        print(f"\n=== create_draft against {sa_id} ===")
        draft = call_tool(
            "create_draft",
            {"social_account_id": sa_id, "caption": "Drafted via MCP."},
        )
        print(f"  draft Post id: {draft['id']}")
        print(f"  status: {draft['platform_posts'][0]['status']}")

        # Analytics tools — read-only, require view_analytics. If the key
        # doesn't hold the permission, these blocks surface a clear
        # "Permission denied" error rather than corrupting state.
        print(f"\n=== get_account_analytics for {sa_id} (days=30) ===")
        try:
            channel = call_tool(
                "get_account_analytics",
                {"account_id": sa_id, "days": 30},
            )
        except RuntimeError as exc:
            print(f"  (skipped: {exc})")
        else:
            if not channel["analytics_available"]:
                print(f"  analytics_available=false: {channel['unavailable_reason']}")
            else:
                print(f"  hero_metrics: {len(channel['hero_metrics'])}")
                for m in channel["hero_metrics"][:3]:
                    print(f"    - {m['key']:14}  value={m['value']}  delta={m['delta']}%")
                print(f"  captured_at:    {channel['captured_at']}")
                print(f"  next_sync_eta:  {channel['next_sync_eta']}")

        # The just-created draft has no analytics yet — but the tool
        # responds with a valid empty envelope so the polling loop in
        # 09_post_then_poll.py can start from day zero.
        print(f"\n=== get_post_analytics for the draft above ===")
        try:
            perf = call_tool("get_post_analytics", {"post_id": draft["id"]})
        except RuntimeError as exc:
            print(f"  (skipped: {exc})")
        else:
            child = perf["platform_posts"][0]
            print(f"  child status: {child['status']}")
            print(f"  analytics_available: {child['analytics_available']}")
            print(f"  metric_tiles: {len(child['metric_tiles'])}  (empty until publish)")


if __name__ == "__main__":
    main()
