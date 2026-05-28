"""
Tax Agent — Capital gains optimization, tax-loss harvesting,
transaction timing, and tax-efficient restructuring for Indian tax regime.
"""
from agents.base_agent import AgentOutput, BaseAgent

TAX_SYSTEM_PROMPT = """
You are the Tax Agent for Boardroom AI, an autonomous financial governance system.

Your expertise (India-specific):
- Income Tax Act 1961: Section 80C, 80D, 80CCD(1B), 24(b)
- Capital Gains Tax:
  * Equity LTCG: 12.5% above ₹1.25 lakh (post-Budget 2024)
  * Equity STCG: 20%
  * Debt LTCG: Slab rates (post-2023)
  * Indexation benefits for real estate
- Tax-loss harvesting: timing sales to offset gains
- Old vs New Tax Regime optimization
- NPS (National Pension System): additional ₹50,000 deduction
- ELSS: ₹1.5 lakh deduction under 80C, 3-year lock-in
- HRA, LTA, Standard Deduction optimization
- Dividend vs Growth option tax implications
- STT (Securities Transaction Tax), LTCG grandfathering (Jan 31, 2018 base)

Your personality: Precise, compliance-focused, tax-minimization oriented.
Always flag compliance risks. Never suggest illegal tax evasion.

Return valid JSON only.
"""


class TaxAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name="Tax Agent",
            system_prompt=TAX_SYSTEM_PROMPT,
        )

    def build_prompt(self, user_profile: dict, macro_data: dict, context: dict, meeting_transcript: str = None) -> str:
        tax_regime = user_profile.get("tax_regime", "new")
        months_to_fy_end = user_profile.get("months_to_fy_end", 12)
        monthly_income = user_profile.get("monthly_income", 0)
        annual_income = monthly_income * 12
        portfolio = user_profile.get("portfolio", {})
        unrealized_gains = portfolio.get("unrealized_gains", {})
        deductions_used = user_profile.get("deductions_used", {})

        return f"""
You are the Tax Optimization Agent in an AI Financial Board meeting. Your role is to provide highly analytical, data-backed tax strategies based on Indian Tax Laws.

CRITICAL INSTRUCTIONS:
1. YOU MUST USE SPECIFIC NUMBERS. Calculate exact INR tax liabilities, exact savings from Sections like 80C/80CCD(1B), and exact capital gains tax (LTCG/STCG).
2. USE SPECIFIC TAX STRATEGIES: Reference Tax-Loss Harvesting, Income Splitting, and optimal Asset Location.
3. ENGAGE WITH THE TRANSCRIPT: If there is an ongoing meeting transcript, you MUST directly address points made by other agents. If the Investment Agent suggests selling a stock, you MUST calculate the exact tax implication of that sale.

MEETING TRANSCRIPT SO FAR:
{meeting_transcript or "Meeting has just started. You are the first to speak."}

MACROECONOMIC CONTEXT:
- Current Nifty 50 Level: {macro_data.get('markets', {}).get('nifty50', 'N/A')}
- Market Trend (1M): {macro_data.get('markets', {}).get('nifty_change_1m', 'N/A')}%
- Interest Rates (FD rates affected): {macro_data.get('interest_rates', {}).get('rbi_repo_rate', 'N/A')}%
- Inflation (real return impact): {macro_data.get('inflation', {}).get('cpi_yoy', 'N/A')}%

USER TAX PROFILE:
- Annual Gross Income: ₹{income:,}
- Tax Regime: {tax_regime.upper()}
- Months to Financial Year End (March 31): {fy_end_months}
- Monthly SIP Amount: ₹{user_profile.get('sip_monthly', 0):,}

DEDUCTIONS UTILIZED (FY so far):
{deductions_used}

PORTFOLIO UNREALIZED GAINS/LOSSES:
{unrealized_gains}

PORTFOLIO HOLDINGS (Enriched with Live Prices and P&L):
{portfolio.get('holdings', [])}

CONTEXT / TRIGGER: {context}

Provide comprehensive tax optimization in EXACT JSON format:
{{
  "tax_regime_recommendation": {{
    "current_regime": "{tax_regime}",
    "recommended_regime": "<old|new>",
    "estimated_tax_saving": <INR>,
    "reasoning": "<why switch or stay>"
  }},
  "recommendation": "<1-2 sentence tax executive summary>",
  "reasoning": "<Deep analytical reasoning. MUST include exact INR tax calculations and specific section references. MUST address points from the Meeting Transcript.>",
  "confidence": <0.0-1.0>,
  "deduction_optimization": {{
    "80C": {{
      "limit": 150000,
      "used": <amount>,
      "remaining": <amount>,
      "recommended_instruments": [
        {{"instrument": "<ELSS|PPF|EPF|NSC>", "amount": <INR>, "reason": "<why>"}}
      ]
    }},
    "80CCD1B": {{
      "limit": 50000,
      "used": <amount>,
      "remaining": <amount>,
      "nps_recommendation": "<action>"
    }},
    "80D": {{
      "limit": <limit based on age>,
      "used": <amount>,
      "remaining": <amount>
    }},
    "total_additional_savings_possible": <INR>
  }},
  "capital_gains_strategy": {{
    "total_realized_ltcg": <INR>,
    "ltcg_exempt_used": <amount of ₹1.25L used>,
    "ltcg_tax_liability": <INR>,
    "stcg_liability": <INR>,
    "harvesting_opportunities": [
      {{
        "holding": "<fund/stock name>",
        "action": "<HARVEST_LOSS|BOOK_LTCG|HOLD>",
        "unrealized_pnl": <INR>,
        "tax_impact": <INR saved/owed>,
        "reasoning": "<why now>"
      }}
    ]
  }},
  "transaction_timing": {{
    "avoid_before": "<date if any>",
    "optimal_window": "<timing recommendation>",
    "fy_end_actions": [
      {{"action": "<action>", "deadline": "<date>", "tax_saving": <INR>}}
    ]
  }},
  "risk_flags": ["<compliance risk or flag>"],
  "priority_actions": [
    {{"action": "<action>", "urgency": "<HIGH|MED|LOW>", "tax_saving": <INR>, "deadline": "<date or timeframe>"}}
  ]
}}
"""

    def parse_output(self, raw: str) -> AgentOutput:
        data = self._safe_parse_json(raw)

        actions = []
        for item in data.get("priority_actions", []):
            actions.append({
                "type": "TAX_ACTION",
                "action": item.get("action"),
                "urgency": item.get("urgency"),
                "tax_saving": item.get("tax_saving"),
                "deadline": item.get("deadline"),
            })

        # Harvesting opportunities as actions
        for opp in data.get("capital_gains_strategy", {}).get("harvesting_opportunities", []):
            if opp.get("action") in ["HARVEST_LOSS", "BOOK_LTCG"]:
                actions.append({
                    "type": "HARVESTING_OPPORTUNITY",
                    "holding": opp.get("holding"),
                    "action": opp.get("action"),
                    "tax_impact": opp.get("tax_impact"),
                    "reasoning": opp.get("reasoning"),
                })

        return AgentOutput(
            agent_name=self.agent_name,
            recommendation=data.get("recommendation", "Tax analysis unavailable"),
            reasoning=data.get("reasoning", ""),
            confidence=self._clamp_confidence(data.get("confidence", 0.8)),
            actions=actions,
            risk_flags=data.get("risk_flags", []),
        )
