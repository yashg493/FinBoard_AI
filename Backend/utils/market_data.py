"""
Market Data Utility — Live NSE/BSE price fetching via yfinance.
Enriches portfolio holdings with real-time LTP, day P&L, and computed metrics.

NSE tickers on yfinance use ".NS" suffix  (e.g. RELIANCE.NS)
BSE tickers use ".BO" suffix             (e.g. RELIANCE.BO)
"""
import asyncio
import logging
import time
from typing import Optional

logger = logging.getLogger("boardroom-ai")

# Cache to avoid hammering yfinance on every request
_price_cache: dict[str, dict] = {}
_CACHE_TTL = 60  # seconds


def _nse_ticker(symbol: str) -> str:
    """Convert plain symbol to NSE yfinance ticker."""
    symbol = symbol.upper().strip()
    if symbol.endswith(".NS") or symbol.endswith(".BO"):
        return symbol
    return f"{symbol}.NS"


async def fetch_live_price(symbol: str) -> dict:
    """
    Fetch live LTP and basic stats for a single NSE symbol.
    Returns dict with: ltp, prev_close, day_change_pct, volume, market_cap.
    Falls back to cached value if yfinance fails.
    """
    ticker = _nse_ticker(symbol)
    now = time.time()

    # Return cache if fresh
    if ticker in _price_cache and (now - _price_cache[ticker]["fetched_at"]) < _CACHE_TTL:
        return _price_cache[ticker]

    try:
        # Run blocking yfinance call in thread pool
        result = await asyncio.get_event_loop().run_in_executor(
            None, _fetch_yfinance, ticker
        )
        _price_cache[ticker] = result
        return result
    except Exception as e:
        logger.warning(f"[market_data] yfinance failed for {ticker}: {e}")
        # Return last cached price or zeros
        return _price_cache.get(ticker, {
            "symbol": symbol,
            "ticker": ticker,
            "ltp": 0,
            "prev_close": 0,
            "day_change": 0,
            "day_change_pct": 0,
            "volume": 0,
            "market_cap": 0,
            "error": str(e),
            "fetched_at": now,
        })


def _fetch_yfinance(ticker: str) -> dict:
    """Blocking yfinance fetch — run in executor."""
    import yfinance as yf

    t = yf.Ticker(ticker)
    info = t.fast_info  # faster than full .info

    ltp = getattr(info, "last_price", 0) or 0
    prev_close = getattr(info, "previous_close", 0) or 0
    day_change = ltp - prev_close if ltp and prev_close else 0
    day_change_pct = (day_change / prev_close * 100) if prev_close else 0

    return {
        "symbol": ticker.replace(".NS", "").replace(".BO", ""),
        "ticker": ticker,
        "ltp": round(ltp, 2),
        "prev_close": round(prev_close, 2),
        "day_change": round(day_change, 2),
        "day_change_pct": round(day_change_pct, 2),
        "volume": getattr(info, "three_month_average_volume", 0) or 0,
        "market_cap": getattr(info, "market_cap", 0) or 0,
        "fetched_at": time.time(),
    }


