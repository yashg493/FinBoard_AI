"""
Base Agent — Foundation class for all Boardroom AI agents.
Handles Vertex AI Gemini calls, structured output, confidence scoring,
Gemini Safety Settings (Phase 5), and formal Tool declarations (Phase 2).
"""
import json
import re
import time
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator

import os
import httpx
import vertexai
from vertexai.generative_models import (
    GenerativeModel,
    GenerationConfig,
    HarmCategory,
    HarmBlockThreshold,
    Tool,
    FunctionDeclaration,
    Part,
)

VERTEX_PROJECT = os.getenv("VERTEX_PROJECT", "your-gcp-project-id")
VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")
MODEL_ID = os.getenv("VERTEX_MODEL", "gemini-2.5-flash")

vertexai.init(project=VERTEX_PROJECT, location=VERTEX_LOCATION)

# ── Gemini Safety Settings (Hackathon Phase 5) ────────────────────────────────
# Allow financial discussion but block harmful content
SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HATE_SPEECH:        HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT:  HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT:  HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_HARASSMENT:         HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
}

# ── Vertex AI Tool Declarations (Hackathon Phase 2) ───────────────────────────
# Formal tool definitions allow agents to call structured functions
fetch_macro_data_tool = FunctionDeclaration(
    name="fetch_macro_data",
    description="Fetch live macroeconomic indicators for India (RBI repo rate, CPI, Nifty50, GDP, employment, currency).",
    parameters={
        "type": "object",
        "properties": {
            "country": {
                "type": "string",
                "description": "Country code for macro data (e.g., 'IN' for India)",
            }
        },
        "required": [],
    },
)

query_user_portfolio_tool = FunctionDeclaration(
    name="query_user_portfolio",
    description="Retrieve a user's current portfolio holdings, allocation breakdown, and unrealized gains/losses.",
    parameters={
        "type": "object",
        "properties": {
            "user_id": {
                "type": "string",
                "description": "The unique identifier of the user",
            },
            "include_live_prices": {
                "type": "boolean",
                "description": "Whether to include real-time LTP prices for each holding",
            },
        },
        "required": ["user_id"],
    },
)

get_portfolio_risk_metrics_tool = FunctionDeclaration(
    name="get_portfolio_risk_metrics",
    description="Compute risk metrics for a portfolio: volatility, beta, Sharpe ratio, max drawdown, and concentration risk.",
    parameters={
        "type": "object",
        "properties": {
            "portfolio_holdings": {
                "type": "array",
                "description": "List of holdings with ticker, quantity, and average cost",
                "items": {"type": "object"},
            }
        },
        "required": ["portfolio_holdings"],
    },
)

BOARDROOM_TOOLS = Tool(
    function_declarations=[
        fetch_macro_data_tool,
        query_user_portfolio_tool,
        get_portfolio_risk_metrics_tool,
    ]
)


class AgentOutput:
    def __init__(
        self,
        agent_name: str,
        recommendation: str,
        reasoning: str,
        confidence: float,
        actions: list[dict],
        risk_flags: list[str] = None,
    ):
        self.agent_name = agent_name
        self.recommendation = recommendation
        self.reasoning = reasoning
        self.confidence = confidence
        self.actions = actions
        self.risk_flags = risk_flags or []
        self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            "agent_name": self.agent_name,
            "recommendation": self.recommendation,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "actions": self.actions,
            "risk_flags": self.risk_flags,
            "timestamp": self.timestamp,
        }


