import pytest
from ai.agents.next_action.agent import NextBestActionAgent
from ai.schemas.analysis import NextActionRequest
from ai.schemas.common import TextEvidence
from ai.schemas.entities import CustomerEntities
from ai.schemas.enums import IntentType, NextActionType, SentimentType
from ai.schemas.orchestration import IntentAnalysis, NextActionRecommendation, SentimentAnalysis
from ai.schemas.rag import RetrievalOutput


@pytest.mark.asyncio
async def test_next_action_agent_uses_controlled_action(fake_llm_factory: type) -> None:
    expected = NextActionRecommendation(
        action=NextActionType.EXPLAIN_BENEFITS,
        rationale="Customer asked about the product.",
        confidence=0.8,
    )
    request = NextActionRequest(
        latest_customer_utterance="What are the benefits?",
        intent=IntentAnalysis(
            intent=IntentType.PRODUCT_INQUIRY,
            confidence=0.9,
            evidence=TextEvidence(text="benefits"),
        ),
        sentiment=SentimentAnalysis(
            sentiment=SentimentType.NEUTRAL, confidence=0.9, evidence=TextEvidence(text="benefits")
        ),
        entities=CustomerEntities(),
        retrieval=RetrievalOutput(query="benefits", sufficient_context=False, confidence=0),
    )
    result = await NextBestActionAgent(fake_llm_factory(expected)).run(request)
    assert result.action is NextActionType.EXPLAIN_BENEFITS
