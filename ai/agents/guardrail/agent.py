"""Final grounding, JSON, confidence, and financial-safety guardrail agent."""

from ai.agents.guardrail.grounding import GroundingVerifier
from ai.agents.guardrail.policy import FinancialSafetyPolicy
from ai.schemas.enums import GuardrailViolationType
from ai.schemas.guardrail import GuardrailOutput, GuardrailRequest, GuardrailViolation
from ai.schemas.responses import SuggestedResponse
from ai.utils.json import StructuredJSONError, load_json_object


class GuardrailAgent:
    name = "guardrail"
    version = "1.0"

    def __init__(
        self,
        *,
        grounding: GroundingVerifier,
        policy: FinancialSafetyPolicy,
        safe_fallback: str,
    ) -> None:
        self._grounding = grounding
        self._policy = policy
        self._safe_fallback = safe_fallback

    async def run(self, request: GuardrailRequest) -> GuardrailOutput:
        checks = self._grounding.verify(request.candidate, request.retrieval.chunks)
        supported = sum(check.is_supported for check in checks)
        coverage = supported / len(checks) if checks else 1.0
        is_grounded = all(check.is_supported for check in checks)
        violations: list[GuardrailViolation] = []
        for check in checks:
            if not check.is_supported:
                violations.append(
                    GuardrailViolation(
                        violation_type=GuardrailViolationType.UNSUPPORTED_CLAIM,
                        severity="error",
                        message="A response claim is not supported by its citations.",
                        claim=check.claim,
                    )
                )
        if coverage < request.minimum_grounding_coverage:
            is_grounded = False
        valid_json = True
        if request.raw_model_output is not None:
            try:
                load_json_object(request.raw_model_output)
            except StructuredJSONError:
                valid_json = False
                violations.append(
                    GuardrailViolation(
                        violation_type=GuardrailViolationType.INVALID_SCHEMA,
                        severity="error",
                        message="Model output was not one valid JSON object.",
                    )
                )
        if request.candidate.confidence < request.minimum_agent_confidence:
            violations.append(
                GuardrailViolation(
                    violation_type=GuardrailViolationType.LOW_CONFIDENCE,
                    severity="error",
                    message="Response confidence is below the configured threshold.",
                )
            )
        policy_result = self._policy.check(request.candidate.text)
        violations.extend(policy_result.violations)
        serious = any(item.severity in {"error", "critical"} for item in violations)
        is_safe = (
            valid_json
            and is_grounded
            and not policy_result.contains_financial_advice
            and not serious
        )
        final_response = request.candidate
        if not is_safe:
            final_response = SuggestedResponse(
                text=self._safe_fallback,
                is_fallback=True,
                requires_human_review=True,
                confidence=1.0,
            )
        return GuardrailOutput(
            is_safe=is_safe,
            is_grounded=is_grounded,
            valid_json=valid_json,
            contains_unsupported_financial_advice=policy_result.contains_financial_advice,
            grounding_coverage=coverage,
            claim_checks=checks,
            violations=tuple(violations),
            requires_human_review=not is_safe or request.candidate.requires_human_review,
            final_response=final_response,
        )


__all__ = ["GuardrailAgent"]
