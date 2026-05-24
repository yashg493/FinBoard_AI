"""
Base Agent — Foundation class for all Boardroom AI agents.
Handles Vertex AI Gemini calls, structured output, and confidence scoring.
"""
import json
import re
import time
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator

import os
import httpx
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

VERTEX_PROJECT = os.getenv("VERTEX_PROJECT", "your-gcp-project-id")
VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")
MODEL_ID = os.getenv("VERTEX_MODEL", "gemini-1.5-pro")

vertexai.init(project=VERTEX_PROJECT, location=VERTEX_LOCATION)


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
    Wraps Vertex AI Gemini with structured output parsing, retry logic,
    and async streaming support.
    """

    def __init__(self, agent_name: str, system_prompt: str):
        self.agent_name = agent_name
        self.system_prompt = system_prompt
        self.model = GenerativeModel(
            MODEL_ID,
            system_instruction=system_prompt,
        )
        self.generation_config = GenerationConfig(
            temperature=0.3,
            top_p=0.9,
            max_output_tokens=2048,
            response_mime_type="application/json",
        )

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
        """Main analysis entry point — calls Gemini and returns structured output with tracing."""
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
                )
                latency_ms = (time.monotonic() - start) * 1000
                raw_text = response.text
                result = self.parse_output(raw_text)

                # Record output attributes
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
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON object within the text
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                return json.loads(match.group())
            raise ValueError(f"Could not parse JSON from: {text[:200]}")

    def _clamp_confidence(self, value: Any) -> float:
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return 0.5
