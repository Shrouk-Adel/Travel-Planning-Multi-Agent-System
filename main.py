from routes.Health import health_router
from fastapi import FastAPI





app = FastAPI(
    title="Travel Planning Multi-Agent System",
    description="A multi-agent system for travel planning.",
    version="1.0.0",
)


app.include_router(health_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)