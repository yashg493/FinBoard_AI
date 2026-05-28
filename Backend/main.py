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
from routers import broker as broker_router
from utils.connection_manager import ConnectionManager
from utils.observability import setup_tracing
from utils.market_data import enrich_holdings_with_prices

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("boardroom-ai")

manager = ConnectionManager()
sentinel = SentinelAgent()

# Per-user session state: tracks macro context + current consensus for Q&A
_session_state: dict[str, dict] = {}


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
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://boardroom-ai.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(portfolio.router,      prefix="/api/portfolio",  tags=["portfolio"])
app.include_router(simulation.router,     prefix="/api/simulation", tags=["simulation"])
app.include_router(history.router,        prefix="/api/history",    tags=["history"])
app.include_router(broker_router.router,  prefix="/api/broker",     tags=["broker"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "boardroom-ai", "version": "2.0.0"}


@app.get("/api/market/tickers")
async def get_common_tickers():
    """Return common NSE tickers for portfolio autocomplete."""
    from utils.market_data import COMMON_NSE_TICKERS
    return {"tickers": COMMON_NSE_TICKERS}


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """
    Main WebSocket for live board meeting streaming.
    Streams agent debate events to the frontend in real time.

    Supported event types from client:
    - trigger_board_meeting: Start a full governance session
    - trigger_simulation:    Run a scenario simulation
    - user_input:            User asks a question or states a constraint mid-session
    - ping:                  Keepalive
    """
    await manager.connect(websocket, user_id)
    # Initialize session state for this user
    _session_state[user_id] = {"macro_data": None, "recent_consensus": None, "user_constraints": []}

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            event_type = payload.get("type")

            if event_type == "trigger_board_meeting":
                context = payload.get("context", {})
                # Attach accumulated user constraints to the meeting
                context["user_constraints"] = _session_state[user_id].get("user_constraints", [])
                await run_board_meeting(user_id, context, websocket)

            elif event_type == "trigger_simulation":
                scenario = payload.get("scenario", "")
                await run_simulation(user_id, scenario, websocket)

            elif event_type == "user_input":
                # User is asking a question or stating a constraint
                question = payload.get("message", "").strip()
                is_constraint = payload.get("is_constraint", False)

                if not question:
                    continue

                # If it's a constraint, store it and acknowledge
                if is_constraint:
                    _session_state[user_id]["user_constraints"].append(question)
                    await websocket.send_json({
                        "type": "constraint_acknowledged",
                        "agent": "System",
                        "message": f"✓ Noted: \"{question}\" — the board will factor this into all future analysis.",
                    })
                else:
                    # Answer the question using the orchestrator
                    await handle_user_question(user_id, question, websocket)

            elif event_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(user_id)
        _session_state.pop(user_id, None)
        logger.info(f"User {user_id} disconnected")


async def run_board_meeting(user_id: str, context: dict, websocket: WebSocket):
    """Orchestrate a full board meeting and stream events to frontend."""
    user_profile = await memory.get_user_profile(user_id)
    macro_data = await sentinel.fetch_macro_data()

    # Enrich holdings with live prices before the meeting starts
    if user_profile.get("portfolio") and user_profile["portfolio"].get("holdings"):
        enriched = await enrich_holdings_with_prices(user_profile["portfolio"]["holdings"])
        user_profile["portfolio"]["holdings"] = enriched

    # Fetch prior meetings for context
    prior_meetings = await memory.get_recent_meetings_summary(user_id, limit=2)
    context["prior_decisions"] = prior_meetings

    # Cache macro data in session state for Q&A use
    _session_state[user_id]["macro_data"] = macro_data

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
        # Cache consensus for context-aware Q&A
        if event.get("type") == "consensus":
            _session_state[user_id]["recent_consensus"] = event.get("message", "")
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


async def handle_user_question(user_id: str, question: str, websocket: WebSocket):
    """Handle a user question mid-session using the orchestrator's Q&A mode."""
    user_profile = await memory.get_user_profile(user_id)
    session = _session_state.get(user_id, {})
    macro_data = session.get("macro_data") or await sentinel.fetch_macro_data()

    # Echo the user's message back so it appears in the event feed
    await websocket.send_json({
        "type": "user_input",
        "agent": "You",
        "message": question,
    })

    orchestrator = OrchestratorAgent(user_id=user_id, memory=memory)

    async for event in orchestrator.handle_user_question(
        user_profile=user_profile,
        macro_data=macro_data,
        question=question,
        meeting_context={"recent_consensus": session.get("recent_consensus")},
    ):
        await websocket.send_json(event)
        await asyncio.sleep(0.05)
