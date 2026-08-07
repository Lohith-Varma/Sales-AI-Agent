import pytest
from ai.agents.guardrail.agent import GuardrailAgent
from ai.agents.guardrail.grounding import GroundingVerifier
from ai.agents.guardrail.policy import FinancialSafetyPolicy
from ai.schemas.guardrail import GuardrailRequest
from ai.schemas.rag import RetrievalOutput, RetrievedChunk
from ai.schemas.responses import GroundedClaim, SuggestedResponse


@pytest.mark.asyncio
async def test_guardrail_replaces_guaranteed_approval() -> None:
    chunk = RetrievedChunk(
        chunk_id="c1",
        document_id="d1",
        text="Applications are reviewed.",
        source="p.txt",
        title="Policy",
        relevance_score=0.9,
    )
    candidate = SuggestedResponse(
        text="You are guaranteed approval.",
        grounded_claims=(
            GroundedClaim(claim="You are guaranteed approval.", citation_chunk_ids=("c1",)),
        ),
        citation_chunk_ids=("c1",),
        confidence=0.9,
    )
    output = await GuardrailAgent(
        grounding=GroundingVerifier(),
        policy=FinancialSafetyPolicy(),
        safe_fallback="Ask an expert.",
    ).run(
        GuardrailRequest(
            candidate=candidate,
            retrieval=RetrievalOutput(
                query="approval",
                chunks=(chunk,),
                context_text=chunk.text,
                sufficient_context=True,
                confidence=0.9,
            ),
            minimum_grounding_coverage=1,
            minimum_agent_confidence=0.5,
        )
    )
    assert not output.is_safe
    assert output.final_response.is_fallback
