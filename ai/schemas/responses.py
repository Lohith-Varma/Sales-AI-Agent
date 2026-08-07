"""Contracts for RAG-grounded sales-response generation."""

from __future__ import annotations

from typing import Annotated, Self

from pydantic import Field, field_validator, model_validator

from ai.schemas.common import Confidence, SchemaModel
from ai.schemas.entities import CustomerEntities
from ai.schemas.enums import IntentType, SentimentType
from ai.schemas.rag import RetrievalOutput


class GroundedClaim(SchemaModel):
    """One factual product claim and the knowledge chunks supporting it."""

    claim: Annotated[str, Field(min_length=1, max_length=1_000)]
    citation_chunk_ids: Annotated[tuple[str, ...], Field(min_length=1, max_length=10)]

    @field_validator("citation_chunk_ids")
    @classmethod
    def reject_duplicate_citations(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        """Require a compact, unique citation set for each claim."""

        if len(value) != len(set(value)):
            raise ValueError("claim citations cannot contain duplicates")
        return value


class ResponseGenerationRequest(SchemaModel):
    """Bounded context supplied to the response generation agent."""

    latest_customer_utterance: Annotated[str, Field(min_length=1, max_length=10_000)]
    conversation_context: Annotated[tuple[str, ...], Field(max_length=100)] = ()
    intent: IntentType
    sentiment: SentimentType
    entities: CustomerEntities
    retrieval: RetrievalOutput


class SuggestedResponse(SchemaModel):
    """A concise suggestion shown to the human sales representative.

    A regular response must be backed by at least one retrieved chunk. An explicit
    fallback is allowed without citations when approved context is insufficient.
    """

    text: Annotated[str, Field(min_length=1, max_length=2_000)]
    grounded_claims: Annotated[tuple[GroundedClaim, ...], Field(max_length=20)] = ()
    citation_chunk_ids: Annotated[tuple[str, ...], Field(max_length=20)] = ()
    is_fallback: bool = False
    requires_human_review: bool = False
    confidence: Confidence

    @field_validator("citation_chunk_ids")
    @classmethod
    def reject_duplicate_response_citations(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        """Keep the response citation list stable and unambiguous."""

        if len(value) != len(set(value)):
            raise ValueError("response citations cannot contain duplicates")
        return value

    @model_validator(mode="after")
    def validate_grounding_shape(self) -> Self:
        """Enforce citation requirements for normal and fallback responses."""

        if self.is_fallback:
            if self.grounded_claims or self.citation_chunk_ids:
                raise ValueError("fallback responses cannot assert grounded product claims")
            return self

        if not self.citation_chunk_ids:
            raise ValueError("a non-fallback response requires at least one citation")
        if not self.grounded_claims:
            raise ValueError("a non-fallback response requires at least one grounded claim")

        response_citations = set(self.citation_chunk_ids)
        claim_citations = {
            chunk_id for claim in self.grounded_claims for chunk_id in claim.citation_chunk_ids
        }
        if claim_citations != response_citations:
            raise ValueError("response citations must exactly match the union of claim citations")
        return self


class ResponseGenerationOutput(SchemaModel):
    """Structured output returned by the response generation agent."""

    suggestion: SuggestedResponse
    source_chunk_count: Annotated[int, Field(ge=0, le=50)]

    @model_validator(mode="after")
    def validate_source_count(self) -> Self:
        """Prevent a grounded response from claiming an empty source set."""

        if not self.suggestion.is_fallback and self.source_chunk_count == 0:
            raise ValueError("a grounded suggestion requires source_chunk_count greater than zero")
        if self.source_chunk_count < len(self.suggestion.citation_chunk_ids):
            raise ValueError("source_chunk_count cannot be smaller than the citation count")
        return self


__all__ = [
    "GroundedClaim",
    "ResponseGenerationOutput",
    "ResponseGenerationRequest",
    "SuggestedResponse",
]
