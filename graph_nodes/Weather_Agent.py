from Travel_State import TravelState
from ..MCP_Severs import *
from ..prompts  import *
from llm import OpenAIConfig
from langchain_core.messages import AIMessage 
from pydantic import BaseModel, Field
from typing import List
import asyncio
from dest_extractor import extract_destination


from pydantic import BaseModel, Field
from typing import List, Optional

def Weather_Agent(state: TravelState):
    """
    Weather Agent that retrieves weather information based on the user's travel request.
    
    Args:
        state (TravelState): The current state of travel.
        
    Returns:
        dict: A dictionary containing weather results and updated messages.
    """ 
    query = state['user_query']

    city =extract_destination(state['user_query'])
    
    try:
        weather_data = asyncio.run(
            tavily_mcp_search(city)
        )

        forcast_data =asyncio.run(
            forecast_mcp_search(city)
        )

        weather_results =f"""
            Current Weather:
            {weather_data}

            Forecast:
            {forcast_data}
        """

    except Exception as exc:
        print(
            f"WEATHER AGENT MCP ERROR: "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )

        weather_results = (
            f"Live weather information for {city} "
            "is temporarily unavailable. Give general "
            "seasonal guidance and advise the traveler "
            "to verify the forecast before departure."
        )

    return {
        "weather_results": weather_results,
        "messages": [
            AIMessage(
                content="Weather information processed."
            )
        ],
    }