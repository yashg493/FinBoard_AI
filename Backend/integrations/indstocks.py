"""
INDstocks Broker Integration (INDmoney's trading platform).

Auth Type: Token-based (no OAuth)
  - User generates token at: https://indstocks.com/app/api-trading
  - Token is valid for 24 hours
  - User pastes token into FinBoard once → auto-refreshes prompt when expired

API Base: https://api.indstocks.com
Key Endpoints:
  GET /portfolio/holdings  → equity holdings
  GET /portfolio/positions → intraday/F&O positions  
  GET /user/funds          → cash balance, margin

Reference: https://api-docs.indstocks.com
"""
import asyncio
import logging
import os
import time
from typing import Optional

import httpx

from integrations.base_broker import BaseBroker, BrokerHolding

logger = logging.getLogger("boardroom-ai")

INDSTOCKS_BASE_URL = "https://api.indstocks.com"
INDSTOCKS_DOCS_URL = "https://indstocks.com/app/api-trading"


class INDstocksBroker(BaseBroker):
    BROKER_ID   = "indstocks"
    BROKER_NAME = "INDmoney (INDstocks)"
    BROKER_LOGO = "🟦"
    AUTH_TYPE   = "token"   # User pastes API token — no OAuth redirect needed

    def get_login_url(self, redirect_uri: str = "") -> str:
        """
        INDstocks uses manual token generation, not OAuth.
        Returns the URL where users can generate their token.
        """
        return INDSTOCKS_DOCS_URL

    async def exchange_token(self, request_token: str, **kwargs) -> dict:
        """
        For INDstocks, 'exchange_token' means: validate the pasted token
        by making a test API call. If it works, store it.
        request_token here IS the actual Bearer token the user copied.
        """
        # Validate the token by fetching profile
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{INDSTOCKS_BASE_URL}/user/profile",
                    headers={"Authorization": f"Bearer {request_token}"},
                )
                if resp.status_code == 401:
                    raise ValueError("Invalid INDstocks token. Please regenerate from indstocks.com/app/api-trading")
                if resp.status_code != 200:
                    raise ValueError(f"INDstocks API error: {resp.status_code}")

                profile = resp.json()
                user_name = profile.get("data", {}).get("user_name", "INDstocks User")
        except httpx.RequestError as e:
            # If the profile endpoint fails (some env issues), still store token
            # and let the holdings fetch reveal any real issues
            logger.warning(f"[indstocks] Profile validation skipped: {e}")
            user_name = "INDstocks User"

        return {
            "broker_id":     self.BROKER_ID,
            "access_token":  request_token,
            "user_name":     user_name,
            "generated_at":  time.time(),
        }

    async def fetch_holdings(self, token_data: dict) -> list[BrokerHolding]:
        """
        Fetch equity holdings from INDstocks API.
        Returns normalized BrokerHolding list.

        INDstocks response format:
        {
          "data": [
            {
              "tradingsymbol": "RELIANCE",
              "exchange": "NSE",
              "isin": "INE002A01018",
              "quantity": 50,
              "average_price": 2800.00,
              "last_price": 2942.50,
              "company_name": "Reliance Industries Ltd",
              ...
            }
          ]
        }
        """
        token = token_data.get("access_token", "")
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{INDSTOCKS_BASE_URL}/portfolio/holdings",
                headers=headers,
            )
            if resp.status_code == 401:
                raise ValueError("INDstocks token expired. Please reconnect.")
            resp.raise_for_status()

        raw = resp.json()
        holdings_raw = raw.get("data", [])

        normalized = []
        for h in holdings_raw:
            qty = float(h.get("quantity", 0))
            if qty <= 0:
                continue  # skip zero-quantity holdings

            normalized.append(BrokerHolding(
                symbol    = h.get("tradingsymbol", ""),
                name      = h.get("company_name", h.get("tradingsymbol", "")),
                quantity  = qty,
                avg_cost  = float(h.get("average_price", 0)),
                ltp       = float(h.get("last_price", 0)),
                isin      = h.get("isin", ""),
                asset_type= "equity",
                exchange  = h.get("exchange", "NSE"),
            ))

        return normalized

    async def fetch_funds(self, token_data: dict) -> dict:
        """
        Fetch cash balance and margin from INDstocks.
        """
        token = token_data.get("access_token", "")
        headers = {"Authorization": f"Bearer {token}"}

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{INDSTOCKS_BASE_URL}/user/funds",
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json().get("data", {})
                return {
                    "available_cash": float(data.get("available_cash", 0)),
                    "used_margin":    float(data.get("used_margin", 0)),
                    "total_balance":  float(data.get("total_balance", 0)),
                }
        except Exception as e:
            logger.warning(f"[indstocks] Funds fetch failed: {e}")
            return {"available_cash": 0, "used_margin": 0, "total_balance": 0}
