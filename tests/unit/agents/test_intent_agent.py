import pytest
from ai.agents.intent.agent import IntentDetectionAgent
from ai.schemas.analysis import IntentDetectionRequest
from ai.schemas.common import TextEvidence
from ai.schemas.enums import IntentType
from ai.schemas.orchestration import IntentAnalysis


@pytest.mark.asyncio
async def test_intent_agent_returns_structured_output(fake_llm_factory: type) -> None:
    expected = IntentAnalysis(
        intent=IntentType.ELIGIBILITY,
        confidence=0.9,
        evidence=TextEvidence(text="am I eligible"),
    )
    result = await IntentDetectionAgent(fake_llm_factory(expected)).run(
        IntentDetectionRequest(latest_customer_utterance="am I eligible")
    )
    assert result == expected
