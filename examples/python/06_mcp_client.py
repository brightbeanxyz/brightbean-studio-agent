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


if __name__ == "__main__":
    main()
