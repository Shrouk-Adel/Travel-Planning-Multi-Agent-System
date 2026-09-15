from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional
from Travel_State import TravelState
from MCP_Severs import *
from prompts import *
from llm import OpenAIConfig
from langchain_core.messages import AIMessage

import logging

logger = logging.getLogger(__name__)


class ItineraryActivity(BaseModel):
    time: Optional[str] = Field(
        default=None,
        description="Suggested time for the activity, e.g. '09:00 AM'"
    )

    activity: str = Field(
        description="Name or description of the activity"
    )

    location: Optional[str] = Field(
        default=None,
        description="Location or attraction"
    )

    duration: Optional[str] = Field(
        default=None,
        description="Expected duration, e.g. '2 hours'"
    )

    estimated_cost: Optional[float] = Field(
        default=None,
        description="Estimated cost of the activity"
    )

    currency: Optional[str] = Field(
        default=None,
        description="Currency of the estimated cost"
    )

    notes: Optional[str] = Field(
        default=None,
        description="Additional practical information"
    )


class ItineraryDay(BaseModel):
    day: int = Field(
        description="Day number starting from 1"
    )

    date: Optional[str] = Field(
        default=None,
        description="Calendar date if available"
    )

    title: Optional[str] = Field(
        default=None,
        description="Short title describing the day's plan"
    )

    activities: List[ItineraryActivity] = Field(
        default_factory=list,
        description="Activities planned for this day"
    )

    daily_estimated_cost: Optional[float] = Field(
        default=None,
        description="Estimated total cost for this day"
    )

    currency: Optional[str] = Field(
        default=None,
        description="Currency used for daily estimated cost"
    )


class TransportationSegment(BaseModel):
    from_location: str = Field(
        description="Starting location"
    )

    to_location: str = Field(
        description="Destination location"
    )

    mode: str = Field(
        description="Transportation method, e.g. metro, taxi, bus, walking"
    )

    estimated_duration: Optional[str] = Field(
        default=None,
        description="Estimated travel duration"
    )

    estimated_cost: Optional[float] = Field(
        default=None,
        description="Estimated transportation cost"
    )

    currency: Optional[str] = Field(
        default=None,
        description="Currency of the estimated cost"
    )


class ItineraryAgentResponse(BaseModel):
    destination: str = Field(
        description="Main destination of the trip"
    )

    trip_duration: Optional[str] = Field(
        default=None,
        description="Trip duration, e.g. '5 days'"
    )

    itinerary: List[ItineraryDay] = Field(
        default_factory=list,
        description="Day-by-day travel itinerary"
    )

    transportation: List[TransportationSegment] = Field(
        default_factory=list,
        description="Important transportation segments between activities"
    )

    total_estimated_cost: Optional[float] = Field(
        default=None,
        description="Estimated total cost of activities and transportation"
    )

    currency: Optional[str] = Field(
        default=None,
        description="Primary currency used for the cost estimates"
    )

    budget_status: Optional[str] = Field(
        default=None,
        description=(
            "Whether the itinerary is within budget, "
            "near budget, or exceeds budget"
        )
    )

    practical_notes: List[str] = Field(
        default_factory=list,
        description="Important practical notes for the traveler"
    )

    assumptions: List[str] = Field(
        default_factory=list,
        description="Assumptions made when information was unavailable"
    )


def _cost_str(amount: Optional[float], currency: Optional[str]) -> str:
    if amount is None:
        return ""
    return f"{amount:.2f} {currency}".strip() if currency else f"{amount:.2f}"


def render_itinerary_markdown(plan: ItineraryAgentResponse) -> str:
    """Turn the structured itinerary response into a markdown string
    the frontend can safely pass straight into marked.parse()."""

    lines: list[str] = []

    lines.append(f"# {plan.destination} Travel Plan")
    if plan.trip_duration:
        lines.append(f"**Duration:** {plan.trip_duration}")

    if plan.total_estimated_cost is not None:
        lines.append(
            f"**Estimated total cost:** "
            f"{_cost_str(plan.total_estimated_cost, plan.currency)}"
        )

    if plan.budget_status:
        lines.append(f"**Budget status:** {plan.budget_status}")

    lines.append("")

    for day in plan.itinerary:
        title = f" — {day.title}" if day.title else ""
        date = f" ({day.date})" if day.date else ""
        lines.append(f"## Day {day.day}{date}{title}")

        for act in day.activities:
            time_prefix = f"**{act.time}** — " if act.time else ""
            details = []
            if act.location:
                details.append(act.location)
            if act.duration:
                details.append(act.duration)
            cost = _cost_str(act.estimated_cost, act.currency)
            if cost:
                details.append(cost)

            detail_str = f" ({', '.join(details)})" if details else ""
            lines.append(f"- {time_prefix}{act.activity}{detail_str}")

            if act.notes:
                lines.append(f"  - _{act.notes}_")

        if day.daily_estimated_cost is not None:
            lines.append(
                f"\n*Estimated day cost: "
                f"{_cost_str(day.daily_estimated_cost, day.currency)}*"
            )

        lines.append("")

    if plan.transportation:
        lines.append("## Transportation")
        for seg in plan.transportation:
            cost = _cost_str(seg.estimated_cost, seg.currency)
            cost_str = f" — {cost}" if cost else ""
            duration_str = f" ({seg.estimated_duration})" if seg.estimated_duration else ""
            lines.append(
                f"- {seg.from_location} → {seg.to_location} via {seg.mode}"
                f"{duration_str}{cost_str}"
            )
        lines.append("")

    if plan.practical_notes:
        lines.append("## Practical Notes")
        for note in plan.practical_notes:
            lines.append(f"- {note}")
        lines.append("")

    if plan.assumptions:
        lines.append("## Assumptions")
        for a in plan.assumptions:
            lines.append(f"- {a}")
        lines.append("")

    return "\n".join(lines).strip()


llm = OpenAIConfig()


async def Itinerar_Agent(state: TravelState):
    logger.info("start itinerary agent")

    prompt = Itinerary_Agent_prompt.format(
        user_query=state.get("user_query", ""),
        trip_constraints=state.get("trip_constraints", {}),
        flight_results=state.get("flight_results", {}),
        hotel_results=state.get("hotel_results", {}),
        weather_results=state.get("weather_results", {}),
        budget_results=state.get("budget_results", {}),
    )

    approval_request = (
        "Please review the generated draft itinerary. Approve it to create the "
        "final polished plan, or provide feedback for revision."
    )

    try:
        response = await llm.generate_response(
            prompt=prompt,
            pydantic_schema=ItineraryAgentResponse,
        )

        plan = ItineraryAgentResponse.model_validate(response)
        itinerary_markdown = render_itinerary_markdown(plan)

    except (ValidationError, Exception) as exp:
        logger.error("Itinerary Agent failed", exc_info=True)
        return {
            "itinerary": (
                "The itinerary could not be generated due to an internal "
                f"error: {exp}"
            ),
            "approval_request": approval_request,
            "messages": [
                AIMessage(content=f"Itinerary Agent failed with error: {exp}")
            ],
            "llm_calls": state.get("llm_calls", 0),
        }

    return {
        "itinerary": itinerary_markdown,
        "approval_request": approval_request,
        "messages": [AIMessage(content="Draft itinerary created for human review.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }