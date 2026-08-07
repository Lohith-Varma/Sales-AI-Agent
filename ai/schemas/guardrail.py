"""Schemas for response grounding, policy checks, and safe finalization."""

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from ai.schemas.common import Confidence, SchemaModel
from ai.schemas.enums import GuardrailViolationType
from ai.schemas.rag import RetrievalOutput
from ai.schemas.responses import SuggestedResponse

ViolationSeverity = Literal["warning", "error", "critical"]


class GuardrailViolation(SchemaModel):
    """One actionable reason a candidate response requires intervention."""

    violation_type: GuardrailViolationType
    severity: ViolationSeverity
    message: Annotated[str, Field(min_length=1, max_length=500)]
    claim: Annotated[str, Field(min_length=1, max_length=1_000)] | None = None


class ClaimGroundingCheck(SchemaModel):
    """Grounding result for one factual claim in a suggested response."""

    claim: Annotated[str, Field(min_length=1, max_length=1_000)]
    cited_chunk_ids: Annotated[tuple[str, ...], Field(max_length=10)] = ()
    supported_chunk_ids: Annotated[tuple[str, ...], Field(max_length=10)] = ()
    is_supported: bool
    support_score: Confidence

    @model_validator(mode="after")
    def validate_support_state(self) -> Self:
        """Ensure supported citations are drawn from the claim's citations."""

        cited = set(self.cited_chunk_ids)
        supported = set(self.supported_chunk_ids)
        if not supported.issubset(cited):
            raise ValueError("supported chunks must be present in cited_chunk_ids")
        if self.is_supported and not supported:
            raise ValueError("a supported claim requires at least one supporting chunk")
        if not self.is_supported and self.support_score == 1.0:
            raise ValueError("an unsupported claim cannot have perfect support")
        return self


class GuardrailRequest(SchemaModel):
    """Candidate response and approved evidence supplied to the self-check agent."""

    candidate: SuggestedResponse
    retrieval: RetrievalOutput
    raw_model_output: Annotated[str, Field(min_length=1, max_length=100_000)] | None = None
    minimum_grounding_coverage: Confidence
    minimum_agent_confidence: Confidence


class GuardrailOutput(SchemaModel):
    """Final response decision returned to the orchestration graph."""

    is_safe: bool
    is_grounded: bool
    valid_json: bool
    contains_unsupported_financial_advice: bool
    grounding_coverage: Confidence
    claim_checks: Annotated[tuple[ClaimGroundingCheck, ...], Field(max_length=20)] = ()
    violations: Annotated[tuple[GuardrailViolation, ...], Field(max_length=50)] = ()
    requires_human_review: bool
    final_response: SuggestedResponse

    @model_validator(mode="after")
    def validate_decision_consistency(self) -> Self:
        """Prevent contradictory safety decisions from leaving the guardrail."""

        has_unsupported_claim = any(not check.is_supported for check in self.claim_checks)
        if self.is_grounded == has_unsupported_claim:
            raise ValueError("is_grounded must reflect claim-level support checks")

        serious_violation = any(
            violation.severity in {"error", "critical"} for violation in self.violations
        )
        unsafe_condition = (
            not self.valid_json
            or not self.is_grounded
            or self.contains_unsupported_financial_advice
            or serious_violation
        )
        if self.is_safe == unsafe_condition:
            raise ValueError("is_safe is inconsistent with guardrail findings")
        if not self.is_safe and not self.requires_human_review:
            raise ValueError("unsafe responses must require human review")
        if not self.is_safe and not self.final_response.is_fallback:
            raise ValueError("an unsafe candidate must be replaced by a safe fallback")
        return self


__all__ = [
    "ClaimGroundingCheck",
    "GuardrailOutput",
    "GuardrailRequest",
    "GuardrailViolation",
    "ViolationSeverity",
]