class BaseAgent(ABC):
    """
    Abstract base for all Boardroom AI agents.
    Wraps Vertex AI Gemini with:
    - Structured output parsing & retry logic
    - Gemini Safety Settings (Phase 5 compliance)
    - Formal Tool declarations for macro/portfolio data (Phase 2 compliance)
    - Arize Phoenix OpenTelemetry tracing (Phase 3 compliance)
    """

    def __init__(self, agent_name: str, system_prompt: str):
        self.agent_name = agent_name
        json_safety_instruction = (
            "\n\nCRITICAL: You must return valid JSON only matching the schema exactly. "
            "Never use unescaped double quotes inside your JSON string values (for example, "
            "do not write \"portfolio allocation\" inside a string; use single quotes like "
            "'portfolio allocation' instead). Verify that the JSON is fully compliant and that "
            "all brackets and parentheses are correctly closed."
        )
        self.system_prompt = system_prompt + json_safety_instruction
        self.model = GenerativeModel(
            MODEL_ID,
            system_instruction=self.system_prompt,
        )
        self.generation_config = {
            "temperature": 0.3,
            "top_p": 0.9,
            "max_output_tokens": 4096,
            "response_mime_type": "application/json",
            "thinking_config": {"thinking_budget": 0},
        }

    @abstractmethod
    def build_prompt(self, user_profile: dict, macro_data: dict, context: dict) -> str:
        """Build the agent-specific prompt."""
        pass

    @abstractmethod
    def parse_output(self, raw: str) -> AgentOutput:
        """Parse the LLM output into structured AgentOutput."""
        pass

    async def analyze(
        self,
        user_profile: dict,
        macro_data: dict,
        context: dict = None,
    ) -> AgentOutput:
        """Main analysis entry point — calls Gemini with safety settings and returns structured output."""
        context = context or {}
        prompt = self.build_prompt(user_profile, macro_data, context)

        # Lazy imports to prevent circular imports
        from utils.observability import get_tracer
        from opentelemetry import trace

        tracer = get_tracer()
        with tracer.start_as_current_span(f"{self.agent_name}.analyze") as span:
            span.set_attribute("agent.name", self.agent_name)
            span.set_attribute("agent.call_time", time.time())

            # Record user identifier
            user_id = user_profile.get("user_id") or context.get("user_id") or getattr(self, "user_id", "unknown")
            span.set_attribute("user.id", user_id)

            try:
                start = time.monotonic()
                response = await self.model.generate_content_async(
                    prompt,
                    generation_config=self.generation_config,
                    safety_settings=SAFETY_SETTINGS,  # Phase 5: enforce safety guardrails
                )
                latency_ms = (time.monotonic() - start) * 1000
                raw_text = response.text
                result = self.parse_output(raw_text)

                # Record output attributes for Arize Phoenix tracing
                span.set_attribute("agent.confidence", getattr(result, "confidence", 0.0))
                span.set_attribute("agent.recommendation", getattr(result, "recommendation", "")[:200])
                span.set_attribute("agent.risk_flags", str(getattr(result, "risk_flags", [])))
                span.set_attribute("agent.action_count", len(getattr(result, "actions", [])))
                span.set_attribute("latency_ms", round(latency_ms, 1))
                span.set_status(trace.StatusCode.OK)

                return result
            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.StatusCode.ERROR, str(e))
                return AgentOutput(
                    agent_name=self.agent_name,
                    recommendation=f"Analysis unavailable: {str(e)}",
                    reasoning="Error during analysis",
                    confidence=0.0,
                    actions=[],
                    risk_flags=["AGENT_ERROR"],
                )

    def _safe_parse_json(self, text: str) -> dict:
        """Robustly extract JSON from model output."""
        text = text.strip()
        # Remove markdown code fences if present
        text = re.sub(r"```(?:json)?\s*", "", text)
        text = text.replace("```", "")

        # Clean up common JSON syntax issues like trailing commas before closing braces/brackets
        text = re.sub(r',\s*\}', '}', text)
        text = re.sub(r',\s*\]', ']', text)

        try:
            return json.loads(text)
        except json.JSONDecodeError as jde:
            import logging
            db_logger = logging.getLogger("boardroom-ai")
            db_logger.error(f"[DEBUG_JSON_FAIL] Text length: {len(text)}. Exception: {str(jde)}")
            db_logger.error(f"[DEBUG_JSON_FAIL] Full text:\n{text}\n[DEBUG_JSON_FAIL_END]")
            # Try to find JSON object within the text
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                try:
                    cleaned_match = match.group()
                    cleaned_match = re.sub(r',\s*\}', '}', cleaned_match)
                    cleaned_match = re.sub(r',\s*\]', ']', cleaned_match)
                    return json.loads(cleaned_match)
                except json.JSONDecodeError as jde_inner:
                    raise ValueError(f"Inner JSON parsing failed: {str(jde_inner)}. Cleaned text: {cleaned_match[:500]}")
            raise ValueError(f"JSON parsing failed: {str(jde)}. Raw text: {text[:500]}")

    def _clamp_confidence(self, value: Any) -> float:
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return 0.5
