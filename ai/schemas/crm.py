"""Schemas for auditable post-call CRM summarization and lead scoring."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Annotated, Self

from pydantic import Field, field_validator, model_validator

from ai.schemas.common import Confidence, SchemaModel
from ai.schemas.entities import CustomerEntities
from ai.schemas.enums import (
    IntentType,
    LeadStatus,
    LeadTemperature,
    NextActionType,
    SentimentType,
)


class LeadScoreFactor(SchemaModel):
    """One explainable positive or negative contribution to a lead score."""

    name: Annotated[str, Field(min_length=1, max_length=100)]
    points: Annotated[int, Field(ge=-100, le=100)]
    rationale: Annotated[str, Field(min_length=1, max_length=500)]


class LeadScore(SchemaModel):
    """Deterministic 0-100 score with a complete factor breakdown."""

    score: Annotated[int, Field(ge=0, le=100)]
    temperature: LeadTemperature
    factors: Annotated[tuple[LeadScoreFactor, ...], Field(min_length=1, max_length=30)]

    @model_validator(mode="after")
    def validate_score_calculation(self) -> Self:
        """Require the reported score and temperature to match the factors."""

        calculated_score = min(100, max(0, sum(factor.points for factor in self.factors)))
        if self.score != calculated_score:
            raise ValueError("lead score must equal the clamped sum of factor points")

        expected_temperature = (
            LeadTemperature.COLD
            if self.score < 40
            else LeadTemperature.WARM
            if self.score < 70
            else LeadTemperature.HOT
        )
        if self.temperature is not expected_temperature:
            raise ValueError("lead temperature does not match the numeric score")
        return self


class CRMGenerationRequest(SchemaModel):
    """Complete, bounded call state supplied to the post-call CRM agent."""

    transcript: Annotated[str, Field(min_length=1, max_length=200_000)]
    primary_intent: IntentType
    final_sentiment: SentimentType
    entities: CustomerEntities
    recommended_action: NextActionType
    call_started_at: datetime
    call_ended_at: datetime

    @model_validator(mode="after")
    def validate_call_timestamps(self) -> Self:
        """Ensure the call has a positive duration and timezone-aware timestamps."""

        if self.call_started_at.tzinfo is None or self.call_ended_at.tzinfo is None:
            raise ValueError("call timestamps must be timezone-aware")
        if self.call_ended_at <= self.call_started_at:
            raise ValueError("call_ended_at must be later than call_started_at")
        return self


class CRMSummary(SchemaModel):
    """Structured CRM fields generated after the call for human review."""

    call_summary: Annotated[str, Field(min_length=1, max_length=5_000)]
    lead_score: LeadScore
    follow_up_date: date | None = None
    customer_concern: Annotated[str, Field(min_length=1, max_length=1_000)] | None = None
    lead_status: LeadStatus
    important_notes: Annotated[tuple[str, ...], Field(max_length=30)] = ()
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("important_notes")
    @classmethod
    def validate_notes(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        """Reject blank or duplicate notes while preserving their order."""

        normalized = tuple(note.strip() for note in value)
        if any(not note for note in normalized):
            raise ValueError("important notes cannot be blank")
        if len(normalized) != len(set(normalized)):
            raise ValueError("important notes cannot contain duplicates")
        return normalized

    @model_validator(mode="after")
    def validate_follow_up(self) -> Self:
        """Require actionable, non-past follow-up dates for follow-up leads."""

        if self.generated_at.tzinfo is None:
            raise ValueError("generated_at must be timezone-aware")
        if self.follow_up_date is not None and self.follow_up_date < self.generated_at.date():
            raise ValueError("follow_up_date cannot be earlier than the generation date")
        if self.lead_status is LeadStatus.FOLLOW_UP_REQUIRED and self.follow_up_date is None:
            raise ValueError("follow_up_date is required when follow-up is required")
        return self


class CRMGenerationOutput(SchemaModel):
    """Post-call CRM agent output and confidence estimate."""

    crm_summary: CRMSummary
    confidence: Confidence
    requires_human_review: bool = True


__all__ = [
    "CRMGenerationOutput",
    "CRMGenerationRequest",
    "CRMSummary",
    "LeadScore",
    "LeadScoreFactor",
]
