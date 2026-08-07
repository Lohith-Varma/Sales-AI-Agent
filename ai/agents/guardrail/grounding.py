"""Deterministic claim-to-citation grounding verification."""

import re
from typing import Final

from ai.schemas.guardrail import ClaimGroundingCheck
from ai.schemas.rag import RetrievedChunk
from ai.schemas.responses import SuggestedResponse

_TOKEN: Final = re.compile(r"[A-Za-z0-9]+")
_STOPWORDS: Final = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "with",
        "you",
        "your",
    }
)


def _tokens(value: str) -> set[str]:
    return {token.casefold() for token in _TOKEN.findall(value)} - _STOPWORDS


class GroundingVerifier:
    """Require meaningful lexical support inside each explicitly cited chunk."""

    def __init__(self, *, minimum_claim_overlap: float = 0.35) -> None:
        self._minimum_claim_overlap = minimum_claim_overlap

    def verify(
        self,
        suggestion: SuggestedResponse,
        chunks: tuple[RetrievedChunk, ...],
    ) -> tuple[ClaimGroundingCheck, ...]:
        chunk_map = {chunk.chunk_id: chunk for chunk in chunks}
        checks: list[ClaimGroundingCheck] = []
        for grounded_claim in suggestion.grounded_claims:
            claim_tokens = _tokens(grounded_claim.claim)
            supported: list[str] = []
            best_score = 0.0
            for chunk_id in grounded_claim.citation_chunk_ids:
                chunk = chunk_map.get(chunk_id)
                if chunk is None or not claim_tokens:
                    continue
                score = len(claim_tokens & _tokens(chunk.text)) / len(claim_tokens)
                best_score = max(best_score, score)
                if score >= self._minimum_claim_overlap:
                    supported.append(chunk_id)
            checks.append(
                ClaimGroundingCheck(
                    claim=grounded_claim.claim,
                    cited_chunk_ids=grounded_claim.citation_chunk_ids,
                    supported_chunk_ids=tuple(supported),
                    is_supported=bool(supported),
                    support_score=min(1.0, best_score),
                )
            )
        return tuple(checks)


__all__ = ["GroundingVerifier"]
