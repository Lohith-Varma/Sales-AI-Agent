"""Shared Pydantic primitives for agent and transport contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Generic, Self, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ai.schemas.enums import ErrorCode

Confidence = Annotated[float, Field(ge=0.0, le=1.0)]
NonEmptyText = Annotated[str, Field(min_length=1)]


class SchemaModel(BaseModel):
    """Strict base class for internal and external application contracts."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
        validate_default=True,
        use_enum_values=False,
    )


class TextEvidence(SchemaModel):
    """A bounded excerpt supporting an agent classification or extraction."""

    text: Annotated[str, Field(min_length=1, max_length=500)]
    start_character: Annotated[int, Field(ge=0)] | None = None
    end_character: Annotated[int, Field(gt=0)] | None = None

    @model_validator(mode="after")
    def validate_character_range(self) -> Self:
        """Require complete, ordered offsets when character positions are used."""

        has_start = self.start_character is not None
        has_end = self.end_character is not None
        if has_start != has_end:
            raise ValueError("start_character and end_character must be provided together")
        if has_start and self.end_character <= self.start_character:  # type: ignore[operator]
            raise ValueError("end_character must be greater than start_character")
        return self


class AgentExecutionMetadata(SchemaModel):
    """Operational metadata emitted for observability, not model reasoning."""

    agent_name: Annotated[str, Field(min_length=1, max_length=100)]
    agent_version: Annotated[str, Field(min_length=1, max_length=50)] = "1.0"
    model_name: Annotated[str, Field(min_length=1, max_length=200)] | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    duration_ms: Annotated[float, Field(ge=0)] = 0.0
    attempt: Annotated[int, Field(ge=1, le=10)] = 1


class AgentError(SchemaModel):
    """Sanitized failure information safe to pass between application layers."""

    code: ErrorCode
    message: Annotated[str, Field(min_length=1, max_length=500)]
    retryable: bool = False
    agent_name: Annotated[str, Field(min_length=1, max_length=100)] | None = None


OutputT = TypeVar("OutputT")


class AgentResult(SchemaModel, Generic[OutputT]):
    """Generic success/failure envelope returned by every isolated agent.

    Exactly one of ``output`` and ``error`` is populated. This prevents graph
    nodes from treating a failed call as a valid empty prediction.
    """

    output: OutputT | None = None
    error: AgentError | None = None
    metadata: AgentExecutionMetadata

    @model_validator(mode="after")
    def validate_result_state(self) -> Self:
        """Enforce mutually exclusive success and failure states."""

        if (self.output is None) == (self.error is None):
            raise ValueError("exactly one of output or error must be provided")
        return self

    @property
    def succeeded(self) -> bool:
        """Return whether the agent produced a validated output."""

        return self.output is not None


class RequestContext(SchemaModel):
    """Correlation identifiers propagated through one graph execution."""

    request_id: UUID
    session_id: UUID
    sequence_number: Annotated[int, Field(ge=0)]
    received_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


__all__ = [
    "AgentError",
    "AgentExecutionMetadata",
    "AgentResult",
    "Confidence",
    "NonEmptyText",
    "RequestContext",
    "SchemaModel",
    "TextEvidence",
]
