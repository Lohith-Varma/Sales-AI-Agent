"""Deterministic financial-safety and prohibited-language checks."""

import re
from dataclasses import dataclass
from typing import Final

from ai.schemas.enums import GuardrailViolationType
from ai.schemas.guardrail import GuardrailViolation

_GUARANTEE: Final = re.compile(
    r"\b(guaranteed?\s+(approval|eligible)|definitely\s+(approved|eligible)|100%\s+approved)\b",
    re.IGNORECASE,
)
_ADVICE: Final = re.compile(
    r"\b(you should borrow|best financial decision|I recommend (that )?you take|risk[- ]free)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class PolicyResult:
    violations: tuple[GuardrailViolation, ...]
    contains_financial_advice: bool


class FinancialSafetyPolicy:
    def check(self, text: str) -> PolicyResult:
        violations: list[GuardrailViolation] = []
        if _GUARANTEE.search(text):
            violations.append(
                GuardrailViolation(
                    violation_type=GuardrailViolationType.GUARANTEED_APPROVAL,
                    severity="critical",
                    message="Response implies guaranteed approval or eligibility.",
                )
            )
        contains_advice = bool(_ADVICE.search(text))
        if contains_advice:
            violations.append(
                GuardrailViolation(
                    violation_type=GuardrailViolationType.FINANCIAL_ADVICE,
                    severity="critical",
                    message="Response contains personalized financial advice.",
                )
            )
        return PolicyResult(tuple(violations), contains_advice)


__all__ = ["FinancialSafetyPolicy", "PolicyResult"]
