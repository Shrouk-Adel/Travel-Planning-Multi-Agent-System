from fastapi import APIRouter, status
from fastapi.responses import JSONResponse




health_router = APIRouter(
    prefix="/health",
    tags=["Health"],
)

    
@health_router.get("")
async def get_health_status():
    """
    Get the health status of the application.

    Returns:
        JSONResponse: A JSON response containing the health status.
    """
    return JSONResponse(
        content={"status": "healthy"},
        status_code=status.HTTP_200_OK
    )