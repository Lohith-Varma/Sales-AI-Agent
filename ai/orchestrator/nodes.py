"""Thin LangGraph nodes adapting typed state to isolated agents."""

import asyncio

from ai.agents.entity.agent import EntityExtractionAgent
from ai.agents.guardrail.agent import GuardrailAgent
from ai.agents.intent.agent import IntentDetectionAgent
from ai.agents.next_action.agent import NextBestActionAgent
from ai.agents.rag.agent import RAGRetrievalAgent
from ai.agents.response.agent import ResponseGenerationAgent
from ai.agents.sentiment.agent import SentimentAgent
from ai.agents.speech.agent import SpeechToTextAgent
from ai.orchestrator.state import CopilotState
from ai.schemas.analysis import IntentDetectionRequest, NextActionRequest, SentimentDetectionRequest
from ai.schemas.entities import EntityExtractionRequest
from ai.schemas.guardrail import GuardrailRequest
from ai.schemas.orchestration import AgentConfidenceScores, CopilotResult, NextActionRecommendation
from ai.schemas.rag import RetrievalRequest
from ai.schemas.rag import RetrievalOutput
from ai.schemas.enums import ErrorCode, NextActionType, WorkflowStage
from ai.schemas.orchestration import WorkflowIssue
from ai.schemas.responses import (
    ResponseGenerationOutput,
    ResponseGenerationRequest,
    SuggestedResponse,
)


