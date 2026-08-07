import pytest
from ai.agents.response.agent import ResponseGenerationAgent
from ai.schemas.entities import CustomerEntities
from ai.schemas.enums import IntentType, SentimentType
from ai.schemas.rag import RetrievalOutput
from ai.schemas.responses import ResponseGenerationRequest


@pytest.mark.asyncio
async def test_response_agent_uses_fallback_without_context(fake_llm_factory: type) -> None:
    agent = ResponseGenerationAgent(fake_llm_factory(), safe_fallback="Verify with an expert.")
    result = await agent.run(
        ResponseGenerationRequest(
            latest_customer_utterance="What is the fee?",
            intent=IntentType.PRICING,
            sentiment=SentimentType.NEUTRAL,
            entities=CustomerEntities(),
            retrieval=RetrievalOutput(query="fee", sufficient_context=False, confidence=0),
        )
    )
    assert result.suggestion.is_fallback
    assert result.suggestion.citation_chunk_ids == ()
