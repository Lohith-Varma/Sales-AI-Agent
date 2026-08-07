import pytest
from ai.agents.entity.agent import EntityExtractionAgent
from ai.schemas.entities import CustomerEntities, EntityExtractionOutput, EntityExtractionRequest


@pytest.mark.asyncio
async def test_entity_agent_preserves_empty_entities(fake_llm_factory: type) -> None:
    expected = EntityExtractionOutput(entities=CustomerEntities(), confidence=0.7)
    result = await EntityExtractionAgent(fake_llm_factory(expected)).run(
        EntityExtractionRequest(latest_customer_utterance="Tell me more")
    )
    assert result.entities.populated_field_names() == ()
