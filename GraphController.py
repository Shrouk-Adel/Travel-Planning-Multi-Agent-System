# =========================
# FastAPI-facing helpers
# =========================
from langgraph.types import Command
from typing import Any
from langchain_core.messages import (
    AnyMessage,
    HumanMessage,
    AIMessage,
    SystemMessage,
)
from graph_nodes.Super_Agent_and_guardrail_Agent import _empty_constraints
import uuid

class GraphController:
    def __init__(self, travel_graph):
        self.travel_graph =travel_graph

    def _interrupt_payload(self,result: dict[str, Any]) -> dict[str, Any] | None:
        interrupts = result.get("__interrupt__", [])
        if not interrupts:
            return None

        first_interrupt = interrupts[0]
        payload = getattr(first_interrupt, "value", first_interrupt)
        return payload if isinstance(payload, dict) else {"value": payload}


    def _serialize_result(self,
        result: dict[str, Any],
        thread_id: str,
    ) -> dict[str, Any]:
        messages = result.get("messages", [])
        last_message = messages[-1].content if messages else ""
        answer = result.get("final_response") or last_message
        interrupt_payload = self._interrupt_payload(result)

        if interrupt_payload:
            answer = interrupt_payload.get("draft_itinerary") or result.get(
                "itinerary", ""
            )

        return {
            "thread_id": thread_id,
            "answer": answer,
            "requires_approval": interrupt_payload is not None,
            "approval_request": (
                interrupt_payload.get("approval_request", "")
                if interrupt_payload
                else result.get("approval_request", "")
            ),
            "flight_results": result.get("flight_results", ""),
            "hotel_results": result.get("hotel_results", ""),
            "weather_results": result.get("weather_results", ""),
            "budget_results": result.get("budget_results", ""),
            "itinerary": (
                interrupt_payload.get("draft_itinerary", "")
                if interrupt_payload
                else result.get("itinerary", "")
            ),
            "selected_agents": result.get("selected_agents", []),
            "trip_constraints": result.get("trip_constraints", {}),
            "supervisor_reasoning": result.get("supervisor_reasoning", ""),
            "guardrail_allowed": result.get("guardrail_allowed", True),
            "guardrail_reason": result.get("guardrail_reason", ""),
            "approved": result.get("approved"),
            "human_feedback": result.get("human_feedback", ""),
            "llm_calls": result.get("llm_calls", 0),
        }


    async def run_travel_agent(self,user_input: str, thread_id: str | None = None):
        """Start a new travel-planning run and pause at human approval."""
        if not thread_id:
            thread_id = f"user_{uuid.uuid4().hex}"

        config = {"configurable": {"thread_id": thread_id}}

        result = await self.travel_graph.ainvoke(
            {
                "messages": [HumanMessage(content=user_input)],
                "user_query": user_input,
                "guardrail_allowed": True,
                "guardrail_reason": "",
                "selected_agents": [],
                "trip_constraints": _empty_constraints(),
                "supervisor_reasoning": "",
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
            },
            config=config,
        )

        return self._serialize_result(result, thread_id)


    async def resume_travel_agent(self,thread_id: str, approved: bool, feedback: str = "" ):
        """Resume the paused LangGraph thread after human review."""
        if not thread_id:
            raise ValueError("thread_id is required to resume a travel plan.")

        config = {"configurable": {"thread_id": thread_id}}
        result = await self.travel_graph.ainvoke(
            Command(
                resume={
                    "approved": approved,
                    "feedback": feedback.strip(),
                }
            ),
            config=config,
        )

        return self._serialize_result(result, thread_id)