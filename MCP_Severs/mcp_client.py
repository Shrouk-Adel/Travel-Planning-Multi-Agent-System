import os
import sys
from pathlib import Path
from typing import Any

import certifi
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient

from config import settings


# =========================================================
# Environment setup
# =========================================================

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

# =========================================================
# MCP server configs
# =========================================================

def _aviation_server_config() -> dict[str, Any]:
    return {
        "transport": "stdio",
        "command": sys.executable,
        "args": ["-m", "MCP_Severs.custom_aviationstack_mcp_server"],
        "env": {
            "AVIATIONSTACK_API_KEY": settings.AVIATIONSTACK_API_KEY,
        },
    }


def _weather_server_config() -> dict[str, Any]:
    return {
        "transport": "stdio",
        "command": sys.executable,
        "args": ["-m", "MCP_Severs.custom_weather_mcp_server"],
        "env": {
            "OPENWEATHER_API_KEY": settings.OPENWEATHER_API_KEY,
        },
    }


# =========================================================
# MCP client
# =========================================================

client = MultiServerMCPClient(
    {
        "tavily": {
            "transport": "streamable_http",
            "url": (
                "https://mcp.tavily.com/mcp/"
                f"?tavilyApiKey={settings.TAVILY_API_KEY}"
            ),
        },
        "aviationstack": _aviation_server_config(),  # kept as key name for compatibility
        "weather": _weather_server_config(),
    }
)


async def _get_server_tool(server_name: str, tool_name: str):
    tools = await client.get_tools(server_name=server_name)
    tool = next((item for item in tools if item.name == tool_name), None)

    if tool is None:
        available_tools = ", ".join(sorted(item.name for item in tools)) or "none"
        raise RuntimeError(
            f"MCP tool '{tool_name}' was not found on server '{server_name}'. "
            f"Available tools: {available_tools}"
        )

    return tool


async def get_all_tools() -> None:
    for server_name in ("tavily", "aviationstack", "weather"):
        try:
            tools = await client.get_tools(server_name=server_name)
            tool_names = ", ".join(tool.name for tool in tools) or "no tools"
            print(f"{server_name}: OK -> {tool_names}")
        except Exception as exc:
            print(f"{server_name}: FAILED -> {type(exc).__name__}: {exc}")


async def tavily_mcp_search(query: str):
    search_tool = await _get_server_tool("tavily", "tavily_search")
    return await search_tool.ainvoke({"query": query})


async def aviation_mcp_call(tool_name: str, tool_args: dict[str, Any] | None = None):
    aviation_tool = await _get_server_tool("aviationstack", tool_name)
    return await aviation_tool.ainvoke(tool_args or {})


async def weather_mcp_search(city: str):
    weather_tool = await _get_server_tool("weather", "get_current_weather")
    return await weather_tool.ainvoke({"city": city})


async def forecast_mcp_search(city: str):
    forecast_tool = await _get_server_tool("weather", "get_forecast")
    return await forecast_tool.ainvoke({"city": city})