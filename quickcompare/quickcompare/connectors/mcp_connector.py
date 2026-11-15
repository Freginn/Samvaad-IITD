"""Adapter for the official Swiggy (Food / Instamart / Dineout) and Zomato MCP servers.

These servers are the only sanctioned way for a third-party app to search,
build carts and place orders on those platforms. Access is gated (Swiggy
Builders Club, Zomato's access form) and uses OAuth with the user's own
account, so this adapter needs:

  * an approved client and an OAuth access token for the user, in the env var
    named by `mcp.token_env` (the OAuth flow itself is done outside this app,
    per the provider's docs), and
  * the server's real tool names, set under `mcp.tools` in platforms.yaml.
    Tool names are NOT hard-coded here: run `python -m quickcompare.connectors.mcp_connector <url>`
    to list the tools the server actually exposes and fill them in.

Not tested against live servers: it needs approved access this repo doesn't have.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any, Optional

from ..models import Listing
from .base import Connector, OrderResult

DEFAULT_URLS = {
    "swiggy_mcp": "https://mcp.swiggy.com/im",       # Instamart; /food and /dineout also exist
    "zomato_mcp": "https://mcp-server.zomato.com/mcp",
}


async def _with_session(url: str, token: Optional[str], fn):
    import httpx
    from mcp import ClientSession
    try:
        from mcp.client.streamable_http import streamable_http_client as _client
    except ImportError:  # older SDKs
        from mcp.client.streamable_http import streamablehttp_client as _client  # type: ignore

    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        ctx = _client(url, http_client=httpx.AsyncClient(headers=headers, timeout=30))
    except TypeError:
        ctx = _client(url, headers=headers)  # type: ignore[call-arg]
    async with ctx as streams:
        read, write = streams[0], streams[1]
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await fn(session)


def _payload(result: Any) -> Any:
    """Pull structured data (or JSON text) out of a CallToolResult."""
    structured = getattr(result, "structuredContent", None) or getattr(result, "structured_content", None)
    if structured:
        return structured
    for block in getattr(result, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text
    return None


class MCPConnector(Connector):
    can_order = True

    def __init__(self, name: str, cfg: dict, kind: str):
        super().__init__(name, cfg)
        m = cfg.get("mcp", {})
        self.url = m.get("url", DEFAULT_URLS[kind])
        self.token = os.environ.get(m.get("token_env", f"{name.upper()}_MCP_TOKEN"))
        self.tools: dict[str, str] = m.get("tools", {})
        # Field names in the server's search results (adjust per server).
        self.fields: dict[str, str] = {"items": "items", "id": "id", "title": "name", "price": "price",
                                       "mrp": "mrp", "available": "in_stock", **m.get("fields", {})}

    def _tool(self, role: str) -> str:
        if role not in self.tools:
            raise RuntimeError(f"{self.name}: set mcp.tools.{role} in platforms.yaml "
                               f"(list tools with: python -m quickcompare.connectors.mcp_connector {self.url})")
        return self.tools[role]

    def _call(self, role: str, args: dict) -> Any:
        tool = self._tool(role)

        async def run(session):
            return _payload(await session.call_tool(tool, args))
        return asyncio.run(_with_session(self.url, self.token, run))

    def search(self, query: str, location: Optional[str] = None) -> list[Listing]:
        args = {"query": query}
        if location:
            args["location"] = location
        data = self._call("search", args)
        rows = data.get(self.fields["items"], []) if isinstance(data, dict) else (data or [])
        f = self.fields
        out = []
        for r in rows:
            if not isinstance(r, dict) or r.get(f["price"]) is None:
                continue
            out.append(Listing(platform=self.name, query=query, title=str(r.get(f["title"], query)),
                               unit_price=float(r[f["price"]]),
                               mrp=float(r[f["mrp"]]) if r.get(f["mrp"]) else None,
                               available=bool(r.get(f["available"], True)),
                               product_id=str(r.get(f["id"])) if r.get(f["id"]) is not None else None))
        return out

    def place_order(self, lines: list[tuple[Listing, int]], payment_method: str,
                    coupon: Optional[str] = None) -> OrderResult:
        """Builds the cart and checks out. The UI must get explicit user confirmation first."""
        for listing, qty in lines:
            self._call("add_to_cart", {"item_id": listing.product_id, "quantity": qty})
        if coupon and "apply_coupon" in self.tools:
            self._call("apply_coupon", {"code": coupon})
        res = self._call("checkout", {"payment_method": payment_method})
        order_id = res.get("order_id") if isinstance(res, dict) else None
        pay_url = res.get("payment_url") if isinstance(res, dict) else None
        return OrderResult(placed=order_id is not None, order_id=order_id, open_url=pay_url,
                           message=f"{self.cfg.get('label', self.name)}: {res}")


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URLS["swiggy_mcp"]

    async def show(session):
        for t in (await session.list_tools()).tools:
            print(f"{t.name}: {(t.description or '').splitlines()[0] if t.description else ''}")
    asyncio.run(_with_session(url, os.environ.get("MCP_TOKEN"), show))
