import os
import shutil
import sys
from pathlib import Path
from typing import Any

import certifi
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient

from ..config import settings


# =========================================================
# Environment setup
# =========================================================


os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

UVX_COMMAND = shutil.which("uvx") or "uvx"

# =========================================================
# MCP server configs (dev = stdio, prod = streamable_http)
# =========================================================

def _aviation_server_config() -> dict[str, Any]:

    return {
        "transport": "stdio",
        "command": UVX_COMMAND,
        "args": [
            "aviationstack-mcp",
        ],
        "env": {
            "AVIATION_STACK_API_KEY": settings.AVIATION_STACK_API_KEY,
        },
    }


def _weather_server_config() -> dict[str, Any]:
    # if settings.WEATHER_MCP_TRANSPORT == "streamable_http":
    #     return {
    #         "transport": "streamable_http",
    #         "url": settings.WEATHER_MCP_URL,
    #     }

    return {
        "transport": "stdio",

        # Uses the Python executable from the active Conda environment.
        "command": sys.executable,

        # Uses the weather server inside the current project folder.
        "args": ["-m",
            "MCP_Severs.custom_weather_mcp_server"
        ],

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

        "aviationstack": _aviation_server_config(),

        "weather": _weather_server_config(),
    }
)


async def _get_server_tool(
    server_name: str,
    tool_name: str,
):
    """
    Load one tool from one MCP server.

    This prevents a broken weather or AviationStack server from
    crashing an unrelated Tavily request.
    """

    # Important: load only the requested MCP server.
    tools = await client.get_tools(
        server_name=server_name,
    )

    tool = next(
        (
            item
            for item in tools
            if item.name == tool_name
        ),
        None,
    )

    if tool is None:
        available_tools = (
            ", ".join(
                sorted(item.name for item in tools)
            )
            or "none"
        )

        raise RuntimeError(
            f"MCP tool '{tool_name}' was not found "
            f"on server '{server_name}'. "
            f"Available tools: {available_tools}"
        )

    return tool


# =========================================================
# MCP connection test
# =========================================================

async def get_all_tools() -> None:
    """
    Test every MCP server independently.

    One failed server will not stop the remaining tests.
    """

    for server_name in (
        "tavily",
        "aviationstack",
        "weather",
    ):
        try:
            tools = await client.get_tools(
                server_name=server_name,
            )

            tool_names = (
                ", ".join(
                    tool.name
                    for tool in tools
                )
                or "no tools"
            )

            print(
                f"{server_name}: OK -> {tool_names}"
            )

        except Exception as exc:
            print(
                f"{server_name}: FAILED -> "
                f"{type(exc).__name__}: {exc}"
            )


# =========================================================
# Tavily MCP
# =========================================================

async def tavily_mcp_search(query: str):
    search_tool = await _get_server_tool(
        "tavily",
        "tavily_search",
    )

    return await search_tool.ainvoke(
        {
            "query": query,
        }
    )


# =========================================================
# AviationStack MCP
# =========================================================

async def aviation_mcp_call(
    tool_name: str,
    tool_args: dict[str, Any] | None = None,
):
    aviation_tool = await _get_server_tool(
        "aviationstack",
        tool_name,
    )

    return await aviation_tool.ainvoke(
        tool_args or {}
    )


# =========================================================
# Weather MCP
# =========================================================

async def weather_mcp_search(city: str):
    weather_tool = await _get_server_tool(
        "weather",
        "get_current_weather",
    )

    return await weather_tool.ainvoke(
        {
            "city": city,
        }
    )


async def forecast_mcp_search(city: str):
    forecast_tool = await _get_server_tool(
        "weather",
        "get_forecast",
    )

    return await forecast_tool.ainvoke(
        {
            "city": city,
        }
    )


