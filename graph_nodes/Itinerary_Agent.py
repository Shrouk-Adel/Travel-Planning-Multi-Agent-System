from typing import List, Optional
import logging

from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage

from Travel_State import TravelState
from llm import OpenAIConfig


logger = logging.getLogger(__name__)


# ============================================================
# Pydantic Schemas
# ============================================================

class ItineraryActivity(BaseModel):
    time: Optional[str] = None
    activity: str
    location: Optional[str] = None
    duration: Optional[str] = None
    estimated_cost: Optional[float] = None
    currency: Optional[str] = None
    notes: Optional[str] = None


class ItineraryDay(BaseModel):
    day: int
    date: Optional[str] = None
    title: Optional[str] = None

    activities: List[ItineraryActivity] = Field(
        default_factory=list
    )

    daily_estimated_cost: Optional[float] = None
    currency: Optional[str] = None


class TransportationSegment(BaseModel):
    from_location: str
    to_location: str
    mode: str

    estimated_duration: Optional[str] = None
    estimated_cost: Optional[float] = None
    currency: Optional[str] = None


class ItineraryAgentResponse(BaseModel):

    # --------------------------------------------------------
    # Trip information
    # --------------------------------------------------------

    destination: str
    trip_duration: Optional[str] = None

    # --------------------------------------------------------
    # Flight information
    # --------------------------------------------------------

    departure_airport: Optional[str] = None
    arrival_airport: Optional[str] = None

    flight_details: List[str] = Field(
        default_factory=list
    )

    # --------------------------------------------------------
    # Hotel information
    # --------------------------------------------------------

    selected_hotel: Optional[str] = None
    hotel_price: Optional[str] = None

    # --------------------------------------------------------
    # Daily itinerary
    # --------------------------------------------------------

    itinerary: List[ItineraryDay] = Field(
        default_factory=list
    )

    # --------------------------------------------------------
    # Transportation
    # --------------------------------------------------------

    transportation: List[TransportationSegment] = Field(
        default_factory=list
    )

    # --------------------------------------------------------
    # Cost
    # --------------------------------------------------------

    total_estimated_cost: Optional[float] = None
    currency: Optional[str] = None

    budget_status: Optional[str] = None

    # --------------------------------------------------------
    # Additional information
    # --------------------------------------------------------

    practical_notes: List[str] = Field(
        default_factory=list
    )

    assumptions: List[str] = Field(
        default_factory=list
    )


# ============================================================
# LLM
# ============================================================

llm = OpenAIConfig()


# ============================================================
# Helper: format cost
# ============================================================

def _cost_str(
    amount: Optional[float],
    currency: Optional[str]
) -> str:

    if amount is None:
        return ""

    if currency:
        return f"{amount:.2f} {currency}"

    return f"{amount:.2f}"


# ============================================================
# Helper: Render itinerary as Markdown
# ============================================================

def render_itinerary_markdown(
    plan: ItineraryAgentResponse
) -> str:

    lines: List[str] = []

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    lines.append(
        f"# {plan.destination} Travel Plan"
    )

    if plan.trip_duration:
        lines.append(
            f"**Duration:** {plan.trip_duration}"
        )

    # --------------------------------------------------------
    # Airports
    # --------------------------------------------------------

    if (
        plan.departure_airport
        or plan.arrival_airport
    ):

        lines.append("")

        lines.append("## Flights")

        if plan.departure_airport:
            lines.append(
                f"- **Departure:** {plan.departure_airport}"
            )

        if plan.arrival_airport:
            lines.append(
                f"- **Arrival:** {plan.arrival_airport}"
            )

        for flight in plan.flight_details:
            lines.append(
                f"- {flight}"
            )

    # --------------------------------------------------------
    # Hotel
    # --------------------------------------------------------

    if plan.selected_hotel:

        lines.append("")

        lines.append("## Hotel")

        lines.append(
            f"- **Hotel:** {plan.selected_hotel}"
        )

        if plan.hotel_price:
            lines.append(
                f"- **Price:** {plan.hotel_price}"
            )

    # --------------------------------------------------------
    # Total cost
    # --------------------------------------------------------

    if plan.total_estimated_cost is not None:

        lines.append("")

        lines.append(
            f"**Estimated total cost:** "
            f"{_cost_str(plan.total_estimated_cost, plan.currency)}"
        )

    if plan.budget_status:

        lines.append(
            f"**Budget status:** {plan.budget_status}"
        )

    # --------------------------------------------------------
    # Daily itinerary
    # --------------------------------------------------------

    lines.append("")

    lines.append("## Daily Itinerary")

    for day in plan.itinerary:

        title = (
            f" — {day.title}"
            if day.title
            else ""
        )

        date = (
            f" ({day.date})"
            if day.date
            else ""
        )

        lines.append(
            f"### Day {day.day}{date}{title}"
        )

        for activity in day.activities:

            time_prefix = (
                f"**{activity.time}** — "
                if activity.time
                else ""
            )

            details = []

            if activity.location:
                details.append(
                    activity.location
                )

            if activity.duration:
                details.append(
                    activity.duration
                )

            cost = _cost_str(
                activity.estimated_cost,
                activity.currency
            )

            if cost:
                details.append(cost)

            detail_text = (
                f" ({', '.join(details)})"
                if details
                else ""
            )

            lines.append(
                f"- {time_prefix}"
                f"{activity.activity}"
                f"{detail_text}"
            )

            if activity.notes:
                lines.append(
                    f"  - _{activity.notes}_"
                )

        if day.daily_estimated_cost is not None:

            lines.append(
                f"*Estimated day cost: "
                f"{_cost_str(day.daily_estimated_cost, day.currency)}*"
            )

        lines.append("")

    # --------------------------------------------------------
    # Transportation
    # --------------------------------------------------------

    if plan.transportation:

        lines.append(
            "## Transportation"
        )

        for segment in plan.transportation:

            duration = (
                f" ({segment.estimated_duration})"
                if segment.estimated_duration
                else ""
            )

            cost = _cost_str(
                segment.estimated_cost,
                segment.currency
            )

            cost_text = (
                f" — {cost}"
                if cost
                else ""
            )

            lines.append(
                f"- {segment.from_location} "
                f"→ {segment.to_location} "
                f"via {segment.mode}"
                f"{duration}"
                f"{cost_text}"
            )

        lines.append("")

    # --------------------------------------------------------
    # Practical notes
    # --------------------------------------------------------

    if plan.practical_notes:

        lines.append(
            "## Practical Notes"
        )

        for note in plan.practical_notes:
            lines.append(
                f"- {note}"
            )

        lines.append("")

    # --------------------------------------------------------
    # Assumptions
    # --------------------------------------------------------

    if plan.assumptions:

        lines.append(
            "## Assumptions"
        )

        for assumption in plan.assumptions:
            lines.append(
                f"- {assumption}"
            )

        lines.append("")

    return "\n".join(lines).strip()


