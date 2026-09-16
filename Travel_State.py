from typing import Any, TypedDict
from typing_extensions import Annotated
import operator
from langchain_core.messages import AnyMessage


class TravelState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], operator.add]
    user_query: str

    # Deterministic selection state (replaces old supervisor/guardrail state)
    selected_agents: list[str]
    trip_constraints: dict[str, Any]

    # Specialist results — structured dicts matching each agent's Pydantic
    # response schema, or "" on that agent's except-block fallback.
    flight_results: dict[str, Any] | str
    hotel_results: dict[str, Any] | str
    weather_results: dict[str, Any] | str
    budget_results: dict[str, Any] | str

    # The itinerary agent renders its output to markdown before storing it.
    itinerary: str

    # Human-in-the-loop state
    approval_request: str
    approved: bool
    human_feedback: str
    final_response: str

    llm_calls: int


# =========================
# Shared helpers
# =========================
# Single source of truth for agent ordering/validity.
AGENT_ORDER = [
    "flight_agent",
    "hotel_agent",
    "weather_agent",
    "budget_agent",
    "itinerary_agent",
]

KNOWN_AGENTS = set(AGENT_ORDER)


def selected_agents_in_order(state: TravelState) -> list[str]:
    selected = state.get("selected_agents", [])
    return [agent for agent in AGENT_ORDER if agent in selected]