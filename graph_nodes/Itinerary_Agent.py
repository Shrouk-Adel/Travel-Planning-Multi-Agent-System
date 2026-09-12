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

llm =OpenAIConfig()
def Itinerar_Agent(state:TravelState):
    prompt =Itinerary_Agent_prompt.format(
               user_query = state.get("user_query", ""),
               trip_constraints = state.get("trip_constraints", {}),
               flight_results = state.get("flight_results", {}),
               hotel_results = state.get("hotel_results", {}),
               weather_results = state.get("weather_results", {}),
               budget_results = state.get("budget_results", {})
        )

    response =llm.generate_response(
        prompt =prompt,
        pydantic_schema=ItineraryAgentResponse
    )

    approval_request = (
        "Please review the generated draft itinerary. Approve it to create the "
        "final polished plan, or provide feedback for revision."
    )

    return {
        "itinerary": response,
        "approval_request": approval_request,
        "messages": [AIMessage(content="Draft itinerary created for human review.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }

    