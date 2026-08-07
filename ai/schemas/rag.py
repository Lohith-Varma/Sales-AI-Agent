"""Schemas for knowledge ingestion, indexing, and grounded retrieval."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Self

from pydantic import Field, field_validator, model_validator

from ai.schemas.common import Confidence, SchemaModel
from ai.schemas.enums import DocumentType, IntentType

MetadataScalar = str | int | float | bool


class DocumentMetadata(SchemaModel):
    """Traceable metadata attached to one approved knowledge document."""

    source: Annotated[str, Field(min_length=1, max_length=1_000)]
    document_type: DocumentType
    title: Annotated[str, Field(min_length=1, max_length=500)]
    version: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    effective_date: datetime | None = None
    tags: Annotated[tuple[str, ...], Field(max_length=50)] = ()
    attributes: dict[str, MetadataScalar] = Field(default_factory=dict)

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        """Normalize tags while retaining their original ordering."""

        normalized = tuple(tag.strip().casefold() for tag in value if tag.strip())
        if len(normalized) != len(set(normalized)):
            raise ValueError("document tags cannot contain duplicates")
        return normalized


class KnowledgeDocument(SchemaModel):
    """Normalized text loaded from a PDF, FAQ, Markdown, or text source."""

    document_id: Annotated[str, Field(min_length=1, max_length=300)]
    content: Annotated[str, Field(min_length=1)]
    content_sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    metadata: DocumentMetadata
    page_number: Annotated[int, Field(ge=1)] | None = None


class DocumentChunk(SchemaModel):
    """A deterministic, embeddable unit derived from a knowledge document."""

    chunk_id: Annotated[str, Field(min_length=1, max_length=500)]
    document_id: Annotated[str, Field(min_length=1, max_length=300)]
    text: Annotated[str, Field(min_length=1)]
    content_sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    chunk_index: Annotated[int, Field(ge=0)]
    start_character: Annotated[int, Field(ge=0)]
    end_character: Annotated[int, Field(gt=0)]
    page_number: Annotated[int, Field(ge=1)] | None = None
    section: Annotated[str, Field(min_length=1, max_length=500)] | None = None
    metadata: DocumentMetadata

    @model_validator(mode="after")
    def validate_character_range(self) -> Self:
        """Ensure the source character range is ordered and plausible."""

        if self.end_character <= self.start_character:
            raise ValueError("end_character must be greater than start_character")
        if self.end_character - self.start_character < len(self.text.strip()):
            raise ValueError("chunk character range cannot be shorter than its text")
        return self


class RetrievedChunk(SchemaModel):
    """A retrieved knowledge chunk with normalized similarity information."""

    chunk_id: Annotated[str, Field(min_length=1, max_length=500)]
    document_id: Annotated[str, Field(min_length=1, max_length=300)]
    text: Annotated[str, Field(min_length=1)]
    source: Annotated[str, Field(min_length=1, max_length=1_000)]
    title: Annotated[str, Field(min_length=1, max_length=500)]
    page_number: Annotated[int, Field(ge=1)] | None = None
    section: Annotated[str, Field(min_length=1, max_length=500)] | None = None
    relevance_score: Confidence


class RetrievalRequest(SchemaModel):
    """Semantic-search input constructed from the current conversation state."""

    query: Annotated[str, Field(min_length=1, max_length=5_000)]
    intent: IntentType | None = None
    top_k: Annotated[int, Field(ge=1, le=50)]
    fetch_k: Annotated[int, Field(ge=1, le=200)]
    minimum_relevance_score: Confidence

    @model_validator(mode="after")
    def validate_candidate_count(self) -> Self:
        """Require the candidate pool to contain at least the requested results."""

        if self.fetch_k < self.top_k:
            raise ValueError("fetch_k must be greater than or equal to top_k")
        return self


class RetrievalOutput(SchemaModel):
    """Ranked evidence returned to response and guardrail agents."""

    query: Annotated[str, Field(min_length=1, max_length=5_000)]
    chunks: tuple[RetrievedChunk, ...] = ()
    context_text: str = ""
    sufficient_context: bool
    confidence: Confidence

    @model_validator(mode="after")
    def validate_context_state(self) -> Self:
        """Prevent a successful retrieval state without supporting evidence."""

        if self.sufficient_context and not self.chunks:
            raise ValueError("sufficient_context requires at least one retrieved chunk")
        if not self.chunks and self.context_text:
            raise ValueError("context_text must be empty when no chunks were retrieved")
        chunk_ids = tuple(chunk.chunk_id for chunk in self.chunks)
        if len(chunk_ids) != len(set(chunk_ids)):
            raise ValueError("retrieval output cannot contain duplicate chunks")
        return self


class IngestionResult(SchemaModel):
    """Auditable outcome of one document-ingestion operation."""

    source: Annotated[str, Field(min_length=1, max_length=1_000)]
    document_count: Annotated[int, Field(ge=0)]
    chunk_count: Annotated[int, Field(ge=0)]
    skipped_unchanged_count: Annotated[int, Field(ge=0)] = 0
    collection_name: Annotated[str, Field(min_length=1, max_length=200)]
    completed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


__all__ = [
    "DocumentChunk",
    "DocumentMetadata",
    "IngestionResult",
    "KnowledgeDocument",
    "MetadataScalar",
    "RetrievalOutput",
    "RetrievalRequest",
    "RetrievedChunk",
]
