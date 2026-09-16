from routes import *
from fastapi import FastAPI

from pathlib import Path
import traceback

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from graph_nodes.airport_data import load_airport_index
import logging 


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)


logger =logging.getLogger(__name__)


# This is kept from the original project to allow the existing synchronous
# agent functions to call async MCP helpers inside FastAPI.
import nest_asyncio

nest_asyncio.apply()

BASE_DIR = Path(__file__).resolve().parent

from contextlib import asynccontextmanager

from fastapi import FastAPI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from graph_nodes.airport_data import find_main_airport

from db import CheckPointer
from graph import graph


@asynccontextmanager
async def lifespan(app: FastAPI):

    db = CheckPointer()

    logger.info("Loading airport database...")

    load_airport_index()

    print(find_main_airport("Cairo"))
    print(find_main_airport("Tokyo"))
    print(find_main_airport("Egypt"))

    logger.info("Airport database loaded")

    async with AsyncPostgresSaver.from_conn_string(
        db.database_url
    ) as checkpointer:

        await checkpointer.setup()

        app.state.travel_graph = graph.compile(
            checkpointer=checkpointer
        )


        

        yield

app = FastAPI(
    title="Travel Planning Multi-Agent System",
    description="A multi-agent system for travel planning.",
    version="1.0.0",
    lifespan=lifespan
)


app.mount(
    "/ui",
    StaticFiles(directory=str(BASE_DIR / "ui")),
    name="ui",
)

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={},
    )



@app.get("/favicon.ico")
async def favicon():
    return JSONResponse(content={})


app.include_router(health_router)
app.include_router(approve_router)
app.include_router(travel_planner_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=7000,reload=True)