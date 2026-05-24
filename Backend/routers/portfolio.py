"""
Portfolio Router — User profile and portfolio management endpoints.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from memory.mongodb import db as memory

router = APIRouter()


class PortfolioUpdate(BaseModel):
    monthly_income: Optional[int] = None
    monthly_expenses: Optional[int] = None
    sip_monthly: Optional[int] = None
    risk_tolerance: Optional[str] = None
    investment_horizon_years: Optional[int] = None
    tax_regime: Optional[str] = None
    emergency_fund_months: Optional[int] = None
    employer_sector: Optional[str] = None
    portfolio: Optional[dict] = None
    emis: Optional[list] = None
    insurance: Optional[dict] = None
    deductions_used: Optional[dict] = None


@router.get("/{user_id}")
async def get_portfolio(user_id: str):
    """Fetch user financial profile and portfolio state."""
    profile = await memory.get_user_profile(user_id)
    return {"user_id": user_id, "profile": profile}


@router.patch("/{user_id}")
async def update_portfolio(user_id: str, update: PortfolioUpdate):
    """Update specific fields of the user's financial profile."""
    patch = {k: v for k, v in update.model_dump().items() if v is not None}
    if not patch:
        raise HTTPException(status_code=400, detail="No fields to update")
    await memory.upsert_user_profile(user_id, patch)
    return {"status": "updated", "fields": list(patch.keys())}


@router.get("/{user_id}/snapshots")
async def get_portfolio_timeline(user_id: str, limit: int = 30):
    """Get historical portfolio snapshots."""
    snapshots = await memory.get_portfolio_timeline(user_id, limit=limit)
    return {"user_id": user_id, "snapshots": snapshots, "count": len(snapshots)}


@router.post("/{user_id}/snapshots")
async def save_portfolio_snapshot(user_id: str, snapshot: dict):
    """Save a portfolio snapshot for trend tracking."""
    await memory.save_portfolio_snapshot(user_id, snapshot)
    return {"status": "saved"}
