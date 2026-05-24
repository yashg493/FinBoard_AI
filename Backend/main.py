"""
Boardroom AI — Autonomous Multi-Agent Financial Governance System
FastAPI Backend Entry Point
"""
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agents.orchestrator import OrchestratorAgent
from agents.sentinel import SentinelAgent
from memory.mongodb import db as memory
from routers import portfolio, simulation, history
from utils.connection_manager import ConnectionManager
from utils.observability import setup_tracing

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("boardroom-ai")

manager = ConnectionManager()
sentinel = SentinelAgent()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_tracing()
    await memory.connect()
    logger.info("MongoDB connected and tracing setup complete")
    yield
    await memory.close()
    logger.info("MongoDB disconnected")


app = FastAPI(
    title="Boardroom AI",
    description="Autonomous Multi-Agent Financial Governance System",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://boardroom-ai.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(simulation.router, prefix="/api/simulation", tags=["simulation"])
app.include_router(history.router, prefix="/api/history", tags=["history"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "boardroom-ai"}


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """
    Main WebSocket for live board meeting streaming.
    Streams agent debate events to the frontend in real time.
    """
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            event_type = payload.get("type")

            if event_type == "trigger_board_meeting":
                context = payload.get("context", {})
                await run_board_meeting(user_id, context, websocket)

            elif event_type == "trigger_simulation":
                scenario = payload.get("scenario", "")
                await run_simulation(user_id, scenario, websocket)

            elif event_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(user_id)
        logger.info(f"User {user_id} disconnected")


async def run_board_meeting(user_id: str, context: dict, websocket: WebSocket):
    """Orchestrate a full board meeting and stream events to frontend."""
    user_profile = await memory.get_user_profile(user_id)
    macro_data = await sentinel.fetch_macro_data()

    orchestrator = OrchestratorAgent(user_id=user_id, memory=memory)

    await websocket.send_json({
        "type": "board_meeting_start",
        "message": "Board meeting initiated. Agents assembling...",
    })

    async for event in orchestrator.run_board_meeting(
        user_profile=user_profile,
        macro_data=macro_data,
        context=context,
    ):
        await websocket.send_json(event)
        await asyncio.sleep(0.05)  # Smooth streaming

    await websocket.send_json({"type": "board_meeting_end"})


async def run_simulation(user_id: str, scenario: str, websocket: WebSocket):
    """Run an economic shock simulation."""
    user_profile = await memory.get_user_profile(user_id)
    orchestrator = OrchestratorAgent(user_id=user_id, memory=memory)

    await websocket.send_json({
        "type": "simulation_start",
        "scenario": scenario,
    })

    async for event in orchestrator.run_simulation(
        user_profile=user_profile,
        scenario=scenario,
    ):
        await websocket.send_json(event)
        await asyncio.sleep(0.05)

    await websocket.send_json({"type": "simulation_end"})
