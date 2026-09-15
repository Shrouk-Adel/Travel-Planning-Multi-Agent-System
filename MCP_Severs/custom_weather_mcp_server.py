import os
from pathlib import Path
from typing import Any
from config import settings

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Weather MCP Server")

REQUEST_TIMEOUT_SECONDS = 20


def _get_api_key() -> str:
    if not settings.OPENWEATHER_API_KEY:
        raise RuntimeError(
            "OPENWEATHER_API_KEY is missing from the project .env file."
        )
    return settings.OPENWEATHER_API_KEY


async def _request_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        details = exc.response.text[:500] if exc.response is not None else ""
        raise RuntimeError(f"OpenWeather request failed: {exc}. Response: {details}") from exc
    except httpx.RequestError as exc:
        raise RuntimeError(f"OpenWeather request failed: {exc}") from exc

    # OpenWeather returns HTTP 200 with a "cod" field for some errors
    # (e.g. city-not-found), so raise_for_status() alone doesn't catch it.
    cod = str(data.get("cod", "200"))
    if cod != "200":
        raise ValueError(
            f"OpenWeather error (cod={cod}): {data.get('message', 'unknown error')}"
        )

    return data


@mcp.tool()
async def get_current_weather(city: str) -> dict[str, Any]:
    """Return the current weather for a city."""
    city = city.strip()
    if not city:
        raise ValueError("city cannot be empty")

    data = await _request_json(
        "https://api.openweathermap.org/data/2.5/weather",
        {"q": city, "appid": _get_api_key(), "units": "metric"},
    )

    try:
        return {
            "city": data["name"],
            "temperature_c": data["main"]["temp"],
            "feels_like_c": data["main"]["feels_like"],
            "humidity": data["main"]["humidity"],
            "condition": data["weather"][0]["description"],
            "wind_speed": data["wind"]["speed"],
        }
    except (KeyError, IndexError) as exc:
        raise ValueError(f"Unexpected OpenWeather response shape for '{city}': {exc}") from exc


@mcp.tool()
async def get_forecast(city: str) -> dict[str, Any]:
    """Return the first five three-hour forecast entries for a city."""
    city = city.strip()
    if not city:
        raise ValueError("city cannot be empty")

    data = await _request_json(
        "https://api.openweathermap.org/data/2.5/forecast",
        {"q": city, "appid": _get_api_key(), "units": "metric"},
    )

    try:
        forecast = [
            {
                "datetime": item["dt_txt"],
                "temperature_c": item["main"]["temp"],
                "condition": item["weather"][0]["description"],
            }
            for item in data.get("list", [])[:5]
        ]
    except (KeyError, IndexError) as exc:
        raise ValueError(f"Unexpected OpenWeather forecast shape for '{city}': {exc}") from exc

    return {
        "city": data.get("city", {}).get("name", city),
        "forecast": forecast,
    }


if __name__ == "__main__":
    # mcp_client.py launches this as a stdio subprocess.
    mcp.run(transport="stdio")