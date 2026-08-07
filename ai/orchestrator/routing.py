"""Conditional LangGraph routing decisions."""

from typing import Literal

from ai.orchestrator.state import CopilotState


def route_after_retrieval(
    state: CopilotState,
) -> Literal["generate_response", "fallback_response"]:
    """Avoid an LLM response call when approved context is insufficient."""

    retrieval = state["retrieval"]
    return "generate_response" if retrieval.sufficient_context else "fallback_response"


__all__ = ["route_after_retrieval"]
