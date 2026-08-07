"""Isolated RAG retrieval agent."""

from ai.agents.rag.retriever import KnowledgeRetriever
from ai.schemas.rag import RetrievalOutput, RetrievalRequest


class RAGRetrievalAgent:
    name = "rag_retrieval"
    version = "1.0"

    def __init__(self, retriever: KnowledgeRetriever) -> None:
        self._retriever = retriever

    async def run(self, request: RetrievalRequest) -> RetrievalOutput:
        return await self._retriever.retrieve(request)


__all__ = ["RAGRetrievalAgent"]
