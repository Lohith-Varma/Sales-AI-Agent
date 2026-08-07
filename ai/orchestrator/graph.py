"""LangGraph compilation and timeout-bounded workflow facade."""

from __future__ import annotations

import asyncio
from typing import Any, TypeAlias, cast

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from ai.agents.crm.agent import CRMSummaryAgent
from ai.orchestrator.nodes import WorkflowNodes
from ai.orchestrator.routing import route_after_retrieval
from ai.orchestrator.state import CopilotState, LiveWorkflowInput
from ai.schemas.crm import CRMGenerationOutput, CRMGenerationRequest
from ai.schemas.orchestration import CopilotResult
from ai.utils.exceptions import WorkflowTimeoutError

CopilotCompiledGraph: TypeAlias = CompiledStateGraph[
    CopilotState,
    None,
    CopilotState,
    CopilotState,
]


def build_graph(nodes: WorkflowNodes) -> CopilotCompiledGraph:
    """Compile the live multi-agent workflow with parallel analysis fan-out."""

    # LangGraph's generic node overloads cannot currently infer TypedDict async
    # node return updates. The compiled facade remains strongly typed below.
    builder = cast(Any, StateGraph(CopilotState))
    builder.add_node("transcribe", nodes.transcribe)
    builder.add_node("detect_intent", nodes.detect_intent)
    builder.add_node("detect_sentiment", nodes.detect_sentiment)
    builder.add_node("extract_entities", nodes.extract_entities)
    builder.add_node("retrieve", nodes.retrieve)
    builder.add_node("generate_response", nodes.generate_response)
    builder.add_node("fallback_response", nodes.fallback_response)
    builder.add_node("recommend_action", nodes.recommend_action)
    builder.add_node("validate_response", nodes.validate_response)
    builder.add_node("assemble", nodes.assemble)

    builder.add_edge(START, "transcribe")
    builder.add_edge("transcribe", "detect_intent")
    builder.add_edge("transcribe", "detect_sentiment")
    builder.add_edge("transcribe", "extract_entities")
    builder.add_edge(["detect_intent", "detect_sentiment", "extract_entities"], "retrieve")
    builder.add_conditional_edges(
        "retrieve",
        route_after_retrieval,
        {
            "generate_response": "generate_response",
            "fallback_response": "fallback_response",
        },
    )
    builder.add_edge("generate_response", "recommend_action")
    builder.add_edge("fallback_response", "recommend_action")
    builder.add_edge("recommend_action", "validate_response")
    builder.add_edge("validate_response", "assemble")
    builder.add_edge("assemble", END)
    return cast(CopilotCompiledGraph, builder.compile())


class SalesCopilotWorkflow:
    """Application facade for live LangGraph and post-call CRM execution."""

    def __init__(
        self,
        *,
        graph: CopilotCompiledGraph,
        crm_agent: CRMSummaryAgent,
        live_timeout_seconds: float,
        crm_timeout_seconds: float,
    ) -> None:
        self._graph = graph
        self._crm_agent = crm_agent
        self._live_timeout_seconds = live_timeout_seconds
        self._crm_timeout_seconds = crm_timeout_seconds

    async def run_live(self, request: LiveWorkflowInput) -> CopilotResult:
        state: CopilotState = {
            "context": request.context,
            "conversation_context": request.conversation_context,
            "known_entities": request.known_entities,
        }
        if request.transcription_request is not None:
            state["transcription_request"] = request.transcription_request
        if request.latest_customer_utterance is not None:
            state["latest_customer_utterance"] = request.latest_customer_utterance
        try:
            async with asyncio.timeout(self._live_timeout_seconds):
                completed = cast(dict[str, Any], await self._graph.ainvoke(state))
        except TimeoutError as exc:
            raise WorkflowTimeoutError(self._live_timeout_seconds) from exc
        return cast(CopilotResult, completed["result"])

    async def run_crm(self, request: CRMGenerationRequest) -> CRMGenerationOutput:
        try:
            async with asyncio.timeout(self._crm_timeout_seconds):
                return await self._crm_agent.run(request)
        except TimeoutError as exc:
            raise WorkflowTimeoutError(self._crm_timeout_seconds) from exc


__all__ = ["SalesCopilotWorkflow", "build_graph"]
