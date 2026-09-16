from langgraph.types import Command
from typing import Any
import uuid

from state_builder import build_initial_state


class GraphController:
    def __init__(self, travel_graph):
        self.travel_graph = travel_graph

    def _interrupt_payload(self, result: dict[str, Any]) -> dict[str, Any] | None:
        interrupts = result.get("__interrupt__", [])
        if not interrupts:
            return None

        first_interrupt = interrupts[0]
        payload = getattr(first_interrupt, "value", first_interrupt)
        return payload if isinstance(payload, dict) else {"value": payload}

    def _serialize_result(
        self,
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
            "approved": result.get("approved"),
            "human_feedback": result.get("human_feedback", ""),
            "llm_calls": result.get("llm_calls", 0),
        }

    async def run_travel_agent(
        self,
        request_data,
        thread_id: str | None = None,
    ):
        """Start a new travel-planning run and pause at human approval."""

        if not thread_id:
            thread_id = f"user_{uuid.uuid4().hex}"

        initial_state = build_initial_state(
            origin=request_data.origin,
            destination=request_data.destination,
            date=request_data.date,
            duration=request_data.duration,
            budget=request_data.budget,
            currency=request_data.currency,
            num_travelers=request_data.num_travelers,
            interests=request_data.interests,
            message=request_data.message,
        )

        config = {
            "configurable": {
                "thread_id": thread_id,
            },
            "run_name": "Travel Planning - New Request",
            "tags": [
                "travel-agent",
                "new-request",
            ],
            "metadata": {
                "thread_id": thread_id,
                "origin": request_data.origin,
                "destination": request_data.destination,
                "num_travelers": request_data.num_travelers,
            },
        }

        result = await self.travel_graph.ainvoke(
            initial_state,
            config=config,
        )

        return self._serialize_result(result, thread_id)

    async def resume_travel_agent(
        self,
        thread_id: str,
        approved: bool,
        feedback: str = "",
    ):
        """Resume the paused LangGraph thread after human review."""

        if not thread_id:
            raise ValueError("thread_id is required to resume a travel plan.")

        config = {
            "configurable": {
                "thread_id": thread_id,
            },
            "run_name": "Travel Planning - Human Approval",
            "tags": [
                "travel-agent",
                "human-approval",
            ],
            "metadata": {
                "thread_id": thread_id,
                "approved": approved,
                "has_feedback": bool(feedback.strip()),
            },
        }

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