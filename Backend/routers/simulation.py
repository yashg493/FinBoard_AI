"""
Simulation Router — REST endpoint for economic shock simulation.
Returns full simulation output as JSON (non-streaming).
For streaming, use the WebSocket endpoint in main.py.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.orchestrator import OrchestratorAgent
from memory.mongodb import db as memory

router = APIRouter()

SUPPORTED_SCENARIOS = [
    "india_recession",
    "rate_hike",
    "market_crash",
    "job_loss",
    "inflation_spike",
]


class SimulationRequest(BaseModel):
    user_id: str
    scenario: str


@router.get("/scenarios")
async def list_scenarios():
    """List all available simulation scenarios."""
    return {
        "scenarios": [
            {"id": "india_recession",   "title": "India Recession",              "severity": "CRITICAL"},
            {"id": "rate_hike",         "title": "RBI Emergency Rate Hike +100bps","severity": "HIGH"},
            {"id": "market_crash",      "title": "Market Crash -30%",            "severity": "CRITICAL"},
            {"id": "job_loss",          "title": "Tech Sector Layoffs",          "severity": "HIGH"},
            {"id": "inflation_spike",   "title": "Inflation Spike to 10%",       "severity": "HIGH"},
        ]
    }


@router.post("/run")
async def run_simulation(request: SimulationRequest):
    """
    Run a non-streaming simulation.
    Returns full agent analysis as JSON.
    For live streaming, use the WebSocket endpoint.
    """
    user_profile = await memory.get_user_profile(request.user_id)
    orchestrator = OrchestratorAgent(user_id=request.user_id, memory=memory)

    # Collect all streamed events into a list
    all_events = []
    async for event in orchestrator.run_simulation(
        user_profile=user_profile,
        scenario=request.scenario,
    ):
        all_events.append(event)

    # Extract key outputs
    consensus_event = next((e for e in all_events if e.get("type") == "consensus"), None)
    agent_events = [e for e in all_events if e.get("type") == "agent_output"]

    return {
        "scenario": request.scenario,
        "user_id": request.user_id,
        "event_count": len(all_events),
        "agent_outputs": {e.get("agent"): e.get("data") for e in agent_events},
        "consensus": consensus_event.get("data") if consensus_event else None,
        "verdict": consensus_event.get("message") if consensus_event else "Simulation incomplete",
    }
