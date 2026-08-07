"""Schemas for evidence-backed customer entity extraction."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import Field, field_validator

from ai.schemas.common import Confidence, SchemaModel, TextEvidence
from ai.schemas.enums import EmploymentType

EntityFieldName = Literal[
    "salary",
    "age",
    "city",
    "occupation",
    "loan_amount",
    "employment_type",
    "customer_name",
]

_ENTITY_FIELD_NAMES: tuple[EntityFieldName, ...] = (
    "salary",
    "age",
    "city",
    "occupation",
    "loan_amount",
    "employment_type",
    "customer_name",
)

EntityValueT = TypeVar("EntityValueT")


class ExtractedEntity(SchemaModel, Generic[EntityValueT]):
    """One normalized value with direct support from the transcript."""

    value: EntityValueT
    confidence: Confidence
    evidence: TextEvidence


class MoneyAmount(SchemaModel):
    """A positive monetary value that preserves its stated currency."""

    amount: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=2)]
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")]

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: object) -> object:
        """Normalize an explicit ISO-like currency code to uppercase."""

        return value.strip().upper() if isinstance(value, str) else value


class CustomerEntities(SchemaModel):
    """Normalized customer facts explicitly present in the conversation.

    Every field is optional because omission means the customer has not stated a
    sufficiently supported value. Missing values must never be guessed.
    """

    salary: ExtractedEntity[MoneyAmount] | None = None
    age: ExtractedEntity[Annotated[int, Field(ge=18, le=120)]] | None = None
    city: ExtractedEntity[Annotated[str, Field(min_length=1, max_length=150)]] | None = None
    occupation: ExtractedEntity[Annotated[str, Field(min_length=1, max_length=200)]] | None = None
    loan_amount: ExtractedEntity[MoneyAmount] | None = None
    employment_type: ExtractedEntity[EmploymentType] | None = None
    customer_name: ExtractedEntity[Annotated[str, Field(min_length=1, max_length=200)]] | None = (
        None
    )

    def populated_field_names(self) -> tuple[EntityFieldName, ...]:
        """Return stable names for fields with evidence-backed values."""

        return tuple(
            field_name
            for field_name in _ENTITY_FIELD_NAMES
            if getattr(self, field_name) is not None
        )


class EntityExtractionRequest(SchemaModel):
    """Conversation text supplied to the entity extraction agent."""

    latest_customer_utterance: Annotated[str, Field(min_length=1, max_length=10_000)]
    conversation_context: Annotated[tuple[str, ...], Field(max_length=100)] = ()
    known_entities: CustomerEntities = Field(default_factory=CustomerEntities)


class EntityExtractionOutput(SchemaModel):
    """Complete evidence-backed entity result for the current graph pass."""

    entities: CustomerEntities
    newly_extracted_fields: tuple[EntityFieldName, ...] = ()
    missing_fields: tuple[EntityFieldName, ...] = ()
    confidence: Confidence

    @field_validator("newly_extracted_fields", "missing_fields")
    @classmethod
    def reject_duplicate_field_names(
        cls,
        value: tuple[EntityFieldName, ...],
    ) -> tuple[EntityFieldName, ...]:
        """Reject repeated field names that could confuse graph merge logic."""

        if len(value) != len(set(value)):
            raise ValueError("entity field-name collections cannot contain duplicates")
        return value


__all__ = [
    "CustomerEntities",
    "EntityExtractionOutput",
    "EntityExtractionRequest",
    "EntityFieldName",
    "ExtractedEntity",
    "MoneyAmount",
]
