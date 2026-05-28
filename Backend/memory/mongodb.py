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
        await self.db.broker_connections.create_index("user_id", unique=True)

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
                "holdings": [
                    {"symbol": "RELIANCE", "quantity": 150, "avg_price": 2450.50, "current_price": 2980.00},
                    {"symbol": "TCS", "quantity": 100, "avg_price": 3850.00, "current_price": 3950.00},
                    {"symbol": "HDFCBANK", "quantity": 300, "avg_price": 1650.00, "current_price": 1420.00},
                    {"symbol": "PAYTM", "quantity": 500, "avg_price": 950.00, "current_price": 420.00}
                ],
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

    async def get_recent_meetings_summary(self, user_id: str, limit: int = 3) -> list[dict]:
        """
        Return compact summaries of recent board meetings for prompt injection.
        Includes: meeting_id, timestamp, board verdict, consensus actions, and macro snapshot.
        """
        cursor = self.db.board_meetings.find(
            {"user_id": user_id},
            {
                "_id": 0,
                "meeting_id": 1,
                "timestamp": 1,
                "agent_outputs.orchestrator.recommendation": 1,
                "agent_outputs.orchestrator.reasoning": 1,
                "agent_outputs.orchestrator.actions": 1,
                "agent_outputs.orchestrator.risk_flags": 1,
                "agent_outputs.investment.recommendation": 1,
                "agent_outputs.risk.recommendation": 1,
                "agent_outputs.tax.recommendation": 1,
                "macro_snapshot.markets.nifty50": 1,
                "macro_snapshot.inflation.cpi_yoy": 1,
                "macro_snapshot.interest_rates.rbi_repo_rate": 1,
            },
        ).sort("timestamp", DESCENDING).limit(limit)
        meetings = await cursor.to_list(length=limit)

        summaries = []
        for m in meetings:
            orch = m.get("agent_outputs", {}).get("orchestrator", {})
            summaries.append({
                "meeting_id": m.get("meeting_id"),
                "timestamp": m.get("timestamp"),
                "board_verdict": orch.get("recommendation", ""),
                "narrative": orch.get("reasoning", ""),
                "actions_decided": [
                    a.get("action", "") for a in orch.get("actions", [])[:5]
                ],
                "risk_flags": orch.get("risk_flags", []),
                "agent_summaries": {
                    "investment": m.get("agent_outputs", {}).get("investment", {}).get("recommendation", ""),
                    "risk": m.get("agent_outputs", {}).get("risk", {}).get("recommendation", ""),
                    "tax": m.get("agent_outputs", {}).get("tax", {}).get("recommendation", ""),
                },
                "macro_at_time": {
                    "nifty50": m.get("macro_snapshot", {}).get("markets", {}).get("nifty50"),
                    "cpi": m.get("macro_snapshot", {}).get("inflation", {}).get("cpi_yoy"),
                    "repo_rate": m.get("macro_snapshot", {}).get("interest_rates", {}).get("rbi_repo_rate"),
                },
            })
        return summaries

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

    # ── Broker Connections ──

    async def save_broker_connection(self, user_id: str, broker_id: str, token_data: dict) -> None:
        """
        Store broker credentials for a user.
        Each user document has a 'brokers' dict keyed by broker_id.
        Token data is stored as-is; in production this should be encrypted
        using GCP Secret Manager or a KMS key.
        """
        token_data["saved_at"] = datetime.utcnow().isoformat()
        await self.db.broker_connections.update_one(
            {"user_id": user_id},
            {"$set": {f"brokers.{broker_id}": token_data, "user_id": user_id}},
            upsert=True,
        )

    async def get_broker_connections(self, user_id: str) -> dict:
        """
        Get all broker token_data dicts for this user.
        Returns: { broker_id: token_data_dict }
        """
        doc = await self.db.broker_connections.find_one({"user_id": user_id}, {"_id": 0})
        if doc:
            return doc.get("brokers", {})
        return {}

    async def remove_broker_connection(self, user_id: str, broker_id: str) -> None:
        """Remove a specific broker's credentials."""
        await self.db.broker_connections.update_one(
            {"user_id": user_id},
            {"$unset": {f"brokers.{broker_id}": ""}},
        )


# Shared global database connection instance
db = MongoMemory()