async def enrich_holdings_with_prices(holdings: list[dict]) -> list[dict]:
    """
    Takes a list of holding dicts and enriches each with live price data.
    Each holding should have: symbol, quantity, avg_cost (average buy price).
    Adds: ltp, current_value, unrealized_pnl, unrealized_pnl_pct, day_pnl.
    """
    if not holdings:
        return []

    # Fetch all prices in parallel
    tasks = [fetch_live_price(h["symbol"]) for h in holdings]
    prices = await asyncio.gather(*tasks, return_exceptions=True)

    enriched = []
    for holding, price_data in zip(holdings, prices):
        if isinstance(price_data, Exception):
            price_data = {"ltp": 0, "day_change_pct": 0}

        qty = holding.get("quantity", 0)
        avg_cost = holding.get("avg_cost", 0)
        ltp = price_data.get("ltp", 0)

        invested = qty * avg_cost
        current_value = qty * ltp
        unrealized_pnl = current_value - invested
        unrealized_pnl_pct = (unrealized_pnl / invested * 100) if invested else 0
        day_pnl = qty * price_data.get("day_change", 0)

        enriched.append({
            **holding,
            "ltp": ltp,
            "prev_close": price_data.get("prev_close", 0),
            "current_value": round(current_value, 2),
            "invested_value": round(invested, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "unrealized_pnl_pct": round(unrealized_pnl_pct, 2),
            "day_pnl": round(day_pnl, 2),
            "day_change_pct": price_data.get("day_change_pct", 0),
        })

    return enriched


async def compute_portfolio_summary(holdings: list[dict]) -> dict:
    """
    Compute aggregate portfolio metrics from enriched holdings.
    Returns total_value, total_invested, total_pnl, day_pnl, xirr_estimate.
    """
    enriched = await enrich_holdings_with_prices(holdings)

    total_value = sum(h.get("current_value", 0) for h in enriched)
    total_invested = sum(h.get("invested_value", 0) for h in enriched)
    total_pnl = total_value - total_invested
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested else 0
    day_pnl = sum(h.get("day_pnl", 0) for h in enriched)

    return {
        "holdings": enriched,
        "summary": {
            "total_value": round(total_value, 2),
            "total_invested": round(total_invested, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
            "day_pnl": round(day_pnl, 2),
            "holdings_count": len(enriched),
        },
    }


# Predefined common NSE large-cap tickers for autocomplete
COMMON_NSE_TICKERS = [
    {"symbol": "RELIANCE",   "name": "Reliance Industries",      "sector": "Energy"},
    {"symbol": "TCS",        "name": "Tata Consultancy Services", "sector": "IT"},
    {"symbol": "INFY",       "name": "Infosys",                   "sector": "IT"},
    {"symbol": "HDFCBANK",   "name": "HDFC Bank",                 "sector": "Banking"},
    {"symbol": "ICICIBANK",  "name": "ICICI Bank",                "sector": "Banking"},
    {"symbol": "SBIN",       "name": "State Bank of India",       "sector": "Banking"},
    {"symbol": "BHARTIARTL", "name": "Bharti Airtel",             "sector": "Telecom"},
    {"symbol": "ITC",        "name": "ITC Limited",               "sector": "FMCG"},
    {"symbol": "HINDUNILVR", "name": "Hindustan Unilever",        "sector": "FMCG"},
    {"symbol": "LT",         "name": "Larsen & Toubro",           "sector": "Infra"},
    {"symbol": "BAJFINANCE", "name": "Bajaj Finance",             "sector": "NBFC"},
    {"symbol": "AXISBANK",   "name": "Axis Bank",                 "sector": "Banking"},
    {"symbol": "KOTAKBANK",  "name": "Kotak Mahindra Bank",       "sector": "Banking"},
    {"symbol": "ASIANPAINT", "name": "Asian Paints",              "sector": "Chemicals"},
    {"symbol": "MARUTI",     "name": "Maruti Suzuki",             "sector": "Auto"},
    {"symbol": "WIPRO",      "name": "Wipro",                     "sector": "IT"},
    {"symbol": "HCLTECH",    "name": "HCL Technologies",          "sector": "IT"},
    {"symbol": "SUNPHARMA",  "name": "Sun Pharmaceutical",        "sector": "Pharma"},
    {"symbol": "TITAN",      "name": "Titan Company",             "sector": "Consumer"},
    {"symbol": "ULTRACEMCO", "name": "UltraTech Cement",          "sector": "Cement"},
    {"symbol": "ADANIENT",   "name": "Adani Enterprises",         "sector": "Conglomerate"},
    {"symbol": "ONGC",       "name": "ONGC",                      "sector": "Energy"},
    {"symbol": "NTPC",       "name": "NTPC",                      "sector": "Power"},
    {"symbol": "POWERGRID",  "name": "Power Grid Corp",           "sector": "Power"},
    {"symbol": "M&M",        "name": "Mahindra & Mahindra",       "sector": "Auto"},
    {"symbol": "NESTLEIND",  "name": "Nestle India",              "sector": "FMCG"},
    {"symbol": "DRREDDY",    "name": "Dr Reddy's Laboratories",   "sector": "Pharma"},
    {"symbol": "TECHM",      "name": "Tech Mahindra",             "sector": "IT"},
    {"symbol": "DIVISLAB",   "name": "Divi's Laboratories",       "sector": "Pharma"},
    {"symbol": "JSWSTEEL",   "name": "JSW Steel",                 "sector": "Metals"},
]
