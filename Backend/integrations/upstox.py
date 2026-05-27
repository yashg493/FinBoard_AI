"""
Upstox Broker Integration — FREE API (no subscription fees).

Auth Type: OAuth2 (same flow as Zerodha but free)
  - Create a free app at: https://account.upstox.com/developer/apps
  - Redirect URL to register: http://localhost:8000/api/broker/upstox/callback
  - Postback URL: leave blank (optional)
  - No fees — completely free for personal use

API Base: https://api.upstox.com/v2
Key Endpoints:
  GET /portfolio/long-term-holdings  → demat holdings
  GET /mf/holdings                   → mutual fund holdings
  GET /user/get-funds-and-margin     → cash balance

Reference: https://upstox.com/developer/api-documentation/
"""
import logging
import os
import time

import httpx

from integrations.base_broker import BaseBroker, BrokerHolding

logger = logging.getLogger("boardroom-ai")

UPSTOX_BASE_URL  = "https://api.upstox.com/v2"
UPSTOX_AUTH_URL  = "https://api.upstox.com/v2/login/authorization/dialog"
UPSTOX_TOKEN_URL = "https://api.upstox.com/v2/login/authorization/token"

UPSTOX_API_KEY    = os.getenv("UPSTOX_API_KEY", "")
UPSTOX_API_SECRET = os.getenv("UPSTOX_API_SECRET", "")


class UpstoxBroker(BaseBroker):
    BROKER_ID   = "upstox"
    BROKER_NAME = "Upstox"
    BROKER_LOGO = "🟣"
    AUTH_TYPE   = "oauth"

    def get_login_url(self, redirect_uri: str = "") -> str:
        if not UPSTOX_API_KEY:
            raise ValueError("UPSTOX_API_KEY not set. Create a free app at account.upstox.com/developer/apps")
        callback = redirect_uri or "http://localhost:8000/api/broker/upstox/callback"
        return (
            f"{UPSTOX_AUTH_URL}"
            f"?response_type=code"
            f"&client_id={UPSTOX_API_KEY}"
            f"&redirect_uri={callback}"
        )

    async def exchange_token(self, request_token: str, **kwargs) -> dict:
        """Exchange Upstox authorization_code for access_token."""
        redirect_uri = kwargs.get("redirect_uri", "http://localhost:8000/api/broker/upstox/callback")

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                UPSTOX_TOKEN_URL,
                data={
                    "code":          request_token,
                    "client_id":     UPSTOX_API_KEY,
                    "client_secret": UPSTOX_API_SECRET,
                    "redirect_uri":  redirect_uri,
                    "grant_type":    "authorization_code",
                },
                headers={"Accept": "application/json"},
            )
            if resp.status_code != 200:
                raise ValueError(f"Upstox token exchange failed: {resp.text}")
            data = resp.json()

        return {
            "broker_id":     self.BROKER_ID,
            "access_token":  data.get("access_token", ""),
            "user_name":     data.get("user_name", "Upstox User"),
            "email":         data.get("email", ""),
            "generated_at":  time.time(),
        }

    async def fetch_holdings(self, token_data: dict) -> list[BrokerHolding]:
        """
        Fetch equity holdings from Upstox.
        Upstox response:
        {
          "data": [
            {
              "isin": "INE002A01018",
              "trading_symbol": "RELIANCE",
              "company_name": "Reliance Industries Ltd",
              "quantity": 50,
              "average_price": 2800.0,
              "last_price": 2942.5,
              "exchange": "NSE",
              ...
            }
          ]
        }
        """
        token = token_data.get("access_token", "")
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

        normalized = []

        # Equity holdings
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{UPSTOX_BASE_URL}/portfolio/long-term-holdings",
                headers=headers,
            )
            if resp.status_code == 401:
                raise ValueError("Upstox session expired. Please reconnect.")
            resp.raise_for_status()
            for h in resp.json().get("data", []):
                qty = float(h.get("quantity", 0))
                if qty <= 0:
                    continue
                normalized.append(BrokerHolding(
                    symbol    = h.get("trading_symbol", ""),
                    name      = h.get("company_name", h.get("trading_symbol", "")),
                    quantity  = qty,
                    avg_cost  = float(h.get("average_price", 0)),
                    ltp       = float(h.get("last_price", 0)),
                    isin      = h.get("isin", ""),
                    asset_type= "equity",
                    exchange  = h.get("exchange", "NSE"),
                ))

        return normalized

    async def fetch_funds(self, token_data: dict) -> dict:
        token = token_data.get("access_token", "")
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{UPSTOX_BASE_URL}/user/get-funds-and-margin?segment=SEC",
                    headers=headers,
                )
                resp.raise_for_status()
                equity = resp.json().get("data", {}).get("equity", {})
                return {
                    "available_cash": float(equity.get("available_margin", 0)),
                    "used_margin":    float(equity.get("used_margin", 0)),
                    "total_balance":  float(equity.get("net_margin", 0)),
                }
        except Exception as e:
            logger.warning(f"[upstox] Funds fetch failed: {e}")
            return {"available_cash": 0, "used_margin": 0, "total_balance": 0}
