from Travel_State import TravelState
from ..MCP_Severs import *
from ..prompts  import *
from llm import OpenAIConfig
from langchain_core.messages import AIMessage 
from pydantic import BaseModel, Field
from typing import List
import asyncio


from pydantic import BaseModel, Field
from typing import List, Optional


class HotelLocation(BaseModel):
    city: str = Field(description="City where the hotel is located")
    country: Optional[str] = None
    neighborhood: Optional[str] = Field(
        default=None,
        description="Neighborhood or area of the hotel"
    )


class HotelPrice(BaseModel):
    amount: Optional[float] = Field(
        default=None,
        description="Price amount"
    )
    currency: Optional[str] = Field(
        default=None,
        description="Currency code, e.g. USD, EUR, EGP"
    )
    period: Optional[str] = Field(
        default=None,
        description="Price period, e.g. per night, per stay"
    )


class Hotel(BaseModel):
    name: str = Field(description="Hotel name")
    location: HotelLocation
    star_rating: Optional[float] = Field(
        default=None,
        description="Hotel star rating if available"
    )
    guest_rating: Optional[float] = Field(
        default=None,
        description="Guest rating if available"
    )
    price: Optional[HotelPrice] = Field(
        default=None,
        description="Price information if available"
    )
    amenities: List[str] = Field(
        default_factory=list,
        description="Important amenities mentioned in the source"
    )
    highlights: List[str] = Field(
        default_factory=list,
        description="Important hotel features or advantages"
    )
    source_url: Optional[str] = Field(
        default=None,
        description="URL of the source where this hotel was found"
    )


class HotelAgentResponse(BaseModel):
    destination: str = Field(
        description="Requested destination"
    )
    hotels: List[Hotel] = Field(
        default_factory=list,
        description="Hotels found in the search results"
    )
    recommended_neighborhoods: List[str] = Field(
        default_factory=list,
        description="Recommended areas to stay"
    )
    accommodation_advice: List[str] = Field(
        default_factory=list,
        description="General accommodation recommendations"
    )
    search_status: str = Field(
        description="live_results, general_advice, or unavailable"
    )
    disclaimer: Optional[str] = Field(
        default=None,
        description="Important limitation or pricing disclaimer"
    )

# =========================
# Hotel Agent - original behavior kept
# =========================


openai =OpenAIConfig()

def hotel_agent(state: TravelState):
    """
    Hotel Agent that retrieves hotel information based on the user's travel request.
    
    Args:
        state (TravelState): The current state of travel.
        
    Returns:
        dict: A dictionary containing hotel results and updated messages.
    """ 
    query = f"Best hotels for {state['user_query']}"

    try:
        hotel_results = asyncio.run(
            tavily_mcp_search(query)
        )

        hotel_results =openai.generate_response(
            prompt =HOTEL_AGENT_PROMPT.format(
                query=query,
                hotel_results=str(hotel_results)[:3000]
            ),
            pydantic_schema=HotelAgentResponse
        )

    except Exception as exc:
        print(
            f"HOTEL AGENT MCP ERROR: "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )

        hotel_results = (
            "Live hotel search is temporarily unavailable. "
            "Provide general accommodation and neighborhood "
            "guidance based on the destination and clearly "
            "label it as non-live advice."
        )
      
    return {
        "hotel_results": hotel_results,
        "messages": [
            AIMessage(
                content="Hotel information processed."
            )
        ],
        "llm_calls": (
            state.get("llm_calls", 0) + 1
        ),
    }