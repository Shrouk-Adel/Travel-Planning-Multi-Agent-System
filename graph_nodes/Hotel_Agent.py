from Travel_State import TravelState
from MCP_Severs import *
from prompts import *
from llm import OpenAIConfig
from langchain_core.messages import AIMessage
from typing import List, Optional
from pydantic import BaseModel

import json
import logging

logger = logging.getLogger(__name__)


class Hotel(BaseModel):
    name: str
    location: str
    price: Optional[str] = None
    rating: Optional[float] = None


class HotelAgentResponse(BaseModel):
    destination: str
    search_status: str
    hotels: List[Hotel] = []


# =========================
# Hotel Agent
# =========================

openai = OpenAIConfig()

MAX_RESULTS = 5        # how many search hits to keep
MAX_CONTENT_LEN = 500  # chars kept per hit's scraped content


def _condense_tavily_results(raw_results, max_results=MAX_RESULTS, max_content_len=MAX_CONTENT_LEN):
    """
    Tavily MCP returns [{'type': 'text', 'text': '<json string>', 'id': ...}].
    The JSON string's 'results' list has full scraped 'content' per hit,
    which is what blows up the prompt. Keep only title + a trimmed
    content snippet per hit, and cap how many hits we forward.
    Falls back to str(raw_results)[:2000] if the shape is unexpected.
    """
    try:
        payload = json.loads(raw_results[0]["text"])
        results = payload.get("results", [])[:max_results]

        condensed = []
        for r in results:
            content = (r.get("content") or "").strip()
            if len(content) > max_content_len:
                content = content[:max_content_len] + "..."
            condensed.append({
                "title": r.get("title", ""),
                "content": content,
            })
        return json.dumps(condensed, ensure_ascii=False)

    except Exception as exc:
        logger.warning(f"Could not condense tavily results, falling back to raw slice: {exc}")
        return str(raw_results)[:2000]


async def hotel_agent(state: TravelState):
    """
    Hotel Agent that retrieves hotel information based on the user's travel request.

    Args:
        state (TravelState): The current state of travel.

    Returns:
        dict: A dictionary containing hotel results and updated messages.
    """
    trip_constraints = state["trip_constraints"]
    destination = trip_constraints["destination"]

    query = f"Best hotels for {destination} and its price "

    try:
        logger.info("start hotel agent")
        raw_results = await tavily_mcp_search(query)

        logger.info(f"hotel_results raw:\n:{raw_results}")

        condensed_results = _condense_tavily_results(raw_results)
        logger.info(f"hotel_results condensed ({len(condensed_results)} chars):\n:{condensed_results}")

        hotel_results = await openai.generate_response(
            prompt=HOTEL_AGENT_PROMPT.format(
                query=query,
                hotel_results=condensed_results
            ),
            pydantic_schema=HotelAgentResponse
        )

        logger.info(f"generated result for hotels from llm :\n{hotel_results}")

    except Exception as exc:
        print(
            f"HOTEL AGENT MCP ERROR: "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )

        hotel_results = (
            "Live hotel search is temporarily unavailable. "
            "Provide general accommodation and neighborhood "
            "guidance based on the destination and clearly "
            "label it as non-live advice."
        )

    return {
        "hotel_results": hotel_results,
        "messages": [
            AIMessage(
                content="Hotel information processed."
            )
        ],
        "llm_calls": (
            state.get("llm_calls", 0) + 1
        ),
    }