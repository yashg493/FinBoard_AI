"""
Base Broker Interface — Abstract contract all broker integrations must implement.

Every broker integration must:
1. Implement fetch_holdings(token_data) → list[dict]
2. Implement fetch_funds(token_data) → dict
3. Define AUTH_TYPE: "token" | "oauth"
4. Define BROKER_ID, BROKER_NAME, BROKER_LOGO

This abstraction means the rest of the system never needs to know
whether it's talking to INDstocks or Zerodha — it calls the same methods.
"""
from abc import ABC, abstractmethod
from typing import Optional


class BrokerHolding:
    """Normalized holding that all brokers map their data to."""
    def __init__(
        self,
        symbol: str,
        name: str,
        quantity: float,
        avg_cost: float,
        ltp: float,
        isin: str = "",
        asset_type: str = "equity",
        exchange: str = "NSE",
        sector: str = "",
    ):
        self.symbol = symbol
        self.name = name
        self.quantity = quantity
        self.avg_cost = avg_cost
        self.ltp = ltp
        self.isin = isin
        self.asset_type = asset_type
        self.exchange = exchange
        self.sector = sector

    def to_dict(self) -> dict:
        invested = self.quantity * self.avg_cost
        current  = self.quantity * self.ltp
        pnl      = current - invested
        pnl_pct  = (pnl / invested * 100) if invested else 0
        return {
            "symbol":            self.symbol,
            "name":              self.name,
            "quantity":          self.quantity,
            "avg_cost":          round(self.avg_cost, 2),
            "ltp":               round(self.ltp, 2),
            "isin":              self.isin,
            "asset_type":        self.asset_type,
            "exchange":          self.exchange,
            "sector":            self.sector,
            "current_value":     round(current, 2),
            "invested_value":    round(invested, 2),
            "unrealized_pnl":    round(pnl, 2),
            "unrealized_pnl_pct": round(pnl_pct, 2),
        }


class BaseBroker(ABC):
    """
    Abstract base class for all broker integrations.
    Concrete brokers (INDstocks, Zerodha) implement this interface.
    """

    # Must be overridden in every subclass
    BROKER_ID:   str = ""
    BROKER_NAME: str = ""
    BROKER_LOGO: str = ""
    AUTH_TYPE:   str = "token"   # "token" | "oauth"

    @abstractmethod
    async def fetch_holdings(self, token_data: dict) -> list[BrokerHolding]:
        """
        Fetch all equity holdings from the broker.
        token_data: dict stored in MongoDB (access_token, api_key, etc.)
        Returns: list of normalized BrokerHolding objects.
        """
        pass

    @abstractmethod
    async def fetch_funds(self, token_data: dict) -> dict:
        """
        Fetch available cash/margin.
        Returns: { available_cash, used_margin, total_balance }
        """
        pass

    @abstractmethod
    def get_login_url(self, redirect_uri: str) -> str:
        """
        For OAuth brokers: return the URL to redirect the user to for login.
        For token brokers: return instructions URL.
        """
        pass

    @abstractmethod
    async def exchange_token(self, request_token: str, **kwargs) -> dict:
        """
        For OAuth brokers: exchange request_token for access_token.
        For token brokers: validate and store the pasted token.
        Returns: token_data dict to store in MongoDB.
        """
        pass

    def is_token_expired(self, token_data: dict) -> bool:
        """
        Check if stored token is expired and needs refresh.
        Default: tokens expire after 24h (both brokers follow this).
        """
        import time
        generated_at = token_data.get("generated_at", 0)
        return (time.time() - generated_at) > 82800  # 23h to be safe

    def broker_info(self) -> dict:
        return {
            "broker_id":   self.BROKER_ID,
            "broker_name": self.BROKER_NAME,
            "broker_logo": self.BROKER_LOGO,
            "auth_type":   self.AUTH_TYPE,
        }
