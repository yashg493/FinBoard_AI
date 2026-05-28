"""
Orchestrator Agent — Aggregates specialist agent outputs, resolves conflicts,
computes disagreement scores, and generates consensus financial governance decisions.

This is the "CEO" of the AI Boardroom — it runs the debate loop and synthesizes
final recommendations.
"""
import asyncio
import time
from typing import AsyncGenerator

from agents.base_agent import AgentOutput, BaseAgent
from agents.investment_agent import InvestmentAgent
from agents.risk_agent import RiskAgent
from agents.sentinel import SentinelAgent
from agents.tax_agent import TaxAgent

ORCHESTRATOR_SYSTEM_PROMPT = """
You are the Orchestrator Agent for Boardroom AI, an autonomous financial governance system.

Your role: You are the Chairperson of the AI Financial Board.

You receive outputs from three specialist agents:
1. Investment Agent — portfolio optimization
2. Risk Agent — risk and emergency planning
3. Tax Agent — tax efficiency

Your job:
- Synthesize their recommendations into a unified governance decision
- Identify and resolve conflicts between agents
- Compute a disagreement score (0=full consensus, 10=strong conflict)
- Generate a final consensus recommendation
- Assign priority tiers to all actions
- Define the governance mode: ADVISORY, COPILOT, or AUTONOMOUS
- Assess overall financial health score (1-100)

Be decisive. When agents disagree, explain the resolution logic clearly.
Governance decisions should be clear, actionable, and explainable to a retail user.

Return valid JSON only.
"""


