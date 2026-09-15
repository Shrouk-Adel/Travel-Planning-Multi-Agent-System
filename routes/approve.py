import traceback

 
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from GraphController import GraphController
from Travel_State import TravelState
from fastapi  import APIRouter
from fastapi import Request

approve_router =APIRouter(
    prefix="/api/travel"
)


class ApprovalRequest(BaseModel):
    thread_id: str = Field(min_length=1)
    approved: bool
    feedback: str = ""



@approve_router.post("/approve")
async def approve_travel_plan(request_data: ApprovalRequest,request:Request):
    try:
        if not request_data.approved and not request_data.feedback.strip():
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Please provide revision feedback when rejecting the draft.",
                },
            )

        graph_controller =GraphController(request.app.state.travel_graph)
        result = await graph_controller.resume_travel_agent(
            thread_id=request_data.thread_id,
            approved=request_data.approved,
            feedback=request_data.feedback,
        )

        return JSONResponse(
            content={
                "success": True,
                **result,
            }
        )

    except Exception as exc:
        print("APPROVAL ERROR:", exc)
        traceback.print_exc()

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(exc),
            },
        )



