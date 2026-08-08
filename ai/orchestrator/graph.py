"""LangGraph compilation and timeout-bounded workflow facade."""

from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import Any, TypeAlias, cast

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from ai.agents.crm.agent import CRMSummaryAgent
from ai.agents.crm.lead_scorer import LeadScorer
from ai.orchestrator.nodes import WorkflowNodes
from ai.orchestrator.routing import route_after_retrieval
from ai.orchestrator.state import CopilotState, LiveWorkflowInput
from ai.schemas.crm import CRMGenerationOutput, CRMGenerationRequest, CRMSummary
from ai.schemas.enums import LeadStatus
from ai.schemas.orchestration import CopilotResult
from ai.schemas.orchestration import AgentConfidenceScores, NextActionRecommendation, WorkflowIssue
from ai.schemas.entities import CustomerEntities
from ai.schemas.enums import ErrorCode, IntentType, NextActionType, SentimentType, WorkflowStage
from ai.schemas.guardrail import GuardrailOutput
from ai.schemas.responses import SuggestedResponse
from ai.utils.exceptions import ModelUnavailableError, WorkflowTimeoutError

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
    builder.add_edge("generate_response", "validate_response")
    builder.add_edge("fallback_response", "validate_response")
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
        safe_fallback: str,
    ) -> None:
        self._graph = graph
        self._crm_agent = crm_agent
        self._live_timeout_seconds = live_timeout_seconds
        self._crm_timeout_seconds = crm_timeout_seconds
        self._safe_fallback = safe_fallback

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
        except ModelUnavailableError:
            if request.latest_customer_utterance is None:
                raise
            fallback = SuggestedResponse(
                text=self._safe_fallback,
                is_fallback=True,
                requires_human_review=True,
                confidence=1.0,
            )
            return CopilotResult(
                request_id=request.context.request_id,
                session_id=request.context.session_id,
                sequence_number=request.context.sequence_number,
                latest_transcript=request.latest_customer_utterance,
                intent=IntentType.UNKNOWN,
                sentiment=SentimentType.UNKNOWN,
                entities=request.known_entities or CustomerEntities(),
                suggested_response=fallback,
                next_best_action=NextActionRecommendation(
                    action=NextActionType.TRANSFER_TO_HUMAN_EXPERT,
                    rationale="The AI model is temporarily unavailable; a human expert should verify the response.",
                    confidence=1.0,
                    requires_confirmation=True,
                ),
                guardrail=GuardrailOutput(
                    is_safe=True,
                    is_grounded=True,
                    valid_json=True,
                    contains_unsupported_financial_advice=False,
                    grounding_coverage=1.0,
                    requires_human_review=True,
                    final_response=fallback,
                ),
                confidence=0.0,
                agent_confidences=AgentConfidenceScores(
                    intent=0.0,
                    sentiment=0.0,
                    entities=0.0,
                    retrieval=0.0,
                    response=0.0,
                    next_action=0.0,
                ),
                issues=(
                    WorkflowIssue(
                        stage=WorkflowStage.GENERATING,
                        code=ErrorCode.MODEL_UNAVAILABLE,
                        message="The AI model was unavailable; no product claim was generated.",
                        recoverable=True,
                    ),
                ),
            )
        return cast(CopilotResult, completed["result"])

    async def run_crm(self, request: CRMGenerationRequest) -> CRMGenerationOutput:
        try:
            async with asyncio.timeout(self._crm_timeout_seconds):
                return await self._crm_agent.run(request)
        except TimeoutError as exc:
            raise WorkflowTimeoutError(self._crm_timeout_seconds) from exc
        except ModelUnavailableError:
            follow_up = request.recommended_action is NextActionType.SCHEDULE_FOLLOW_UP
            status = (
                LeadStatus.FOLLOW_UP_REQUIRED
                if follow_up
                else LeadStatus.APPLICATION_READY
                if request.recommended_action is NextActionType.START_APPLICATION
                else LeadStatus.INTERESTED
                if request.primary_intent is IntentType.INTERESTED
                else LeadStatus.QUALIFYING
            )
            transcript_lines = [line.strip() for line in request.transcript.splitlines() if line.strip()]
            excerpt = " ".join(transcript_lines[-3:])[:1_500]
            summary = CRMSummary(
                call_summary=(
                    f"Model-assisted summarization was unavailable. Recent verified transcript: {excerpt}"
                ),
                lead_score=LeadScorer().score(request),
                follow_up_date=date.today() + timedelta(days=1) if follow_up else None,
                lead_status=status,
                important_notes=("AI summary requires representative review.",),
            )
            return CRMGenerationOutput(
                crm_summary=summary,
                confidence=0.0,
                requires_human_review=True,
            )


__all__ = ["SalesCopilotWorkflow", "build_graph"]
