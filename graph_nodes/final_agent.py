from Travel_State import TravelState
from MCP_Severs import *
from prompts import *
from llm import OpenAIConfig
from langchain_core.messages import AIMessage

import logging

logger = logging.getLogger(__name__)

llm = OpenAIConfig()


async def final_agent(state: TravelState):
    """
    Final agent that compiles the final itinerary and budget analysis.

    Args:
        state (TravelState): The current travel state containing user
            query, itinerary, and budget analysis.
    """
    logger.info("start final agent")

    if state.get("approved", False):
        review_instruction = (
            "The user approved the draft. Preserve its decisions while polishing it."
        )
    else:
        review_instruction = f"""
        The user requested a revision. Apply this feedback carefully:
        {state.get('human_feedback', '') or 'Improve the draft before finalizing it.'}
        """

    final_itinerary_prompt = final_agent_prompt.format(
        user_query=state.get("user_query", ""),
        review_instruction=review_instruction,
        itinerary=state.get("itinerary", ""),
        budget_analysis=state.get("budget_analysis", ""),
        trip_constraints=state.get("trip_constraints", {}),
        flight_results=state.get("flight_results", {}),
        hotel_results=state.get("hotel_results", {}),
        weather_results=state.get("weather_results", {}),
        budget_results=state.get("budget_results", {}),
    )

    try:
        response = await llm.generate_response(prompt=final_itinerary_prompt)

        if response is None:
            raise ValueError("Final agent LLM call returned no content")

    except Exception as exc:
        logger.error("Final Agent failed", exc_info=True)
        fallback = (
            "The final itinerary could not be generated due to an internal "
            f"error: {exc}. Please review the draft itinerary above."
        )
        return {
            "final_response": fallback,
            "messages": [AIMessage(content=fallback)],
            "llm_calls": state.get("llm_calls", 0) + 1,
        }

    return {
        "final_response": response,
        "messages": [AIMessage(content=response)],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }