from pydantic import BaseModel, Field
from typing import List, Optional
from Travel_State import TravelState
from ..MCP_Severs import *
from ..prompts  import *
from llm import OpenAIConfig
from langchain_core.messages import AIMessage 
from pydantic import BaseModel, Field
from typing import List
import asyncio


llm =OpenAIConfig()

def final_agent(state: TravelState):
    """
    Final agent that compiles the final itinerary and budget analysis.

    Args:
        state (TravelState): The current travel state containing user query, itinerary, and budget analysis.    
    """
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


    response = llm.generate_response(
        prompt=final_itinerary_prompt)


    return {
        "final_response": response,
        "messages": [response],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }




