"""
Arize Phoenix Observability — OpenTelemetry tracing for all Boardroom AI agents.
Traces agent reasoning, confidence scores, debate flow, and execution chains.

Usage: call setup_tracing() once at app startup in main.py lifespan.
Then wrap any agent call with @trace_agent_call decorator.
"""
import functools
import os
import time
from typing import Callable

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

# Arize Phoenix local endpoint (or cloud)
PHOENIX_ENDPOINT = os.getenv("PHOENIX_ENDPOINT", "http://localhost:6006/v1/traces")
ARIZE_SPACE_KEY  = os.getenv("ARIZE_SPACE_KEY", "")
ARIZE_API_KEY    = os.getenv("ARIZE_API_KEY", "")

_tracer: trace.Tracer | None = None


def setup_tracing(service_name: str = "boardroom-ai") -> None:
    """Initialize OpenTelemetry + Arize Phoenix tracing. Call once at startup."""
    global _tracer

    provider = TracerProvider()

    # Local Phoenix (self-hosted)
    local_exporter = OTLPSpanExporter(endpoint=PHOENIX_ENDPOINT)
    provider.add_span_processor(BatchSpanProcessor(local_exporter))

    # Arize cloud (if keys provided)
    if ARIZE_SPACE_KEY and ARIZE_API_KEY:
        arize_exporter = OTLPSpanExporter(
            endpoint="https://otlp.arize.com/v1/traces",
            headers={
                "space_key": ARIZE_SPACE_KEY,
                "api_key": ARIZE_API_KEY,
            },
        )
        provider.add_span_processor(BatchSpanProcessor(arize_exporter))

    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer(service_name)


def get_tracer() -> trace.Tracer:
    global _tracer
    if _tracer is None:
        setup_tracing()
    return _tracer


def trace_agent_call(agent_name: str):
    """
    Decorator that wraps an agent's analyze() call in an OpenTelemetry span.
    Captures: agent_name, confidence, recommendation, risk_flags, latency.

    Usage:
        @trace_agent_call("Investment Agent")
        async def analyze(...):
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.start_as_current_span(f"{agent_name}.analyze") as span:
                span.set_attribute("agent.name", agent_name)
                span.set_attribute("agent.call_time", time.time())

                # Capture user_id from self if present
                if args and hasattr(args[0], "user_id"):
                    span.set_attribute("user.id", getattr(args[0], "user_id", "unknown"))

                try:
                    start = time.monotonic()
                    result = await func(*args, **kwargs)
                    latency_ms = (time.monotonic() - start) * 1000

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
                    raise

        return wrapper
    return decorator


def trace_board_meeting(meeting_id: str, user_id: str):
    """Context manager for tracing a full board meeting as a root span."""
    tracer = get_tracer()
    span = tracer.start_span("board_meeting")
    span.set_attribute("meeting.id", meeting_id)
    span.set_attribute("user.id", user_id)
    return trace.use_span(span, end_on_exit=True)
