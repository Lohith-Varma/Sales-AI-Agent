"""Cross-agent analysis models and the final versioned co-pilot contract."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from ai.schemas.common import Confidence, SchemaModel, TextEvidence
from ai.schemas.crm import CRMSummary
from ai.schemas.entities import CustomerEntities
from ai.schemas.enums import (
    ErrorCode,
    IntentType,
    NextActionType,
    SentimentType,
    WorkflowStage,
)
from ai.schemas.guardrail import GuardrailOutput
from ai.schemas.rag import RetrievedChunk
from ai.schemas.responses import SuggestedResponse


class IntentAnalysis(SchemaModel):
    """Intent agent output for the latest customer utterance."""

    intent: IntentType
    secondary_intent: IntentType | None = None
    confidence: Confidence
    evidence: TextEvidence

    @model_validator(mode="after")
    def reject_duplicate_intents(self) -> Self:
        """Prevent the secondary label from repeating the primary label."""

        if self.secondary_intent is self.intent:
            raise ValueError("secondary_intent must differ from intent")
        return self


class SentimentAnalysis(SchemaModel):
    """Sentiment agent output for the latest customer utterance."""

    sentiment: SentimentType
    confidence: Confidence
    evidence: TextEvidence


class NextActionRecommendation(SchemaModel):
    """Controlled action recommendation for the human sales representative."""

    action: NextActionType
    rationale: Annotated[str, Field(min_length=1, max_length=1_000)]
    confidence: Confidence
    suggested_follow_up_date: date | None = None
    requires_confirmation: bool = True

    @model_validator(mode="before")
    @classmethod
    def discard_irrelevant_follow_up_date(cls, value: object) -> object:
        """Ignore harmless provider metadata on non-follow-up actions."""

        if isinstance(value, dict) and value.get("action") != NextActionType.SCHEDULE_FOLLOW_UP:
            normalized = dict(value)
            normalized["suggested_follow_up_date"] = None
            return normalized
        return value

    @model_validator(mode="after")
    def validate_follow_up_date(self) -> Self:
        """Permit a date only for a schedule-follow-up recommendation."""

        if (
            self.suggested_follow_up_date is not None
            and self.action is not NextActionType.SCHEDULE_FOLLOW_UP
        ):
            raise ValueError("suggested_follow_up_date is only valid for schedule_follow_up")
        if (
            self.action is NextActionType.SCHEDULE_FOLLOW_UP
            and self.suggested_follow_up_date is None
        ):
            raise ValueError("schedule_follow_up requires a suggested date")
        return self


class WorkflowIssue(SchemaModel):
    """A sanitized, non-fatal or fatal issue recorded during graph execution."""

    stage: WorkflowStage
    code: ErrorCode
    message: Annotated[str, Field(min_length=1, max_length=500)]
    recoverable: bool


class AgentConfidenceScores(SchemaModel):
    """Per-agent confidence values used to explain the aggregate score."""

    intent: Confidence
    sentiment: Confidence
    entities: Confidence
    retrieval: Confidence
    response: Confidence
    next_action: Confidence


class CopilotResult(SchemaModel):
    """Final JSON payload sent to the real-time sales-agent console."""

    schema_version: Literal["1.0"] = "1.0"
    request_id: UUID
    session_id: UUID
    sequence_number: Annotated[int, Field(ge=0)]
    latest_transcript: Annotated[str, Field(min_length=1, max_length=10_000)]
    intent: IntentType
    sentiment: SentimentType
    entities: CustomerEntities
    retrieved_context: Annotated[tuple[RetrievedChunk, ...], Field(max_length=50)] = ()
    suggested_response: SuggestedResponse
    next_best_action: NextActionRecommendation
    crm_summary: CRMSummary | None = None
    guardrail: GuardrailOutput
    confidence: Confidence
    agent_confidences: AgentConfidenceScores
    issues: Annotated[tuple[WorkflowIssue, ...], Field(max_length=50)] = ()
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("issues")
    @classmethod
    def reject_duplicate_issues(
        cls,
        value: tuple[WorkflowIssue, ...],
    ) -> tuple[WorkflowIssue, ...]:
        """Reject duplicate stage/code pairs to keep errors actionable."""

        keys = tuple((issue.stage, issue.code) for issue in value)
        if len(keys) != len(set(keys)):
            raise ValueError("issues cannot repeat the same stage and error code")
        return value

    @model_validator(mode="after")
    def validate_final_payload(self) -> Self:
        """Ensure the assembled result preserves grounding and guardrail output."""

        if self.generated_at.tzinfo is None:
            raise ValueError("generated_at must be timezone-aware")
        if self.suggested_response != self.guardrail.final_response:
            raise ValueError("suggested_response must be the guardrail-approved final response")

        retrieved_ids = {chunk.chunk_id for chunk in self.retrieved_context}
        cited_ids = set(self.suggested_response.citation_chunk_ids)
        if not cited_ids.issubset(retrieved_ids):
            raise ValueError("suggested_response contains citations absent from retrieved_context")

        if not self.guardrail.is_safe and not self.suggested_response.is_fallback:
            raise ValueError("an unsafe result must expose only a safe fallback response")
        return self


__all__ = [
    "AgentConfidenceScores",
    "CopilotResult",
    "IntentAnalysis",
    "NextActionRecommendation",
    "SentimentAnalysis",
    "WorkflowIssue",
]
