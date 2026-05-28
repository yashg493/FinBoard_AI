"""
Sentinel Agent — Macroeconomic monitoring, anomaly detection,
and board meeting trigger logic.
"""
import asyncio
from typing import AsyncGenerator, Optional

import httpx

from agents.base_agent import AgentOutput, BaseAgent

SENTINEL_SYSTEM_PROMPT = """
You are the Sentinel Agent for Boardroom AI, a financial governance system.

Your role:
- Monitor macroeconomic indicators (inflation, interest rates, unemployment, GDP)
- Detect significant anomalies or regime changes
- Assess the severity of macroeconomic events on a 1-10 scale
- Generate concise, factual alerts that trigger board meetings
- Classify event type: INTEREST_RATE, INFLATION, RECESSION, MARKET_CRASH, EMPLOYMENT

Always respond in valid JSON matching the schema provided.
Be conservative: only trigger HIGH severity (≥7) for genuinely significant events.
"""


class SentinelAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name="Sentinel Agent",
            system_prompt=SENTINEL_SYSTEM_PROMPT,
        )
        self._macro_cache = {}
        self._cache_ttl = 300  # 5 minutes

    def build_prompt(self, user_profile: dict, macro_data: dict, context: dict) -> str:
        return f"""
Analyze the following macroeconomic snapshot and determine if it warrants a financial board meeting.

MACROECONOMIC DATA:
{macro_data}

USER FINANCIAL PROFILE SUMMARY:
- Monthly Income: {user_profile.get('monthly_income', 'unknown')}
- Portfolio Value: {user_profile.get('portfolio_value', 'unknown')}
- Risk Tolerance: {user_profile.get('risk_tolerance', 'moderate')}
- Country: {user_profile.get('country', 'India')}

CONTEXT (if any): {context}

Respond ONLY with a JSON object:
{{
  "trigger_board_meeting": <true/false>,
  "severity_score": <1-10>,
  "event_type": "<INTEREST_RATE|INFLATION|RECESSION|MARKET_CRASH|EMPLOYMENT|ROUTINE>",
  "alert_summary": "<1-2 sentence summary of the macroeconomic event>",
  "key_indicators": [
    {{"name": "<indicator>", "value": "<value>", "change": "<change>", "impact": "<LOW|MED|HIGH>"}}
  ],
  "reasoning": "<brief explanation of severity assessment>",
  "confidence": <0.0-1.0>,
  "recommended_mode": "<ADVISORY|COPILOT|AUTONOMOUS>"
}}
"""

    def parse_output(self, raw: str) -> AgentOutput:
        data = self._safe_parse_json(raw)
        return AgentOutput(
            agent_name=self.agent_name,
            recommendation=data.get("alert_summary", "Monitoring active"),
            reasoning=data.get("reasoning", ""),
            confidence=self._clamp_confidence(data.get("confidence", 0.7)),
            actions=[
                {
                    "action": "TRIGGER_BOARD_MEETING" if data.get("trigger_board_meeting") else "CONTINUE_MONITORING",
                    "severity": data.get("severity_score", 5),
                    "event_type": data.get("event_type", "ROUTINE"),
                    "key_indicators": data.get("key_indicators", []),
                    "recommended_mode": data.get("recommended_mode", "ADVISORY"),
                }
            ],
            risk_flags=["HIGH_SEVERITY"] if data.get("severity_score", 0) >= 7 else [],
        )

    async def fetch_macro_data(self) -> dict:
        """
        Fetch live macroeconomic data.
        In production: connect to Fivetran MCP / FRED API / RBI / NSE data.
        For demo: returns structured mock data + live fetches where possible.
        """
        return await self._fetch_india_macro()

    async def _fetch_india_macro(self) -> dict:
        """
        Fetch India-specific macro data.
        Sources: RBI, MOSPI, NSE/BSE indices, FRED for global rates.
        Replace URLs with actual API endpoints + API keys.
        """
        # In production, wire these to real APIs:
        # - RBI API: https://rbi.org.in/scripts/PublicationsView.aspx
        # - FRED API: https://fred.stlouisfed.org/
        # - NSE: https://www.nseindia.com/api/
        # - Alpha Vantage / Twelve Data for market prices
        import time
        from datetime import datetime

        # Default fallback data
        macro = {
            "country": "India",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "inflation": {
                "cpi_yoy": 5.48,
                "core_inflation": 3.65,
                "food_inflation": 8.39,
                "trend": "declining",
            },
            "interest_rates": {
                "rbi_repo_rate": 6.50,
                "reverse_repo": 6.25,
                "10yr_gsec_yield": 6.82,
                "trend": "on_hold",
            },
            "employment": {
                "unemployment_rate": 7.8,
                "cmie_unemployment": 8.1,
                "urban_unemployment": 9.2,
                "trend": "stable",
            },
            "growth": {
                "gdp_growth_yoy": 7.3,
                "iip_growth": 5.0,
                "trend": "moderating",
            },
            "markets": {
                "nifty50": 24100,
                "sensex": 79800,
                "nifty_change_1m": -2.3,
                "vix_india": 13.5,
                "trend": "volatile",
            },
            "currency": {
                "usd_inr": 84.50,
                "change_ytd": -1.8,
            },
            "global": {
                "us_fed_rate": 5.25,
                "crude_oil_brent": 81.5,
                "global_recession_probability": 0.25,
            },
        }

        # Attempt to fetch live market data via yfinance
        def _fetch_live():
            import yfinance as yf
            try:
                # Nifty 50
                nifty = yf.Ticker("^NSEI").fast_info
                if hasattr(nifty, "last_price") and nifty.last_price:
                    macro["markets"]["nifty50"] = round(nifty.last_price, 2)
                    if hasattr(nifty, "previous_close") and nifty.previous_close:
                        macro["markets"]["nifty_change_1m"] = round((nifty.last_price - nifty.previous_close) / nifty.previous_close * 100, 2) # Approximating 1m change with daily change for demo
            except Exception:
                pass
            
            try:
                # Sensex
                sensex = yf.Ticker("^BSESN").fast_info
                if hasattr(sensex, "last_price") and sensex.last_price:
                    macro["markets"]["sensex"] = round(sensex.last_price, 2)
            except Exception:
                pass
                
            try:
                # India VIX
                vix = yf.Ticker("^INDIAVIX").fast_info
                if hasattr(vix, "last_price") and vix.last_price:
                    macro["markets"]["vix_india"] = round(vix.last_price, 2)
            except Exception:
                pass
                
            try:
                # USD/INR
                usdinr = yf.Ticker("INR=X").fast_info
                if hasattr(usdinr, "last_price") and usdinr.last_price:
                    macro["currency"]["usd_inr"] = round(usdinr.last_price, 2)
            except Exception:
                pass

        try:
            await asyncio.get_event_loop().run_in_executor(None, _fetch_live)
        except Exception as e:
            import logging
            logging.getLogger("boardroom-ai").warning(f"Failed to fetch live macro data: {e}")

        return macro

    async def watch_for_triggers(self) -> AsyncGenerator[dict, None]:
        """
        Continuous monitoring loop — yields trigger events.
        Use with Cloud Scheduler / Pub/Sub in production.
        """
        while True:
            macro_data = await self.fetch_macro_data()
            # Quick heuristic check before full LLM call
            if self._quick_severity_check(macro_data) >= 5:
                output = await self.analyze(
                    user_profile={},
                    macro_data=macro_data,
                    context={"source": "automated_watch"},
                )
                if output.actions[0].get("severity", 0) >= 6:
                    yield {
                        "type": "sentinel_alert",
                        "agent": self.agent_name,
                        "data": output.to_dict(),
                    }
            await asyncio.sleep(3600)  # Check every hour

    def _quick_severity_check(self, macro: dict) -> int:
        score = 0
        cpi = macro.get("inflation", {}).get("cpi_yoy", 0)
        if cpi > 7:
            score += 3
        elif cpi > 5.5:
            score += 1

        nifty_change = macro.get("markets", {}).get("nifty_change_1m", 0)
        if nifty_change < -5:
            score += 3
        elif nifty_change < -2:
            score += 1

        unemp = macro.get("employment", {}).get("cmie_unemployment", 0)
        if unemp > 10:
            score += 2

        return min(score, 10)
