from typing import Any

from Travel_State import TravelState, AGENT_ORDER, KNOWN_AGENTS
from prompts import guardrail_prompt, supervisor_prompt
from pydantic import BaseModel, Field
from llm.OpenAI import OpenAIConfig
import logging
from langchain_core.messages import AIMessage
openai_config = OpenAIConfig()

logger = logging.getLogger(__name__)


class guardrail_schema(BaseModel):
    allowed: bool = Field(description="Indicates whether the user request is allowed or blocked")
    reason: str = Field(description="Reason for allowing or blocking the user request")


class supervisor_schema(BaseModel):
    selected_agents: list[str] = Field(description="List of selected agents for the travel request")
    trip_constraints: dict = Field(description="Constraints for the travel request, including destination, origin, duration, budget, travel style, and special preferences")
    reasoning: str = Field(description="Reasoning behind the selection of agents and trip constraints")


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


async def Supervisor_Agent(state: TravelState):
    """
    Supervisor Agent that makes decisions based on the current travel state.

    Args:
        state (TravelState): The current state of travel.

    Returns:
        str: The decision made by the supervisor agent.
    """
    logger.info("start with guardrail Agent")
    user_query = state.get('user_query')  # Access the user query from the travel state
    llm_calls = state.get('llm_calls', 0)  # Access the LLM calls from the travel state

    try:
        # start with gurdrail agent to check if the request is valid
        logger.info(f"user query is :{user_query}")
        prompt = guardrail_prompt.format(query=user_query)
        # logger.info(f"guardrail prompt is\n:{prompt}")
        guardrail_response = await openai_config.generate_response(
            prompt=prompt,
            pydantic_schema=guardrail_schema
        )

        logger.info(f"guardrail response :{guardrail_response}")

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
        logger.info("start supervisor agent")
        supervisor_response = await openai_config.generate_response(
            prompt=supervisor_prompt.format(query=user_query),
            pydantic_schema=supervisor_schema
        )
        logger.info(f"supervisor response is :{supervisor_response}")
        # Validate against KNOWN_AGENTS before normalizing into AGENT_ORDER,
        # so a hallucinated/misspelled agent name from the LLM is dropped
        # here with a log line instead of silently disappearing later.
        raw_agents = supervisor_response.get('selected_agents', [])
        normalized_agents = [normalize_agent_name(agent) for agent in raw_agents]

        unknown = [a for a in normalized_agents if a not in KNOWN_AGENTS]
        if unknown:
            logger.warning(f"Supervisor selected unrecognized agents, dropping: {unknown}")

        selected_agents = [
            agent
            for agent in AGENT_ORDER
            if agent in normalized_agents
        ]

        logger.info(f"selected agents:{selected_agents}")
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