# ============================================================
# Itinerary Agent
# ============================================================

async def Itinerary_Agent(
    state: TravelState
):

    logger.info(
        "Starting Itinerary Agent"
    )

    try:

        # ====================================================
        # 1. Get basic trip information
        # ====================================================

        constraints = state.get(
            "trip_constraints",
            {}
        )

        destination = constraints.get(
            "destination",
            ""
        )

        duration = constraints.get(
            "duration",
            ""
        )

        travel_style = constraints.get(
            "travel_style",
            ""
        )

        # ====================================================
        # 2. Get previous agent results
        # ====================================================

        flight = state.get(
            "flight_results",
            {}
        ) or {}

        hotel = state.get(
            "hotel_results",
            {}
        ) or {}

        weather = state.get(
            "weather_results",
            {}
        ) or {}

        # ====================================================
        # 3. Build SMALL flight input
        #
        # Don't send the entire flight response.
        # ====================================================

        flight_input = {

            "departure_airport": flight.get(
                "departure_airport"
            ),

            "arrival_airport": flight.get(
                "arrival_airport"
            ),

            "flights": flight.get(
                "flights",
                []
            )
        }

        # ====================================================
        # 4. Build SMALL hotel input
        # ====================================================

        hotels = hotel.get(
            "hotels",
            []
        )

        # Keep only useful hotel information
        hotel_input = []

        for h in hotels[:5]:

            if isinstance(h, dict):

                hotel_input.append({
                    "name": h.get("name"),
                    "location": h.get("location"),
                    "price": h.get("price"),
                    "rating": h.get("rating"),
                    "source_url": h.get("source_url")
                })

            else:

                # Pydantic object support
                try:

                    hotel_input.append({
                        "name": getattr(
                            h,
                            "name",
                            None
                        ),

                        "location": getattr(
                            h,
                            "location",
                            None
                        ),

                        "price": getattr(
                            h,
                            "price",
                            None
                        ),

                        "rating": getattr(
                            h,
                            "rating",
                            None
                        ),

                        "source_url": getattr(
                            h,
                            "source_url",
                            None
                        )
                    })

                except Exception:
                    continue

        # ====================================================
        # 5. Build SMALL weather input
        # ====================================================

        weather_input = {

            "current": weather.get(
                "current"
            ),

            "forecast": weather.get(
                "forecast"
            )
        }

        # ====================================================
        # 6. Prompt
        # ====================================================

        prompt = f"""
You are a travel itinerary planner.

Create a practical day-by-day travel itinerary.

TRIP
Destination: {destination}
Duration: {duration}
Travel style: {travel_style}

FLIGHT INFORMATION
{flight_input}

HOTEL INFORMATION
{hotel_input}

WEATHER INFORMATION
{weather_input}

REQUIREMENTS

1. Create a practical itinerary for each day.
2. Include the departure and arrival airport names when available.
3. Include useful flight information when available.
4. Select a suitable hotel from the provided hotels.
5. Consider the weather when choosing activities.
6. Include transportation between important locations.
7. Include estimated activity and transportation costs when available.
8. Do not invent flight information.
9. Do not invent hotel prices.
10. Do not invent weather information.
11. If information is missing, leave the field empty.
12. Keep the itinerary concise and realistic.

Return the result using the required structured format.
"""

        logger.debug(
            "Itinerary prompt prepared"
        )

        # ====================================================
        # 7. Call LLM with Pydantic schema
        # ====================================================

        response = await llm.generate_response(
            prompt=prompt,
            pydantic_schema=ItineraryAgentResponse
        )

        # ====================================================
        # 8. Validate response
        # ====================================================

        plan = ItineraryAgentResponse.model_validate(
            response
        )

        # ====================================================
        # 9. Render for frontend
        # ====================================================

        itinerary_markdown = (
            render_itinerary_markdown(plan)
        )

        logger.info(
            "Itinerary Agent completed successfully"
        )

        # ====================================================
        # 10. Return state update
        # ====================================================

        return {

            "itinerary": itinerary_markdown,

            "messages": [
                AIMessage(
                    content="Draft itinerary created."
                )
            ],

            "llm_calls": (
                state.get("llm_calls", 0) + 1
            )
        }

    except Exception as exc:

        logger.error(
            "Itinerary Agent failed: %s",
            exc,
            exc_info=True
        )

        return {

            "itinerary": (
                "Unable to create the itinerary."
            ),

            "messages": [
                AIMessage(
                    content="Itinerary Agent failed."
                )
            ],

            "llm_calls": (
                state.get("llm_calls", 0) + 1
            )
        }