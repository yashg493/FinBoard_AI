"""
Risk Agent — Emergency fund analysis, layoff risk assessment,
recession stress testing, and debt pressure analysis.
"""
from agents.base_agent import AgentOutput, BaseAgent

RISK_SYSTEM_PROMPT = """
You are the Risk Agent for Boardroom AI, an autonomous financial governance system.

Your expertise:
- Emergency fund adequacy analysis (target: 6-12 months of expenses)
- Layoff risk assessment based on sector, company, and macroeconomic signals
- Recession stress testing: portfolio drawdown, income disruption, EMI pressure
- Debt sustainability: EMI-to-income ratio, debt paydown prioritization
- Insurance coverage gaps (term, health, disability)
- India-specific risks: INR depreciation, inflation erosion, regulatory changes

Your personality: Cautious, scenario-focused, stress-tester.
Your job is to find the worst-case scenarios and quantify them.
Challenge optimistic projections. Always ask: "What if it goes wrong?"

Always return valid JSON only. Be specific with numbers.
"""


class RiskAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name="Risk Agent",
            system_prompt=RISK_SYSTEM_PROMPT,
        )

    def build_prompt(self, user_profile: dict, macro_data: dict, context: dict, meeting_transcript: str = None) -> str:
        monthly_expenses = user_profile.get("monthly_expenses", 0)
        emergency_fund = user_profile.get("emergency_fund_months", 0)
        monthly_income = user_profile.get("monthly_income", 0)
        emis = user_profile.get("emis", [])
        total_emi = sum(e.get("amount", 0) for e in emis)
        emi_ratio = (total_emi / monthly_income * 100) if monthly_income else 0
        sector = user_profile.get("employer_sector", "Unknown")

        return f"""
You are the Risk Management Agent in an AI Financial Board meeting. Your role is to provide highly analytical, data-backed risk assessments.

CRITICAL INSTRUCTIONS:
1. YOU MUST USE SPECIFIC NUMBERS. Calculate exact INR drawdown amounts and exact runway months based on the user's income and portfolio.
2. USE STATISTICAL FRAMEWORKS: Reference specific risk models (e.g., Value at Risk (VaR), Stress Testing scenarios, Safe Withdrawal Rates).
3. ENGAGE WITH THE TRANSCRIPT: If there is an ongoing meeting transcript, you MUST directly address points made by other agents. For example, if the Investment Agent recommends buying equities, you MUST calculate the risk of that exact move.

MEETING TRANSCRIPT SO FAR:
{meeting_transcript or "Meeting has just started. You are the first to speak."}

MACROECONOMIC RISK SIGNALS:
- Unemployment Rate: {macro_data.get('employment', {}).get('cmie_unemployment', 'N/A')}%
- GDP Growth: {macro_data.get('growth', {}).get('gdp_growth_yoy', 'N/A')}%
- Global Recession Probability: {macro_data.get('global', {}).get('global_recession_probability', 0) * 100:.0f}%
- Inflation (eroding purchasing power): {macro_data.get('inflation', {}).get('cpi_yoy', 'N/A')}%
- Market Drawdown (1M): {macro_data.get('markets', {}).get('nifty_change_1m', 'N/A')}%
- Crude Oil Price: ${macro_data.get('global', {}).get('crude_oil_brent', 'N/A')}

USER RISK PROFILE:
- Monthly Income: ₹{monthly_income:,}
- Monthly Expenses: ₹{monthly_expenses:,}
- Emergency Fund: {emergency_fund} months (target: 6-12 months)
- Emergency Fund Value: ₹{emergency_fund * monthly_expenses:,}
- Total EMI Burden: ₹{total_emi:,}/month ({emi_ratio:.1f}% of income)
- EMI Details: {emis}
- Employer Sector: {sector}
- Portfolio Value: ₹{user_profile.get('portfolio', {}).get('total_value', 0):,}
- Portfolio Holdings (Enriched): {user_profile.get('portfolio', {}).get('holdings', [])}
- Insurance Coverage: {user_profile.get('insurance', {})}

CONTEXT / TRIGGER: {context}

Return comprehensive risk assessment in EXACT JSON format:
{{
  "overall_risk_level": "<LOW|MODERATE|HIGH|CRITICAL>",
  "risk_score": <1-10>,
  "recommendation": "<1-2 sentence risk executive summary>",
  "reasoning": "<Deep analytical reasoning. MUST include statistical risk calculations and exact INR numbers. MUST address points from the Meeting Transcript.>",
  "confidence": <0.0-1.0>,
  "emergency_fund_analysis": {{
    "current_months": {emergency_fund},
    "target_months": <recommended months given context>,
    "gap_months": <gap>,
    "gap_amount_inr": <amount in INR needed>,
    "adequacy": "<CRITICAL|INSUFFICIENT|ADEQUATE|STRONG>",
    "monthly_top_up_needed": <amount per month to reach target in 6 months>
  }},
  "layoff_risk": {{
    "probability": <0.0-1.0>,
    "sector_outlook": "<sector risk narrative>",
    "income_disruption_scenario": {{
      "months_to_financial_stress": <months>,
      "runway_with_emergency_fund": <months>,
      "portfolio_liquidation_needed": <true/false>
    }}
  }},
  "recession_stress_test": {{
    "portfolio_drawdown_30pct": {{
      "new_value": <INR>,
      "impact": "<narrative>"
    }},
    "portfolio_drawdown_50pct": {{
      "new_value": <INR>,
      "impact": "<narrative>"
    }},
    "sector_correlation_stress": {{
      "vulnerable_sectors": ["<sector>"],
      "correlation_impact_inr": <INR>,
      "narrative": "<analysis based on holdings>"
    }},
    "income_loss_scenario": {{
      "months_coverage": <months>,
      "emi_stress_months": <how many months EMIs can be paid>
    }}
  }},
  "debt_analysis": {{
    "emi_to_income_ratio": {emi_ratio:.1f},
    "safe_threshold_pct": 40,
    "status": "<SAFE|ELEVATED|STRESSED|CRITICAL>",
    "high_priority_paydown": [
      {{"loan_type": "<type>", "balance": <INR>, "rate_pct": <rate>, "action": "<action>"}}
    ]
  }},
  "insurance_gaps": [
    {{"type": "<insurance type>", "current_cover": "<amount>", "recommended": "<amount>", "urgency": "<HIGH|MED|LOW>"}}
  ],
  "risk_flags": ["<flag1>", "<flag2>"],
  "priority_actions": [
    {{"action": "<action>", "urgency": "<HIGH|MED|LOW>", "impact": "<impact>", "timeline": "<when>"}}
  ]
}}
"""

    def parse_output(self, raw: str) -> AgentOutput:
        data = self._safe_parse_json(raw)

        actions = []
        for item in data.get("priority_actions", []):
            actions.append({
                "type": "RISK_ACTION",
                "action": item.get("action"),
                "urgency": item.get("urgency"),
                "impact": item.get("impact"),
                "timeline": item.get("timeline"),
            })

        # Include stress test as structured action
        stress_test = data.get("recession_stress_test", {})
        if stress_test:
            actions.append({
                "type": "STRESS_TEST_RESULT",
                "drawdown_30pct_impact": stress_test.get("portfolio_drawdown_30pct", {}),
                "drawdown_50pct_impact": stress_test.get("portfolio_drawdown_50pct", {}),
            })

        return AgentOutput(
            agent_name=self.agent_name,
            recommendation=data.get("recommendation", "Risk assessment unavailable"),
            reasoning=data.get("reasoning", ""),
            confidence=self._clamp_confidence(data.get("confidence", 0.75)),
            actions=actions,
            risk_flags=data.get("risk_flags", []),
        )