class WorkflowNodes:
    """Dependency-injected node collection used to compile the workflow."""

    def __init__(
        self,
        *,
        speech: SpeechToTextAgent,
        intent: IntentDetectionAgent,
        sentiment: SentimentAgent,
        entity: EntityExtractionAgent,
        rag: RAGRetrievalAgent,
        response: ResponseGenerationAgent,
        next_action: NextBestActionAgent,
        guardrail: GuardrailAgent,
        safe_fallback: str,
        rag_top_k: int,
        rag_fetch_k: int,
        rag_minimum_score: float,
        minimum_grounding_coverage: float,
        minimum_agent_confidence: float,
    ) -> None:
        self.speech_agent = speech
        self.intent_agent = intent
        self.sentiment_agent = sentiment
        self.entity_agent = entity
        self.rag_agent = rag
        self.response_agent = response
        self.next_action_agent = next_action
        self.guardrail_agent = guardrail
        self.safe_fallback = safe_fallback
        self.rag_top_k = rag_top_k
        self.rag_fetch_k = rag_fetch_k
        self.rag_minimum_score = rag_minimum_score
        self.minimum_grounding_coverage = minimum_grounding_coverage
        self.minimum_agent_confidence = minimum_agent_confidence

    async def transcribe(self, state: CopilotState) -> dict[str, object]:
        request = state.get("transcription_request")
        if request is None:
            return {}
        output = await self.speech_agent.run(request)
        return {"transcription": output, "latest_customer_utterance": output.full_text}

    async def detect_intent(self, state: CopilotState) -> dict[str, object]:
        output = await self.intent_agent.run(
            IntentDetectionRequest(
                latest_customer_utterance=state["latest_customer_utterance"],
                conversation_context=state["conversation_context"],
            )
        )
        return {"intent": output}

    async def detect_sentiment(self, state: CopilotState) -> dict[str, object]:
        output = await self.sentiment_agent.run(
            SentimentDetectionRequest(
                latest_customer_utterance=state["latest_customer_utterance"],
                conversation_context=state["conversation_context"],
            )
        )
        return {"sentiment": output}

    async def extract_entities(self, state: CopilotState) -> dict[str, object]:
        output = await self.entity_agent.run(
            EntityExtractionRequest(
                latest_customer_utterance=state["latest_customer_utterance"],
                conversation_context=state["conversation_context"],
                known_entities=state["known_entities"],
            )
        )
        return {"entity_output": output}

    async def retrieve(self, state: CopilotState) -> dict[str, object]:
        utterance = state["latest_customer_utterance"]
        intent = state["intent"]
        request = RetrievalRequest(
            query=f"Intent: {intent.intent.value}\nCustomer: {utterance}",
            intent=intent.intent,
            top_k=self.rag_top_k,
            fetch_k=self.rag_fetch_k,
            minimum_relevance_score=self.rag_minimum_score,
        )
        try:
            output = await self.rag_agent.run(request)
            return {"retrieval": output}
        except Exception:
            return {
                "retrieval": RetrievalOutput(
                    query=request.query,
                    sufficient_context=False,
                    confidence=0.0,
                ),
                "issues": (
                    WorkflowIssue(
                        stage=WorkflowStage.RETRIEVING,
                        code=ErrorCode.RETRIEVAL_FAILED,
                        message="Approved knowledge retrieval failed; a safe fallback was used.",
                        recoverable=True,
                    ),
                ),
            }

    async def generate_response(self, state: CopilotState) -> dict[str, object]:
        response_request = ResponseGenerationRequest(
            latest_customer_utterance=state["latest_customer_utterance"],
            conversation_context=state["conversation_context"],
            intent=state["intent"].intent,
            sentiment=state["sentiment"].sentiment,
            entities=state["entity_output"].entities,
            retrieval=state["retrieval"],
        )
        action_request = NextActionRequest(
            latest_customer_utterance=state["latest_customer_utterance"],
            intent=state["intent"],
            sentiment=state["sentiment"],
            entities=state["entity_output"].entities,
            retrieval=state["retrieval"],
        )
        response, action = await asyncio.gather(
            self.response_agent.run(response_request),
            self.next_action_agent.run(action_request),
        )
        return {"response": response, "next_action": action}

    async def fallback_response(self, state: CopilotState) -> dict[str, object]:
        action = NextActionRecommendation(
            action=NextActionType.TRANSFER_TO_HUMAN_EXPERT,
            rationale="Approved product context is unavailable, so a human expert must verify the answer.",
            confidence=1.0,
            requires_confirmation=True,
        )
        return {
            "response": ResponseGenerationOutput(
                suggestion=SuggestedResponse(
                    text=self.safe_fallback,
                    is_fallback=True,
                    requires_human_review=True,
                    confidence=1.0,
                ),
                source_chunk_count=0,
            ),
            "next_action": action,
        }

    async def recommend_action(self, state: CopilotState) -> dict[str, object]:
        output = await self.next_action_agent.run(
            NextActionRequest(
                latest_customer_utterance=state["latest_customer_utterance"],
                intent=state["intent"],
                sentiment=state["sentiment"],
                entities=state["entity_output"].entities,
                retrieval=state["retrieval"],
            )
        )
        return {"next_action": output}

    async def validate_response(self, state: CopilotState) -> dict[str, object]:
        output = await self.guardrail_agent.run(
            GuardrailRequest(
                candidate=state["response"].suggestion,
                retrieval=state["retrieval"],
                minimum_grounding_coverage=self.minimum_grounding_coverage,
                minimum_agent_confidence=self.minimum_agent_confidence,
            )
        )
        return {"guardrail": output}

    async def assemble(self, state: CopilotState) -> dict[str, object]:
        intent = state["intent"]
        sentiment = state["sentiment"]
        entities = state["entity_output"]
        retrieval = state["retrieval"]
        response = state["response"]
        action = state["next_action"]
        guardrail = state["guardrail"]
        confidences = AgentConfidenceScores(
            intent=intent.confidence,
            sentiment=sentiment.confidence,
            entities=entities.confidence,
            retrieval=retrieval.confidence,
            response=response.suggestion.confidence,
            next_action=action.confidence,
        )
        aggregate = min(confidences.model_dump().values())
        context = state["context"]
        result = CopilotResult(
            request_id=context.request_id,
            session_id=context.session_id,
            sequence_number=context.sequence_number,
            latest_transcript=state["latest_customer_utterance"],
            intent=intent.intent,
            sentiment=sentiment.sentiment,
            entities=entities.entities,
            retrieved_context=retrieval.chunks,
            suggested_response=guardrail.final_response,
            next_best_action=action,
            guardrail=guardrail,
            confidence=aggregate,
            agent_confidences=confidences,
            issues=state.get("issues", ()),
        )
        return {"result": result}


__all__ = ["WorkflowNodes"]
