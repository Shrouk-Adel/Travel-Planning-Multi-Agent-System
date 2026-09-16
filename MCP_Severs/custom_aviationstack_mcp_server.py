"""Custom MCP server wrapping the AviationStack REST API (free tier).

Free tier only has access to the `flights` endpoint (live/scheduled
flight status) — `airports` and `routes` return
403 function_access_restricted on this plan. So this server exposes
exactly one tool: get_flights. Airport lookup stays local via
find_main_airport / airport_data.py, not via this API.

NOTE: free tier is HTTP only — https:// throws an auth error on this plan.
"""

import json
import os

import httpx
from mcp.server.fastmcp import FastMCP
import logging

mcp = FastMCP("aviationstack")
logger = logging.getLogger(__name__)

AVIATIONSTACK_API_KEY = os.environ["AVIATIONSTACK_API_KEY"]
BASE_URL = "http://api.aviationstack.com/v1"  # http, not https — free tier requirement


async def _aviationstack_get(endpoint: str, params: dict) -> str:
    query = {k: v for k, v in params.items() if v not in (None, "")}
    query["access_key"] = AVIATIONSTACK_API_KEY

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{BASE_URL}/{endpoint}", params=query)

        logger.info("AviationStack status: %s", resp.status_code)
        logger.info("AviationStack URL: %s", resp.url)
        logger.info("AviationStack response: %s", resp.text[:2000])

        data = resp.json()

    except Exception as exc:
        return json.dumps({
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "context": f"fetching {endpoint}",
        })

    if "error" in data:
        err = data["error"]
        return json.dumps({
            "ok": False,
            "error": err.get("message", str(err)) if isinstance(err, dict) else str(err),
            "code": err.get("code") if isinstance(err, dict) else None,
            "context": f"fetching {endpoint}",
        })

    return json.dumps({
        "ok": True,
        "total": data.get("pagination", {}).get("total", 0),
        "flights": data.get("data", []),
    })


@mcp.tool()
async def get_flights(
    dep_iata: str = "",
    arr_iata: str = "",
    flight_iata: str = "",
    limit: int = 10,
) -> str:
    """Live/scheduled flight status for a route or specific flight number.
    This is the only endpoint available on the AviationStack free tier —
    it returns today's real flights with status, gates, delays, and
    scheduled/estimated/actual times. An empty `flights` list with
    `total: 0` means no flights exist for this route today, not an error.
    """
    return await _aviationstack_get(
        "flights",
        {
            "dep_iata": dep_iata,
            "arr_iata": arr_iata,
            "flight_iata": flight_iata,
            "limit": limit,
        },
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")