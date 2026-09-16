from Travel_State import TravelState
from MCP_Severs import *
from prompts  import *
from llm import OpenAIConfig
from langchain_core.messages import AIMessage 
from pydantic import BaseModel, Field
from typing import List
import asyncio
from .dest_extractor import extract_destination
import asyncio


from pydantic import BaseModel, Field
from typing import List, Optional

import logging

logger =logging.getLogger(__name__)

async def Weather_Agent(state: TravelState):

    logger.info("Start Weather Agent")

    destination = state.get(
        "trip_constraints", {}
    ).get("destination", "")

    if not destination:
        return {
            "weather_results": "Destination is missing."
        }

    try:

        weather_data = await weather_mcp_search(destination)
        forecast_data = await forecast_mcp_search(destination)

        weather_results = {
            "current": weather_data,
            "forecast": forecast_data
        }

        return {
            "weather_results": weather_results,
            "messages": [
                AIMessage(content="Weather information retrieved.")
            ]
        }

    except Exception as exc:

        logger.error("Weather Agent failed", exc_info=True)

        return {
            "weather_results": {
                "status": "unavailable"
            },
            "messages": [
                AIMessage(content="Weather search failed.")
            ]
        }