"""
Investment Agent — Portfolio allocation, market exposure,
and investment optimization for Boardroom AI.
"""
from agents.base_agent import AgentOutput, BaseAgent

INVESTMENT_SYSTEM_PROMPT = """
You are the Investment Agent for Boardroom AI, an autonomous financial governance system.

Your expertise:
- Portfolio allocation optimization (equity, debt, gold, real estate, cash)
- Market exposure management (domestic vs international, sector weights)
- Risk-adjusted return optimization
- Defensive vs aggressive positioning based on macroeconomic regime
- India-specific investment vehicles: Nifty 50, ELSS, PPF, NPS, SGBs, FDs
- SIP (Systematic Investment Plan) optimization

Your personality: Evidence-driven, quantitative, forward-looking. 
Challenge conservative thinking when data supports growth opportunities.
Challenge aggressive positions when risk is elevated.

Always return valid JSON only.
"""


class InvestmentAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name="Investment Agent",
            system_prompt=INVESTMENT_SYSTEM_PROMPT,
        )

    def build_prompt(self, user_profile: dict, macro_data: dict, context: dict) -> str:
        portfolio = user_profile.get("portfolio", {})
        current_allocation = portfolio.get("allocation", {})
        sip_amount = user_profile.get("sip_monthly", 0)
        risk_tolerance = user_profile.get("risk_tolerance", "moderate")

        return f"""
Analyze the current macroeconomic environment and provide investment portfolio recommendations.

CURRENT MACROECONOMIC CONDITIONS:
- Inflation (CPI YoY): {macro_data.get('inflation', {}).get('cpi_yoy', 'N/A')}%
- RBI Repo Rate: {macro_data.get('interest_rates', {}).get('rbi_repo_rate', 'N/A')}%
- 10Y G-Sec Yield: {macro_data.get('interest_rates', {}).get('10yr_gsec_yield', 'N/A')}%
- Nifty 50 Monthly Change: {macro_data.get('markets', {}).get('nifty_change_1m', 'N/A')}%
- India VIX: {macro_data.get('markets', {}).get('vix_india', 'N/A')}
- GDP Growth: {macro_data.get('growth', {}).get('gdp_growth_yoy', 'N/A')}%
- USD/INR: {macro_data.get('currency', {}).get('usd_inr', 'N/A')}
- Global Recession Probability: {macro_data.get('global', {}).get('global_recession_probability', 'N/A')}

USER INVESTMENT PROFILE:
- Portfolio Value: ₹{portfolio.get('total_value', 0):,}
- Monthly SIP: ₹{sip_amount:,}
- Risk Tolerance: {risk_tolerance}
- Investment Horizon: {user_profile.get('investment_horizon_years', 10)} years
- Age: {user_profile.get('age', 'N/A')}

CURRENT ALLOCATION:
{current_allocation}

CONTEXT / TRIGGER: {context}

Provide investment recommendations in this EXACT JSON format:
{{
  "market_regime": "<BULL|BEAR|SIDEWAYS|VOLATILE>",
  "positioning": "<AGGRESSIVE|MODERATE|DEFENSIVE|CASH_HEAVY>",
  "recommendation": "<1-2 sentence executive summary>",
  "reasoning": "<detailed analysis referencing macro data>",
  "confidence": <0.0-1.0>,
  "proposed_allocation": {{
    "large_cap_equity": <percent>,
    "mid_small_cap_equity": <percent>,
    "international_equity": <percent>,
    "debt_funds": <percent>,
    "gold_sgb": <percent>,
    "fd_liquid": <percent>,
    "real_estate_reit": <percent>
  }},
  "allocation_changes": [
    {{
      "asset": "<asset name>",
      "current_pct": <current %>,
      "proposed_pct": <proposed %>,
      "change_pct": <delta>,
      "action": "<INCREASE|DECREASE|HOLD>",
      "rationale": "<why>"
    }}
  ],
  "sip_recommendation": {{
    "current_sip": {sip_amount},
    "recommended_sip": <amount>,
    "sip_changes": [
      {{"fund_type": "<type>", "current": <amount>, "proposed": <amount>, "reason": "<why>"}}
    ]
  }},
  "risk_flags": ["<flag1>", "<flag2>"],
  "priority_actions": [
    {{"action": "<action>", "urgency": "<HIGH|MED|LOW>", "impact": "<expected impact>"}}
  ]
}}
"""

    def parse_output(self, raw: str) -> AgentOutput:
        data = self._safe_parse_json(raw)

        allocation_changes = data.get("allocation_changes", [])
        priority_actions = data.get("priority_actions", [])

        all_actions = []
        for change in allocation_changes:
            all_actions.append({
                "type": "ALLOCATION_CHANGE",
                "asset": change.get("asset"),
                "action": change.get("action"),
                "current_pct": change.get("current_pct"),
                "proposed_pct": change.get("proposed_pct"),
                "rationale": change.get("rationale"),
            })

        for action in priority_actions:
            all_actions.append({
                "type": "PRIORITY_ACTION",
                "action": action.get("action"),
                "urgency": action.get("urgency"),
                "impact": action.get("impact"),
            })

        return AgentOutput(
            agent_name=self.agent_name,
            recommendation=data.get("recommendation", "No recommendation"),
            reasoning=data.get("reasoning", ""),
            confidence=self._clamp_confidence(data.get("confidence", 0.7)),
            actions=all_actions,
            risk_flags=data.get("risk_flags", []),
        )
