import traceback

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from GraphController import GraphController

travel_planner_router = APIRouter(prefix="/api")


class TravelRequest(BaseModel):
    origin: str
    destination: str
    date: str
    duration: int
    budget: float
    currency: str
    num_travelers: int
    interests: list[str] = []
    thread_id: str | None = None
    message: str | None = None


@travel_planner_router.post("/travel")
async def travel_planner(request_data: TravelRequest, request: Request):
    try:
        graph_controller = GraphController(
            travel_graph=request.app.state.travel_graph
        )

        result = await graph_controller.run_travel_agent(
            request_data=request_data,
            thread_id=request_data.thread_id,
        )

        return JSONResponse(content={"success": True, **result})

    except Exception as exc:
        print("ERROR:", exc)
        traceback.print_exc()

        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(exc)},
        )