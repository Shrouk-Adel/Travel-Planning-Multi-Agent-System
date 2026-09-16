"""Deterministic replacement for the old LLM-based Supervisor_Agent.

The UI form guarantees well-formed structured input (origin, destination,
dates, budget, interests, etc.), so there is nothing left to "guess" —
this just maps that input onto TravelState. No LLM call, no parsing
failure mode.
"""

from langchain_core.messages import HumanMessage
from Travel_State import AGENT_ORDER, TravelState

# Map UI interest checkboxes -> optional specialist agents.
# Only agents that make sense as "opt in" belong here. Weather and budget
# are treated as always-on below since they're cheap and generally useful
# whenever there's a destination/date and a budget on the form.
INTEREST_AGENT_MAP = {
    "flights": "flight_agent",
    "hotels": "hotel_agent",
}

ALWAYS_ON_AGENTS = ["weather_agent", "budget_agent"]

MAX_FREE_TEXT_LEN = 1000


def sanitize_free_text(text: str | None) -> str:
    """Cheap, non-LLM guard on the one free-text field the UI exposes.
    Not a security boundary by itself — just keeps obviously bad input
    (huge blobs, control chars) out of prompts. Escalate to a real
    moderation/guardrail call only if you add an unstructured entry
    point elsewhere (e.g. a chat box)."""
    if not text:
        return ""
    text = text.strip()[:MAX_FREE_TEXT_LEN]
    return "".join(ch for ch in text if ch.isprintable() or ch in "\n\t")


def build_initial_state(
    *,
    origin: str,
    destination: str,
    date: str,
    duration: int,
    budget: float,
    currency: str,
    num_travelers: int,
    interests: list[str] | None = None,
    message: str | None = None,
) -> TravelState:
    interests = interests or []
    interests_lower = {i.strip().lower() for i in interests}

    trip_constraints = {
        "origin": origin,
        "destination": destination,
        "start_date": date,
        "duration": duration,
        "budget": budget,
        "currency": currency,
        "num_travelers": num_travelers,
        "special_preferences": sorted(interests_lower),
    }

    selected = {
        agent
        for key, agent in INTEREST_AGENT_MAP.items()
        if key in interests_lower
    }
    selected.update(ALWAYS_ON_AGENTS)
    selected.add("itinerary_agent")

    selected_agents = [agent for agent in AGENT_ORDER if agent in selected]

    free_text = sanitize_free_text(message)
    user_query = free_text or (
        f"Trip from {origin} to {destination}, {duration} days starting "
        f"{date}, {num_travelers} traveler(s), budget {budget} {currency}."
    )
    if free_text and free_text != user_query:
        # Free text supplements rather than replaces the structured summary,
        # so downstream prompts still see origin/destination/etc. in prose.
        user_query = (
            f"Trip from {origin} to {destination}, {duration} days starting "
            f"{date}, {num_travelers} traveler(s), budget {budget} {currency}. "
            f"Additional notes: {free_text}"
        )

    return {
        "messages": [HumanMessage(content=user_query)],
        "user_query": user_query,
        "selected_agents": selected_agents,
        "trip_constraints": trip_constraints,
        "flight_results": "",
        "hotel_results": "",
        "weather_results": "",
        "budget_results": "",
        "itinerary": "",
        "approval_request": "",
        "approved": False,
        "human_feedback": "",
        "final_response": "",
        "llm_calls": 0,
    }