"""
Portfolio Router — User profile, portfolio management, and live price endpoints.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

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


class Holding(BaseModel):
    symbol: str                  # NSE symbol e.g. "RELIANCE"
    name: Optional[str] = None   # Full company name
    quantity: float              # Number of shares/units
    avg_cost: float              # Average buy price per unit
    asset_type: Optional[str] = "equity"   # equity | mf | etf | sgb | fd
    sector: Optional[str] = None


class HoldingsUpdate(BaseModel):
    holdings: List[Holding]


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


@router.get("/{user_id}/live")
async def get_live_portfolio(user_id: str):
    """
    Return the user's holdings enriched with live LTP prices from NSE via yfinance.
    Computes real-time: current value, unrealized P&L, day P&L per holding.
    """
    from utils.market_data import compute_portfolio_summary

    profile = await memory.get_user_profile(user_id)
    holdings = profile.get("portfolio", {}).get("holdings", [])

    if not holdings:
        return {
            "user_id": user_id,
            "holdings": [],
            "summary": {"total_value": 0, "total_invested": 0, "total_pnl": 0, "total_pnl_pct": 0, "day_pnl": 0},
            "message": "No holdings found. Add your holdings via the Portfolio page.",
        }

    result = await compute_portfolio_summary(holdings)
    return {"user_id": user_id, **result}


@router.put("/{user_id}/holdings")
async def update_holdings(user_id: str, update: HoldingsUpdate):
    """
    Replace the user's equity/fund holdings list.
    Each holding: symbol, quantity, avg_cost, asset_type, sector.
    """
    holdings_list = [h.model_dump() for h in update.holdings]
    await memory.upsert_user_profile(user_id, {
        "portfolio.holdings": holdings_list
    })
    return {"status": "saved", "holdings_count": len(holdings_list)}


@router.post("/{user_id}/holdings/add")
async def add_holding(user_id: str, holding: Holding):
    """Add or update a single holding by symbol (upserts by symbol)."""
    profile = await memory.get_user_profile(user_id)
    holdings = profile.get("portfolio", {}).get("holdings", [])

    # Upsert: update if symbol exists, else append
    new_holding = holding.model_dump()
    updated = False
    for i, h in enumerate(holdings):
        if h.get("symbol", "").upper() == holding.symbol.upper():
            holdings[i] = new_holding
            updated = True
            break
    if not updated:
        holdings.append(new_holding)

    await memory.upsert_user_profile(user_id, {"portfolio.holdings": holdings})
    return {"status": "added" if not updated else "updated", "symbol": holding.symbol}


@router.delete("/{user_id}/holdings/{symbol}")
async def delete_holding(user_id: str, symbol: str):
    """Remove a holding by symbol."""
    profile = await memory.get_user_profile(user_id)
    holdings = profile.get("portfolio", {}).get("holdings", [])
    filtered = [h for h in holdings if h.get("symbol", "").upper() != symbol.upper()]

    if len(filtered) == len(holdings):
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found in holdings")

    await memory.upsert_user_profile(user_id, {"portfolio.holdings": filtered})
    return {"status": "deleted", "symbol": symbol}


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
