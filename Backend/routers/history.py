"""
History Router — Board meeting history retrieval endpoints.
"""
from fastapi import APIRouter

from memory.mongodb import db as memory

router = APIRouter()


@router.get("/{user_id}")
async def get_meeting_history(user_id: str, limit: int = 10):
    """Fetch past board meetings for a user (newest first)."""
    meetings = await memory.get_meeting_history(user_id, limit=limit)
    return {
        "user_id": user_id,
        "meetings": meetings,
        "count": len(meetings),
    }


@router.get("/{user_id}/{meeting_id}")
async def get_single_meeting(user_id: str, meeting_id: str):
    """Fetch a single board meeting by ID."""
    meeting = await memory.get_meeting_by_id(meeting_id)
    if not meeting or meeting.get("user_id") != user_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


@router.get("/macro/events")
async def get_macro_events(limit: int = 20):
    """Recent macroeconomic events that triggered board meetings."""
    events = await memory.get_recent_macro_events(limit=limit)
    return {"events": events, "count": len(events)}
