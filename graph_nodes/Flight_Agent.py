from Travel_State import TravelState
from ..MCP_Severs import *
from ..prompts  import FLIGHT_AGENT_PROMPT
from llm import OpenAIConfig
from langchain_core.messages import AIMessage   


openai_config = OpenAIConfig()

from pydantic import BaseModel, Field
from typing import List, Optional


class Airport(BaseModel):
    name: str = Field(description="Full airport name")
    iata_code: str = Field(description="3-letter IATA airport code")
    city: str = Field(description="City where the airport is located")
    country: Optional[str] = Field(
        default=None,
        description="Country where the airport is located"
    )


class Airline(BaseModel):
    name: str = Field(description="Airline name")
    iata_code: Optional[str] = Field(
        default=None,
        description="2-letter IATA airline code"
    )


class FlightAgentResponse(BaseModel):
    departure_airport: Optional[Airport] = Field(
        default=None,
        description="Most likely departure airport"
    )

    arrival_airport: Optional[Airport] = Field(
        default=None,
        description="Most likely arrival airport"
    )

    airlines: List[Airline] = Field(
        default_factory=list,
        description="Airlines that typically serve this route"
    )

    typical_flight_duration: Optional[str] = Field(
        default=None,
        description="Typical flight duration, e.g. '3h 45m'"
    )

    estimated_airfare_range: Optional[str] = Field(
        default=None,
        description="Estimated airfare range, including currency, e.g. 'USD 250–450'"
    )

    peak_season_warning: Optional[str] = Field(
        default=None,
        description="Warning about higher prices during peak travel periods"
    )

    booking_advice: List[str] = Field(
        default_factory=list,
        description="Practical booking recommendations"
    )



def fight_agent(state: TravelState) -> str:

        try:
            query = state.get("user_query", "")

            airports =aviation_mcp_call( "get_airports")
            airlines =aviation_mcp_call("get_airlines")

            print("\nAIRPORTS:", airports)
            print("\nAIRLINES:", airlines)

            sys_prompt =FLIGHT_AGENT_PROMPT.format(query=query,
                airport_data=str(airports)[:3000],
                airline_data=str(airlines)[:3000]
            )

            res = openai_config.generate_response(
                    prompt=sys_prompt,
                    pydantic_schema=FlightAgentResponse
            )

        except Exception as exp:
            return f"Flight Agent failed with error: {str(exp)}"

        
        return {
            "flight_results":res,
            "messages": [AIMessage(content="Flight recommendations generated")],
            "llm_calls": state.get("llm_calls", 0) + 1,
        }





