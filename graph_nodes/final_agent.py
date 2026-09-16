from Travel_State import TravelState
from MCP_Severs import *
from prompts import *
from llm import OpenAIConfig
from langchain_core.messages import AIMessage

import logging

logger = logging.getLogger(__name__)

llm = OpenAIConfig()


from Travel_State import TravelState
from prompts import final_agent_prompt
from llm import OpenAIConfig
from langchain_core.messages import AIMessage

import logging

logger = logging.getLogger(__name__)

llm = OpenAIConfig()


async def final_agent(state: TravelState):
    """
    Final agent that compiles the final itinerary and budget analysis.
    """

    logger.info("Start Final Agent")

    # --------------------------------
    # 1. Determine review instruction
    # --------------------------------
    if state.get("approved", False):

        review_instruction = (
            "The user approved the draft. "
            "Preserve the itinerary, hotel, flights, and budget decisions. "
            "Only polish the presentation and make the final response clear."
        )

    else:

        review_instruction = f"""
The user requested a revision.

Apply the following feedback carefully:

{state.get("human_feedback", "") or "Improve the draft before finalizing it."}

Preserve valid information from the existing draft.
Do not invent flights, hotels, prices, weather information, or costs.
"""

    # --------------------------------
    # 2. Build final prompt
    # --------------------------------
    final_itinerary_prompt = final_agent_prompt.format(
        review_instruction=review_instruction,
        itinerary=state.get("itinerary", ""),
        trip_constraints=state.get("trip_constraints", {}),
        flight_results=state.get("flight_results", {}),
        hotel_results=state.get("hotel_results", {}),
        weather_results=state.get("weather_results", {}),
        budget_results=state.get("budget_results", {}),
    )

    # --------------------------------
    # 3. Call LLM
    # --------------------------------
    try:

        response = await llm.generate_text_response(
            prompt=final_itinerary_prompt,
        )

        if not response:
            raise ValueError(
                "Final Agent LLM call returned no content"
            )

    except Exception as exc:

        logger.error(
            "Final Agent failed",
            exc_info=True
        )

        fallback = (
            "The final itinerary could not be generated due to an "
            "internal error. Please review the draft itinerary."
        )

        return {
            "final_response": fallback,
            "messages": [
                AIMessage(content=fallback)
            ],
            "llm_calls": state.get("llm_calls", 0) + 1,
        }

    # --------------------------------
    # 4. Return final response
    # --------------------------------
    return {
        "final_response": response,
        "messages": [
            AIMessage(content=response)
        ],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }