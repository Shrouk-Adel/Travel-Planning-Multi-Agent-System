from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

from Travel_State import TravelState
from ..MCP_Severs import *
from ..prompts  import *
from llm import OpenAIConfig
from langchain_core.messages import AIMessage 
from pydantic import BaseModel, Field
from typing import List
import asyncio


class BudgetRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CostEstimate(BaseModel):
    category: str = Field(
        description=(
            "Cost category, e.g. flights, accommodation, "
            "food, transportation, activities, visa, insurance"
        )
    )

    estimated_amount: Optional[float] = Field(
        default=None,
        description="Estimated cost for this category"
    )

    currency: Optional[str] = Field(
        default=None,
        description="Currency code, e.g. USD, EUR, EGP"
    )

    basis: Optional[str] = Field(
        default=None,
        description=(
            "Explanation of how the estimate was determined, "
            "e.g. live price, search result, approximate estimate"
        )
    )

    is_estimate: bool = Field(
        default=True,
        description="Whether the amount is an approximate estimate"
    )


class BudgetRisk(BaseModel):
    category: str = Field(
        description="Cost category associated with the risk"
    )

    risk_level: BudgetRiskLevel = Field(
        description="Level of budget risk"
    )

    reason: str = Field(
        description="Reason this category represents a budget risk"
    )


class BudgetAgentResponse(BaseModel):
    currency: Optional[str] = Field(
        default=None,
        description="Primary currency used for the budget analysis"
    )

    estimated_costs: List[CostEstimate] = Field(
        default_factory=list,
        description="Estimated costs broken down by category"
    )

    estimated_total: Optional[float] = Field(
        default=None,
        description="Estimated total trip cost"
    )

    budget_provided: Optional[float] = Field(
        default=None,
        description="User's stated trip budget"
    )

    budget_remaining: Optional[float] = Field(
        default=None,
        description=(
            "Estimated amount remaining after subtracting "
            "the estimated trip cost from the user's budget"
        )
    )

    budget_risks: List[BudgetRisk] = Field(
        default_factory=list,
        description="Potential areas where the trip may exceed the budget"
    )

    money_saving_suggestions: List[str] = Field(
        default_factory=list,
        description="Practical ways to reduce trip costs"
    )

    overall_feasibility: str = Field(
        description=(
            "Overall assessment: feasible, potentially_feasible, "
            "or not_feasible"
        )
    )

    feasibility_reason: str = Field(
        description="Short explanation supporting the feasibility assessment"
    )

    is_based_on_live_prices: bool = Field(
        default=False,
        description=(
            "Whether the analysis relies on current/live prices "
            "rather than approximate estimates"
        )
    )


openai =OpenAIConfig()

def Budget_Agent(state: TravelState):
    """
    Budget Agent that analyzes the user's travel request and provides budget feasibility insights.
    
    Args:
        state (TravelState): The current state of travel.

    """

    prompt =Budget_Agent_prompt.formate(
        user_query = state.get("user_query", ""),
        trip_constraints = state.get("trip_constraints", {}),
        flight_results = state.get("flight_results", {}),
        hotel_results = state.get("hotel_results", {}),
        weather_results = state.get("weather_results", {})
    )


    response =openai.generate_response(
            prompt=prompt,
            pydantic_schema=BudgetAgentResponse
        )

    return {
        "budget_results": response,
        "messages": [AIMessage(content="Budget assessment generated.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }
