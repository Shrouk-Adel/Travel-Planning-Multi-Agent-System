from typing import Any, TypedDict
from typing_extensions import Annotated
import operator
from langchain_core.messages import (
    AnyMessage,
    HumanMessage,
    AIMessage,
    SystemMessage,
)


class TravelState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], operator.add]
    user_query: str

    # Supervisor + guardrail state
    guardrail_allowed: bool
    guardrail_reason: str
    selected_agents: list[str]
    trip_constraints: dict[str, Any]
    supervisor_reasoning: str

    # Specialist results — these are structured dicts matching each
    # agent's Pydantic response schema (e.g. FlightAgentResponse), not
    # plain strings. The "" case comes from an agent's except-block
    # fallback when it fails.
    flight_results: dict[str, Any] | str
    hotel_results: dict[str, Any] | str
    weather_results: dict[str, Any] | str
    budget_results: dict[str, Any] | str

    # The itinerary agent renders its output to markdown before storing
    # it here, so this one genuinely is a string (see Itinerary_Agent.py).
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
# Single source of truth for agent ordering/validity. Import this
# wherever it's needed (e.g. Super_Agent_and_guardrail_Agent.py,
# graph.py) instead of redefining it — two independent copies can
# silently drift out of sync.
AGENT_ORDER = [
    "flight_agent",
    "hotel_agent",
    "weather_agent",
    "budget_agent",
    "itinerary_agent",
]

KNOWN_AGENTS = set(AGENT_ORDER)