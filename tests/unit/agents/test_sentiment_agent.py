import pytest
from ai.agents.sentiment.agent import SentimentAgent
from ai.schemas.analysis import SentimentDetectionRequest
from ai.schemas.common import TextEvidence
from ai.schemas.enums import SentimentType
from ai.schemas.orchestration import SentimentAnalysis


@pytest.mark.asyncio
async def test_sentiment_agent_returns_structured_output(fake_llm_factory: type) -> None:
    expected = SentimentAnalysis(
        sentiment=SentimentType.CONFUSED,
        confidence=0.8,
        evidence=TextEvidence(text="I do not understand"),
    )
    result = await SentimentAgent(fake_llm_factory(expected)).run(
        SentimentDetectionRequest(latest_customer_utterance="I do not understand")
    )
    assert result.sentiment is SentimentType.CONFUSED