class OrchestratorAgent(BaseAgent):
    def __init__(self, user_id: str, memory):
        super().__init__(
            agent_name="Orchestrator",
            system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
        )
        self.user_id = user_id
        self.memory = memory
        self.investment_agent = InvestmentAgent()
        self.risk_agent = RiskAgent()
        self.tax_agent = TaxAgent()
        self.sentinel = SentinelAgent()

    def build_prompt(self, user_profile: dict, macro_data: dict, context: dict) -> str:
        meeting_transcript = context.get("meeting_transcript", "No transcript available.")
        sentinel_output = context.get("sentinel_output", {})

        return f"""
You are chairing the AI Financial Board meeting. Synthesize the FULL MEETING TRANSCRIPT into a unified board decision.

MEETING TRANSCRIPT:
{meeting_transcript}

PRIOR BOARD DECISIONS:
{context.get('prior_decisions', 'None')}

MACROECONOMIC TRIGGER:
{sentinel_output}

Synthesize the board discussion into a unified board decision in EXACT JSON format:
{{
  "board_verdict": "<detailed multi-paragraph decisive financial governance statement>",
  "financial_health_score": <1-100>,
  "governance_mode": "<ADVISORY|COPILOT|AUTONOMOUS>",
  "disagreement_score": <0-10>,
  "confidence": <0.0-1.0>,
  "conflicts": [
    {{
      "between": ["<Agent1>", "<Agent2>"],
      "conflict_description": "<what they disagree on>",
      "resolution": "<how you resolved it>",
      "resolution_reasoning": "<why>"
    }}
  ],
  "consensus_actions": [
    {{
      "tier": <1|2|3>,
      "action": "<specific action>",
      "domain": "<INVESTMENT|RISK|TAX|GOVERNANCE>",
      "urgency": "<IMMEDIATE|THIS_WEEK|THIS_MONTH|THIS_QUARTER>",
      "estimated_impact": "<financial impact in INR if applicable>",
      "responsible_agent": "<which agent owns this>",
      "requires_user_approval": <true/false>
    }}
  ],
  "holding_level_recommendations": [
    {{
      "symbol": "<symbol>",
      "action": "<action>",
      "reasoning": "<reasoning>"
    }}
  ],
  "per_agent_summary": {{
    "investment": "<summary>",
    "risk": "<summary>",
    "tax": "<summary>"
  }},
  "narrative": "<Detailed multi-paragraph board meeting narrative explaining the overall situation and decision, incorporating the reasoning of the agents>",
  "macroeconomic_outlook": "<brief macro regime description>",
  "next_review_trigger": "<what event or timeframe should trigger next board meeting>",
  "debate_summary": "<brief summary of agent debates and key points of agreement/disagreement>"
}}
"""

    def parse_output(self, raw: str) -> AgentOutput:
        data = self._safe_parse_json(raw)
        return AgentOutput(
            agent_name=self.agent_name,
            recommendation=data.get("board_verdict", "Board meeting concluded"),
            reasoning=data.get("narrative", ""),
            confidence=self._clamp_confidence(data.get("confidence", 0.8)),
            actions=data.get("consensus_actions", []),
            risk_flags=[c.get("conflict_description", "") for c in data.get("conflicts", [])],
        )

    async def run_board_meeting(
        self,
        user_profile: dict,
        macro_data: dict,
        context: dict = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Full board meeting flow: Sentinel → Parallel Agents → Debate Loop → Consensus.
        Yields streaming events for the frontend live UI.
        User constraints (stated goals, constraints) are injected into the context
        so all agents are aware of them during analysis.
        """
        context = context or {}
        meeting_id = f"meeting_{int(time.time())}"

        # Enrich user_profile with any live portfolio data passed in context
        if context.get("live_portfolio"):
            user_profile = {**user_profile, "portfolio": context["live_portfolio"]}

        # Attach user-stated constraints to profile for agent awareness
        if context.get("user_constraints"):
            user_profile = {**user_profile, "user_stated_constraints": context["user_constraints"]}

        from utils.observability import trace_board_meeting

        with trace_board_meeting(meeting_id, self.user_id):
            # ── Phase 1: Sentinel Analysis ──
            yield self._event("agent_thinking", "Sentinel Agent", "Analyzing macroeconomic conditions...")
            sentinel_output = await self.sentinel.analyze(user_profile, macro_data, context)
            yield self._event("agent_output", "Sentinel Agent", sentinel_output.recommendation,
                             data=sentinel_output.to_dict(), icon="sentinel")

            meeting_transcript = f"CHAIRPERSON (Orchestrator): The meeting has started. Sentinel reports the following macroeconomic conditions: {sentinel_output.recommendation}\n\n"

            # ── Phase 2: Sequential Round Table ──
            yield self._event("phase_start", "Board", "Sequential analysis initiated — agents deliberating in turn...")

            # 1. Investment Agent
            yield self._event("agent_thinking", "Investment Agent", "Analyzing portfolio and generating data-backed strategy...")
            investment_output = await self.investment_agent.analyze(user_profile, macro_data, context, meeting_transcript)
            transcript_entry = f"INVESTMENT AGENT: {investment_output.recommendation}\nReasoning: {investment_output.reasoning}\n\n"
            meeting_transcript += transcript_entry
            yield self._event("agent_output", "Investment Agent", investment_output.recommendation,
                             data=investment_output.to_dict(), icon="investment")

            # 2. Risk Agent
            yield self._event("agent_thinking", "Risk Agent", "Evaluating risks and reviewing Investment strategy...")
            risk_output = await self.risk_agent.analyze(user_profile, macro_data, context, meeting_transcript)
            transcript_entry = f"RISK AGENT: {risk_output.recommendation}\nReasoning: {risk_output.reasoning}\n\n"
            meeting_transcript += transcript_entry
            yield self._event("agent_output", "Risk Agent", risk_output.recommendation,
                             data=risk_output.to_dict(), icon="risk")

            # 3. Tax Agent
            yield self._event("agent_thinking", "Tax Agent", "Optimizing taxes and reviewing previous strategies...")
            tax_output = await self.tax_agent.analyze(user_profile, macro_data, context, meeting_transcript)
            transcript_entry = f"TAX AGENT: {tax_output.recommendation}\nReasoning: {tax_output.reasoning}\n\n"
            meeting_transcript += transcript_entry
            yield self._event("agent_output", "Tax Agent", tax_output.recommendation,
                             data=tax_output.to_dict(), icon="tax")

            # ── Phase 3: Debate & Rebuttal Loop ──
            yield self._event("debate_start", "Board", "Orchestrator moderating debate...")

            conflicts = await self._detect_conflicts_llm(meeting_transcript)
            
            # The conflicts are currently generated as statements from the agents. We will stream them and append to transcript.
            for conflict in conflicts:
                agent_name = conflict["agent"]
                message = conflict["message"]
                yield self._event("agent_debate", agent_name, message, debate=True)
                meeting_transcript += f"{agent_name.upper()}: {message}\n\n"
                await asyncio.sleep(0.3)

            debate_context = {
                "sentinel_output": sentinel_output.to_dict(),
                "investment_output": investment_output.to_dict(),
                "risk_output": risk_output.to_dict(),
                "tax_output": tax_output.to_dict(),
                "meeting_transcript": meeting_transcript
            }

            # ── Phase 4: Orchestrator Consensus ──
            yield self._event("agent_thinking", "Orchestrator", "Synthesizing board consensus from the full transcript...")
            final_output = await self.analyze(user_profile, macro_data, debate_context)

            yield self._event("consensus", "Orchestrator", final_output.recommendation,
                             data=final_output.to_dict(), icon="orchestrator")

            # ── Phase 5: Persist to Memory ──
            await self.memory.save_board_meeting({
                "meeting_id": meeting_id,
                "user_id": self.user_id,
                "timestamp": time.time(),
                "macro_snapshot": macro_data,
                "agent_outputs": {
                    "sentinel": sentinel_output.to_dict(),
                    "investment": investment_output.to_dict(),
                    "risk": risk_output.to_dict(),
                    "tax": tax_output.to_dict(),
                    "orchestrator": final_output.to_dict(),
                },
                "meeting_transcript": meeting_transcript,
                "consensus_actions": final_output.actions,
            })

            yield self._event("meeting_saved", "System", f"Board meeting {meeting_id} saved to memory.")

    async def handle_user_question(
        self,
        user_profile: dict,
        macro_data: dict,
        question: str,
        meeting_context: dict = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Respond to a user question mid-meeting.
        The Orchestrator synthesizes a focused board response without re-running all agents.
        Streams events back to the frontend as a live board reply.
        """
        meeting_context = meeting_context or {}

        yield self._event("agent_thinking", "Orchestrator", "Board is considering your question...")

        # Build a focused Q&A prompt
        qa_prompt = f"""
        A board member (the user) has asked the following question mid-meeting:

        USER QUESTION: "{question}"

        USER FINANCIAL PROFILE SUMMARY:
        - Monthly Income: {user_profile.get('monthly_income', 'N/A')}
        - Portfolio Value: {user_profile.get('portfolio', {}).get('total_value', 'N/A')}
        - Risk Tolerance: {user_profile.get('risk_tolerance', 'moderate')}
        - Investment Horizon: {user_profile.get('investment_horizon_years', 'N/A')} years
        - User Constraints: {user_profile.get('user_stated_constraints', [])}

        CURRENT MACRO CONTEXT:
        - Nifty 50: {macro_data.get('markets', {}).get('nifty50', 'N/A')}
        - RBI Repo Rate: {macro_data.get('interest_rates', {}).get('rbi_repo_rate', 'N/A')}%
        - CPI Inflation: {macro_data.get('inflation', {}).get('cpi_yoy', 'N/A')}%

        RECENT MEETING CONTEXT: {meeting_context.get('recent_consensus', 'No prior consensus this session')}

        As the Board Chairperson, provide a direct, actionable board response to the user's question.
        Return valid JSON in EXACTLY this format:
        {{
          "board_response": "<2-4 sentence direct answer to the user's specific question>",
          "responding_agents": ["<list of agents most relevant to this question>"],
          "key_insight": "<the single most important insight for the user>",
          "recommended_action": "<one specific action the user should take based on this question>",
          "confidence": <0.0-1.0>
        }}
        """

        try:
            from agents.base_agent import SAFETY_SETTINGS
            response = await self.model.generate_content_async(
                qa_prompt,
                generation_config=self.generation_config,
                safety_settings=SAFETY_SETTINGS,
            )
            data = self._safe_parse_json(response.text)

            yield self._event(
                "user_response",
                "Orchestrator",
                data.get("board_response", "The board has reviewed your question."),
                data={"key_insight": data.get("key_insight"), "recommended_action": data.get("recommended_action"), "confidence": data.get("confidence", 0.8), "responding_agents": data.get("responding_agents", [])},
            )
        except Exception as e:
            yield self._event("user_response", "Orchestrator", f"Board response error: {str(e)}")

    async def run_simulation(
        self,
        user_profile: dict,
        scenario: str,
    ) -> AsyncGenerator[dict, None]:
        """Run an economic shock simulation scenario."""
        yield self._event("agent_thinking", "Orchestrator", f"Simulating scenario: {scenario}")

        sim_macro = await self._generate_scenario_macro(scenario)
        yield self._event("simulation_data", "Sentinel Agent", f"Scenario macro environment constructed",
                         data=sim_macro)

        async for event in self.run_board_meeting(
            user_profile=user_profile,
            macro_data=sim_macro,
            context={"simulation": True, "scenario": scenario},
        ):
            event["simulation"] = True
            yield event

    async def _generate_scenario_macro(self, scenario: str) -> dict:
        """Generate macro data for a given simulation scenario."""
        scenarios = {
            "india_recession": {
                "country": "India", "simulation": True, "scenario": "India Recession",
                "inflation": {"cpi_yoy": 9.5, "core_inflation": 7.0, "food_inflation": 13.0, "trend": "rising"},
                "interest_rates": {"rbi_repo_rate": 7.50, "reverse_repo": 7.25, "10yr_gsec_yield": 8.20, "trend": "hiking"},
                "employment": {"unemployment_rate": 12.0, "cmie_unemployment": 14.5, "urban_unemployment": 18.0, "trend": "surging"},
                "growth": {"gdp_growth_yoy": -1.5, "iip_growth": -3.0, "trend": "contraction"},
                "markets": {"nifty50": 17000, "sensex": 57000, "nifty_change_1m": -15.0, "vix_india": 28.0, "trend": "crash"},
                "currency": {"usd_inr": 92.0, "change_ytd": -8.0},
                "global": {"us_fed_rate": 5.5, "crude_oil_brent": 95.0, "global_recession_probability": 0.65},
            },
            "rate_hike": {
                "country": "India", "simulation": True, "scenario": "RBI Emergency Rate Hike +100bps",
                "inflation": {"cpi_yoy": 8.2, "core_inflation": 6.5, "food_inflation": 11.0, "trend": "surging"},
                "interest_rates": {"rbi_repo_rate": 7.50, "reverse_repo": 7.25, "10yr_gsec_yield": 8.80, "trend": "emergency_hike"},
                "employment": {"unemployment_rate": 8.5, "cmie_unemployment": 9.0, "urban_unemployment": 11.0, "trend": "stable"},
                "growth": {"gdp_growth_yoy": 5.0, "iip_growth": 2.5, "trend": "slowing"},
                "markets": {"nifty50": 21000, "sensex": 70000, "nifty_change_1m": -8.0, "vix_india": 22.0, "trend": "correction"},
                "currency": {"usd_inr": 85.5, "change_ytd": -2.5},
                "global": {"us_fed_rate": 6.0, "crude_oil_brent": 88.0, "global_recession_probability": 0.35},
            },
            "market_crash": {
                "country": "India", "simulation": True, "scenario": "Market Crash -30%",
                "inflation": {"cpi_yoy": 5.1, "core_inflation": 3.8, "food_inflation": 6.5, "trend": "stable"},
                "interest_rates": {"rbi_repo_rate": 6.00, "reverse_repo": 5.75, "10yr_gsec_yield": 6.50, "trend": "easing"},
                "employment": {"unemployment_rate": 8.2, "cmie_unemployment": 8.5, "urban_unemployment": 9.8, "trend": "stable"},
                "growth": {"gdp_growth_yoy": 4.5, "iip_growth": 2.1, "trend": "moderating"},
                "markets": {"nifty50": 16870, "sensex": 55860, "nifty_change_1m": -30.0, "vix_india": 26.5, "trend": "bear"},
                "currency": {"usd_inr": 86.8, "change_ytd": -3.5},
                "global": {"us_fed_rate": 4.5, "crude_oil_brent": 72.0, "global_recession_probability": 0.55},
            },
            "job_loss": {
                "country": "India", "simulation": True, "scenario": "Tech Sector Layoffs",
                "inflation": {"cpi_yoy": 4.9, "core_inflation": 3.5, "food_inflation": 5.8, "trend": "stable"},
                "interest_rates": {"rbi_repo_rate": 6.50, "reverse_repo": 6.25, "10yr_gsec_yield": 6.80, "trend": "on_hold"},
                "employment": {"unemployment_rate": 11.2, "cmie_unemployment": 11.5, "urban_unemployment": 14.8, "trend": "surging"},
                "growth": {"gdp_growth_yoy": 6.2, "iip_growth": 4.0, "trend": "stable"},
                "markets": {"nifty50": 23500, "sensex": 77800, "nifty_change_1m": -1.5, "vix_india": 14.2, "trend": "sideways"},
                "currency": {"usd_inr": 84.6, "change_ytd": -1.2},
                "global": {"us_fed_rate": 5.25, "crude_oil_brent": 80.5, "global_recession_probability": 0.30},
            },
            "inflation_spike": {
                "country": "India", "simulation": True, "scenario": "Inflation Spike to 10%",
                "inflation": {"cpi_yoy": 10.2, "core_inflation": 8.0, "food_inflation": 15.5, "trend": "surging"},
                "interest_rates": {"rbi_repo_rate": 7.50, "reverse_repo": 7.25, "10yr_gsec_yield": 8.10, "trend": "hiking"},
                "employment": {"unemployment_rate": 8.4, "cmie_unemployment": 8.9, "urban_unemployment": 10.5, "trend": "stable"},
                "growth": {"gdp_growth_yoy": 5.0, "iip_growth": 2.5, "trend": "slowing"},
                "markets": {"nifty50": 22200, "sensex": 73500, "nifty_change_1m": -5.2, "vix_india": 18.5, "trend": "volatile"},
                "currency": {"usd_inr": 86.2, "change_ytd": -3.2},
                "global": {"us_fed_rate": 5.75, "crude_oil_brent": 98.0, "global_recession_probability": 0.45},
            },
        }

        # Default scenario from text
        for key, data in scenarios.items():
            if key.lower() in scenario.lower() or data["scenario"].lower() in scenario.lower():
                return data

        return scenarios["india_recession"]

    async def _detect_conflicts_llm(
        self,
        meeting_transcript: str,
    ) -> list[dict]:
        """LLM-powered conflict detection between agents."""
        prompt = f"""
        Analyze the following meeting transcript of three financial agents (Investment, Risk, Tax).
        Identify any disagreements or conflicts in their recommendations or reasoning.

        MEETING TRANSCRIPT:
        {meeting_transcript}

        Identify up to 3 key conflicts or points of tension. If no conflicts exist, return an empty array.
        Respond ONLY in EXACT JSON format:
        {{
            "conflicts": [
                {{
                    "agent": "<Agent Name that raised the point>",
                    "message": "<A 1-2 sentence first-person statement from this agent challenging another agent's point>"
                }}
            ]
        }}
        """
        try:
            from agents.base_agent import SAFETY_SETTINGS
            response = await self.model.generate_content_async(
                prompt,
                generation_config=self.generation_config,
                safety_settings=SAFETY_SETTINGS,
            )
            data = self._safe_parse_json(response.text)
            return data.get("conflicts", [])
        except Exception as e:
            return []

    def _event(
        self,
        event_type: str,
        agent: str,
        message: str,
        data: dict = None,
        icon: str = None,
        debate: bool = False,
    ) -> dict:
        return {
            "type": event_type,
            "agent": agent,
            "message": message,
            "data": data,
            "icon": icon,
            "debate": debate,
            "timestamp": time.time(),
        }
