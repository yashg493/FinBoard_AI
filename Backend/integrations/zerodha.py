"""
Zerodha Kite Connect Broker Integration.

Auth Type: OAuth (per-day login flow)
  Flow:
    1. Redirect user → https://kite.zerodha.com/connect/login?v=3&api_key=...
    2. User logs in + 2FA → redirected to our callback with ?request_token=...
    3. Backend exchanges request_token for access_token (SHA-256 checksum required)
    4. access_token valid for that calendar day only
    5. Next day: user clicks "Reconnect" to repeat step 1

API Base: https://api.kite.trade
Python SDK: kiteconnect (pip install kiteconnect)

Key Endpoints:
  GET /portfolio/holdings  → long-term demat holdings
  GET /portfolio/positions → intraday / F&O positions
  GET /user/margins        → cash, margin
  
Reference: https://kite.trade/docs/connect/v3/
"""
import hashlib
import logging
import os
import time
from typing import Optional

import httpx

from integrations.base_broker import BaseBroker, BrokerHolding

logger = logging.getLogger("boardroom-ai")

ZERODHA_BASE_URL  = "https://api.kite.trade"
ZERODHA_LOGIN_URL = "https://kite.zerodha.com/connect/login"

# From env (set these in .env after creating a Kite Connect app at developers.kite.trade)
KITE_API_KEY    = os.getenv("KITE_API_KEY", "")
KITE_API_SECRET = os.getenv("KITE_API_SECRET", "")


class ZerodhaBroker(BaseBroker):
    BROKER_ID   = "zerodha"
    BROKER_NAME = "Zerodha Kite"
    BROKER_LOGO = "🟠"
    AUTH_TYPE   = "oauth"   # Full OAuth redirect flow

    def get_login_url(self, redirect_uri: str = "") -> str:
        """
        Return the Zerodha login URL.
        User is redirected here; after login Zerodha sends them back to
        our /api/broker/zerodha/callback?request_token=... endpoint.
        """
        if not KITE_API_KEY:
            raise ValueError("KITE_API_KEY not set in environment. Get one at developers.kite.trade")
        return f"{ZERODHA_LOGIN_URL}?v=3&api_key={KITE_API_KEY}"

    async def exchange_token(self, request_token: str, **kwargs) -> dict:
        """
        Exchange the request_token (from OAuth callback) for an access_token.
        Zerodha requires a SHA-256 checksum: hash(api_key + request_token + api_secret)
        """
        if not KITE_API_KEY or not KITE_API_SECRET:
            raise ValueError("KITE_API_KEY and KITE_API_SECRET must be set in .env")

        # Compute checksum as per Kite Connect spec
        checksum_raw = f"{KITE_API_KEY}{request_token}{KITE_API_SECRET}"
        checksum = hashlib.sha256(checksum_raw.encode()).hexdigest()

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{ZERODHA_BASE_URL}/session/token",
                data={
                    "api_key":       KITE_API_KEY,
                    "request_token": request_token,
                    "checksum":      checksum,
                },
                headers={"X-Kite-Version": "3"},
            )
            if resp.status_code != 200:
                raise ValueError(f"Zerodha token exchange failed: {resp.text}")

            data = resp.json().get("data", {})

        return {
            "broker_id":     self.BROKER_ID,
            "api_key":       KITE_API_KEY,
            "access_token":  data.get("access_token", ""),
            "user_id":       data.get("user_id", ""),
            "user_name":     data.get("user_name", "Zerodha User"),
            "user_email":    data.get("email", ""),
            "generated_at":  time.time(),
        }

    async def fetch_holdings(self, token_data: dict) -> list[BrokerHolding]:
        """
        Fetch long-term demat holdings from Zerodha Kite.

        Zerodha response format:
        {
          "data": [
            {
              "tradingsymbol": "RELIANCE",
              "exchange": "NSE",
              "isin": "INE002A01018",
              "quantity": 50,
              "average_price": 2800.0,
              "last_price": 2942.5,
              "pnl": 7125.0,
              "day_change": 12.3,
              "day_change_percentage": 0.42,
              ...
            }
          ]
        }
        """
        api_key      = token_data.get("api_key", KITE_API_KEY)
        access_token = token_data.get("access_token", "")

        headers = {
            "X-Kite-Version": "3",
            "Authorization":  f"token {api_key}:{access_token}",
        }

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{ZERODHA_BASE_URL}/portfolio/holdings",
                headers=headers,
            )
            if resp.status_code == 403:
                raise ValueError("Zerodha session expired. Please reconnect (Kite tokens expire daily).")
            resp.raise_for_status()

        raw = resp.json()
        holdings_raw = raw.get("data", [])

        normalized = []
        for h in holdings_raw:
            qty = float(h.get("quantity", 0))
            if qty <= 0:
                continue

            normalized.append(BrokerHolding(
                symbol    = h.get("tradingsymbol", ""),
                name      = h.get("tradingsymbol", ""),   # Kite doesn't return company name in holdings
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
        Fetch available margin/cash from Zerodha.
        Zerodha splits margins into equity and commodity segments.
        """
        api_key      = token_data.get("api_key", KITE_API_KEY)
        access_token = token_data.get("access_token", "")
        headers = {
            "X-Kite-Version": "3",
            "Authorization":  f"token {api_key}:{access_token}",
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{ZERODHA_BASE_URL}/user/margins",
                    headers=headers,
                )
                resp.raise_for_status()
                margins = resp.json().get("data", {})
                equity  = margins.get("equity", {})
                return {
                    "available_cash": float(equity.get("available", {}).get("live_balance", 0)),
                    "used_margin":    float(equity.get("utilised", {}).get("debits", 0)),
                    "total_balance":  float(equity.get("net", 0)),
                }
        except Exception as e:
            logger.warning(f"[zerodha] Funds fetch failed: {e}")
            return {"available_cash": 0, "used_margin": 0, "total_balance": 0}
