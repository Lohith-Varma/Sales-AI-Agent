import pytest
from ai.agents.rag.agent import RAGRetrievalAgent
from ai.schemas.rag import RetrievalOutput, RetrievalRequest


class FakeRetriever:
    async def retrieve(self, request: RetrievalRequest) -> RetrievalOutput:
        return RetrievalOutput(query=request.query, sufficient_context=False, confidence=0)


@pytest.mark.asyncio
async def test_rag_agent_delegates() -> None:
    request = RetrievalRequest(query="fees", top_k=3, fetch_k=5, minimum_relevance_score=0.6)
    result = await RAGRetrievalAgent(FakeRetriever()).run(request)
    assert result.query == "fees"
    assert not result.sufficient_context
