"""Typed LangGraph state and workflow input contracts."""

from __future__ import annotations

from typing import Annotated, NotRequired, TypedDict

from pydantic import Field, model_validator

from ai.schemas.common import RequestContext, SchemaModel
from ai.schemas.entities import CustomerEntities, EntityExtractionOutput
from ai.schemas.guardrail import GuardrailOutput
from ai.schemas.orchestration import (
    CopilotResult,
    IntentAnalysis,
    NextActionRecommendation,
    SentimentAnalysis,
    WorkflowIssue,
)
from ai.schemas.rag import RetrievalOutput
from ai.schemas.responses import ResponseGenerationOutput
from ai.schemas.speech import TranscriptionOutput, TranscriptionRequest


class LiveWorkflowInput(SchemaModel):
    """Input for either audio-backed or text-only live analysis."""

    context: RequestContext
    transcription_request: TranscriptionRequest | None = None
    latest_customer_utterance: Annotated[str, Field(min_length=1, max_length=10_000)] | None = None
    conversation_context: Annotated[tuple[str, ...], Field(max_length=100)] = ()
    known_entities: CustomerEntities = Field(default_factory=CustomerEntities)

    @model_validator(mode="after")
    def require_one_input_mode(self) -> LiveWorkflowInput:
        if (self.transcription_request is None) == (self.latest_customer_utterance is None):
            raise ValueError(
                "provide exactly one of transcription_request or latest_customer_utterance"
            )
        return self


class CopilotState(TypedDict):
    context: RequestContext
    conversation_context: tuple[str, ...]
    known_entities: CustomerEntities
    transcription_request: NotRequired[TranscriptionRequest]
    transcription: NotRequired[TranscriptionOutput]
    latest_customer_utterance: NotRequired[str]
    intent: NotRequired[IntentAnalysis]
    sentiment: NotRequired[SentimentAnalysis]
    entity_output: NotRequired[EntityExtractionOutput]
    retrieval: NotRequired[RetrievalOutput]
    response: NotRequired[ResponseGenerationOutput]
    next_action: NotRequired[NextActionRecommendation]
    guardrail: NotRequired[GuardrailOutput]
    issues: NotRequired[tuple[WorkflowIssue, ...]]
    result: NotRequired[CopilotResult]


__all__ = ["CopilotState", "LiveWorkflowInput"]
