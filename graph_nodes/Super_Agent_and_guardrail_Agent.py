from transformers import Any

from ..Travel_State import TravelState
from prompts import guardrail_prompt, guardrail_prompt_sys, supervisor_prompt, supervisor_prompt_sys
from pydantic import BaseModel, Field
from ..llm.OpenAI import OpenAIConfig
from langchain_core.messages import AIMessage
openai_config = OpenAIConfig()

class guardrail_schema(BaseModel):
    allowed: bool =Field(description="Indicates whether the user request is allowed or blocked")
    reason: str =Field(description="Reason for allowing or blocking the user request")

class supervisor_schema(BaseModel):
    selected_agents: list[str] =Field(description="List of selected agents for the travel request")
    trip_constraints: dict =Field(description="Constraints for the travel request, including destination, origin, duration, budget, travel style, and special preferences")
    reasoning: str =Field(description="Reasoning behind the selection of agents and trip constraints")


AGENT_ORDER = [
    "flight_agent",
    "hotel_agent",
    "weather_agent",
    "budget_agent",
    "itinerary_agent",
]
    
def _empty_constraints() -> dict[str, Any]:
    return {
        "destination": "",
        "origin": "",
        "duration": "",
        "budget": "",
        "travel_style": "",
        "special_preferences": [],
    }

def normalize_agent_name(name: str) -> str:
    return str(name).strip().lower().replace(" ", "_")


def Supervisor_Agent(state: TravelState):
    """
    Supervisor Agent that makes decisions based on the current travel state.
    
    Args:
        state (TravelState): The current state of travel.
        
    Returns:
        str: The decision made by the supervisor agent.
    """
    user_query =state.get('user_query')  # Access the user query from the travel state
    llm_calls = state.get('llm_calls',0)  # Access the LLM calls from the travel state

    try:
        # start with gurdrail agent to check if the request is valid
        guardrail_response = openai_config.generate_response(
            user_prompt=guardrail_prompt.format(query=user_query),
            system_prompt=guardrail_prompt_sys,
            pydantic_schema=guardrail_schema
        )

        allowed = guardrail_response.get('allowed', False)
        reason = guardrail_response.get('reason', '').strip()
        llm_calls += 1

    except Exception as e:
        allowed = False
        reason = f"Guardrail agent failed with error: {str(e)}"
        llm_calls += 1

    if not allowed:
        reason = reason or (
            "TripMate AI can only help with travel-planning requests. "
            "Please ask about a destination, flight, hotel, weather, budget, "
            "or itinerary."
        )


        return {
            "guardrail_allowed": False,
            "guardrail_reason": reason,
            "selected_agents": [],
            "trip_constraints": _empty_constraints(),
            "supervisor_reasoning": reason,
            "final_response": reason,
            "messages": [AIMessage(content=f"Guardrail blocked request: {reason}")],
            "llm_calls": llm_calls,
        }

    try:
        supervisor_response = openai_config.generate_response(
            user_prompt=supervisor_prompt.format(query=user_query),
            system_prompt=supervisor_prompt_sys,
            pydantic_schema=supervisor_schema
        )

        normalized_agents = [normalize_agent_name(agent) for agent in supervisor_response.get('selected_agents', [])]

        selected_agents = [
            agent
            for agent in AGENT_ORDER
            if agent in normalized_agents
        ]
        trip_constraints = supervisor_response.get('trip_constraints', _empty_constraints())
        reasoning = supervisor_response.get('reasoning', '').strip()

        # The itinerary agent integrates whichever specialist results were selected.
        if "itinerary_agent" not in selected_agents:
            selected_agents.append("itinerary_agent")

        constraints = _empty_constraints()
        if isinstance(trip_constraints, dict):
            constraints.update(trip_constraints)

        llm_calls += 1
    except Exception as e:
        print(f"Supervisor fallback used: {e}")
        # Original workflow behavior is preserved as the fallback.
        selected_agents = AGENT_ORDER.copy()
        constraints = _empty_constraints()
        reasoning = (
            "Supervisor parsing failed, so the original full travel workflow "
            "was selected as a safe fallback."
        )

    return {
        "guardrail_allowed": True,
        "guardrail_reason": reason,
        "selected_agents": selected_agents,
        "trip_constraints": constraints,
        "supervisor_reasoning": reasoning,
        "messages": [AIMessage(content=f"Supervisor selected agents: {selected_agents}")],
        "llm_calls": llm_calls,
    }


def guardrail_blocked_agent(state: TravelState):

    reason = (
        state.get("final_response")
        or state.get("guardrail_reason")
        or "This request was blocked by the travel input guardrail."
    )

    return {
        "guardrail_allowed": False,
        "guardrail_reason": reason,
        "messages": [AIMessage(content=reason)],
    }