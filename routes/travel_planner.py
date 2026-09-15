from pathlib import Path
import traceback

 
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from GraphController import GraphController
from fastapi import Request
from Travel_State import TravelState
from fastapi  import APIRouter

travel_planner_router =APIRouter(
    prefix="/api"
)

class TravelRequest(BaseModel):
    message: str
    thread_id: str | None = None



@travel_planner_router.post("/travel")
async def travel_planner(request_data: TravelRequest,request: Request):
    try:

        graph_controller =GraphController(travel_graph =request.app.state.travel_graph)

        user_message = request_data.message.strip()

        if not user_message:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Message cannot be empty.",
                },
            )

        result = await graph_controller.run_travel_agent(
            user_input=user_message,
            thread_id=request_data.thread_id,
        )

        return JSONResponse(
            content={
                "success": True,
                **result,
            }
        )

    except Exception as exc:
        print("ERROR:", exc)
        traceback.print_exc()

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(exc),
            },
        )
