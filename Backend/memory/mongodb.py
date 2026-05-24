"""
MongoDB Memory Layer — Persistent storage for user profiles,
board meeting history, portfolio state, and macroeconomic events.
"""
import os
from datetime import datetime
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import DESCENDING

MONGO_URI = os.getenv("MONGODB_URI", "mongodb+srv://user:pass@cluster.mongodb.net/boardroom-ai")
DB_NAME = "boardroom_ai"


class MongoMemory:
    """
    Async MongoDB client using motor.
    Collections:
      - users: user financial profiles
      - board_meetings: full meeting transcripts and outputs
      - macro_events: macroeconomic event log
      - portfolio_snapshots: periodic portfolio state
    """

    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None

    async def connect(self):
        self.client = AsyncIOMotorClient(MONGO_URI)
        self.db = self.client[DB_NAME]
        # Ensure indexes
        await self.db.board_meetings.create_index([("user_id", 1), ("timestamp", DESCENDING)])
        await self.db.users.create_index("user_id", unique=True)
        await self.db.macro_events.create_index([("timestamp", DESCENDING)])

    async def close(self):
        if self.client:
            self.client.close()

    # ── User Profile ──

    async def get_user_profile(self, user_id: str) -> dict:
        doc = await self.db.users.find_one({"user_id": user_id})
        if doc:
            doc.pop("_id", None)
            return doc
        return self._default_profile(user_id)

    async def upsert_user_profile(self, user_id: str, profile: dict) -> None:
        profile["user_id"] = user_id
        profile["updated_at"] = datetime.utcnow().isoformat()
        await self.db.users.update_one(
            {"user_id": user_id},
            {"$set": profile},
            upsert=True,
        )

    def _default_profile(self, user_id: str) -> dict:
        """Demo profile — replace with actual onboarding data."""
        return {
            "user_id": user_id,
            "name": "Yash",
            "age": 28,
            "country": "India",
            "employer_sector": "Technology",
            "monthly_income": 150000,
            "monthly_expenses": 60000,
            "sip_monthly": 65000,
            "risk_tolerance": "moderate_aggressive",
            "investment_horizon_years": 20,
            "tax_regime": "new",
            "months_to_fy_end": 3,
            "emergency_fund_months": 3,
            "portfolio": {
                "total_value": 2500000,
                "allocation": {
                    "large_cap_equity": 40,
                    "mid_small_cap_equity": 25,
                    "international_equity": 5,
                    "debt_funds": 15,
                    "gold_sgb": 5,
                    "fd_liquid": 10,
                },
                "unrealized_gains": {
                    "total_ltcg": 180000,
                    "total_stcg": 45000,
                    "total_loss": 30000,
                },
                "holdings": [],
            },
            "emis": [
                {"type": "Home Loan", "amount": 25000, "remaining_months": 180, "rate_pct": 8.5},
            ],
            "insurance": {
                "term": {"cover": 20000000, "provider": "ICICI Prudential", "premium_monthly": 1010},
                "health": {"cover": 500000, "provider": "Star Health"},
            },
            "deductions_used": {
                "80C": 90000,
                "80D": 25000,
                "80CCD1B": 0,
            },
        }

    # ── Board Meetings ──

    async def save_board_meeting(self, meeting: dict) -> str:
        meeting["created_at"] = datetime.utcnow().isoformat()
        result = await self.db.board_meetings.insert_one(meeting)
        return str(result.inserted_id)

    async def get_meeting_history(self, user_id: str, limit: int = 10) -> list[dict]:
        cursor = self.db.board_meetings.find(
            {"user_id": user_id},
            {"_id": 0},
        ).sort("timestamp", DESCENDING).limit(limit)
        return await cursor.to_list(length=limit)

    async def get_meeting_by_id(self, meeting_id: str) -> Optional[dict]:
        doc = await self.db.board_meetings.find_one(
            {"meeting_id": meeting_id}, {"_id": 0}
        )
        return doc

    # ── Macro Events ──

    async def log_macro_event(self, event: dict) -> None:
        event["logged_at"] = datetime.utcnow().isoformat()
        await self.db.macro_events.insert_one(event)

    async def get_recent_macro_events(self, limit: int = 20) -> list[dict]:
        cursor = self.db.macro_events.find(
            {}, {"_id": 0}
        ).sort("timestamp", DESCENDING).limit(limit)
        return await cursor.to_list(length=limit)

    # ── Portfolio Snapshots ──

    async def save_portfolio_snapshot(self, user_id: str, snapshot: dict) -> None:
        snapshot["user_id"] = user_id
        snapshot["snapshot_at"] = datetime.utcnow().isoformat()
        await self.db.portfolio_snapshots.insert_one(snapshot)

    async def get_portfolio_timeline(self, user_id: str, limit: int = 30) -> list[dict]:
        cursor = self.db.portfolio_snapshots.find(
            {"user_id": user_id}, {"_id": 0}
        ).sort("snapshot_at", DESCENDING).limit(limit)
        return await cursor.to_list(length=limit)


# Shared global database connection instance
db = MongoMemory()

