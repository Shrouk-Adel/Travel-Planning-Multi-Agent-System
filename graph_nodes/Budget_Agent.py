from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

from Travel_State import TravelState
from MCP_Severs import *
from prompts import *
from llm import OpenAIConfig
from langchain_core.messages import AIMessage

import logging

logger = logging.getLogger(__name__)

class BudgetAgentResponse(BaseModel):
    overall_feasibility: str
    feasibility_reason: str
    estimated_total: Optional[float] = None
    currency: Optional[str] = None
    budget_remaining: Optional[float] = None

openai = OpenAIConfig()


async def Budget_Agent(state: TravelState):

    logger.info("Start Budget Agent")

    constraints = state.get("trip_constraints", {})

    budget = constraints.get("budget")
    currency = constraints.get("currency")
    flight_results = state.get("flight_results", {})
    hotel_results = state.get("hotel_results", {})
    itinerary = state.get("itinerary", "")

    prompt = f"""
    Analyze the trip budget.

    Budget: {budget} {currency or ""}
    Flights: {flight_results}
    Hotels: {hotel_results}
    Activities: {itinerary}

    Return:
    - overall_feasibility
    - feasibility_reason
    - estimated_total
    - currency
    - budget_remaining

    Keep the answer short.
    """

    try:
        response = await openai.generate_response(
            prompt=prompt,
            pydantic_schema=BudgetAgentResponse
        )

        return {
            "budget_results": response,
            "messages": [
                AIMessage(content="Budget analysis completed.")
            ],
            "llm_calls": state.get("llm_calls", 0) + 1
        }

    except Exception as exc:

        logger.error("Budget Agent failed", exc_info=True)

        return {
            "budget_results": {
                "overall_feasibility": "unknown",
                "feasibility_reason": "Budget analysis unavailable."
            },
            "messages": [
                AIMessage(content="Budget Agent failed.")
            ],
            "llm_calls": state.get("llm_calls", 0) + 1
        }