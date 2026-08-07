"""Input contracts for classification and next-action agents."""

from typing import Annotated

from pydantic import Field

from ai.schemas.common import SchemaModel
from ai.schemas.entities import CustomerEntities
from ai.schemas.orchestration import IntentAnalysis, SentimentAnalysis
from ai.schemas.rag import RetrievalOutput


class IntentDetectionRequest(SchemaModel):
    latest_customer_utterance: Annotated[str, Field(min_length=1, max_length=10_000)]
    conversation_context: Annotated[tuple[str, ...], Field(max_length=100)] = ()


class SentimentDetectionRequest(SchemaModel):
    latest_customer_utterance: Annotated[str, Field(min_length=1, max_length=10_000)]
    conversation_context: Annotated[tuple[str, ...], Field(max_length=100)] = ()


class NextActionRequest(SchemaModel):
    latest_customer_utterance: Annotated[str, Field(min_length=1, max_length=10_000)]
    intent: IntentAnalysis
    sentiment: SentimentAnalysis
    entities: CustomerEntities
    retrieval: RetrievalOutput


__all__ = ["IntentDetectionRequest", "NextActionRequest", "SentimentDetectionRequest"]
