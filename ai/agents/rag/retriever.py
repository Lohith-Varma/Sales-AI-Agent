"""Thresholded semantic retrieval and bounded context assembly."""

from ai.models.embeddings import EmbeddingModel
from ai.schemas.rag import RetrievalOutput, RetrievalRequest
from ai.services.chroma_store import VectorStore
from ai.utils.text import join_bounded_text


class KnowledgeRetriever:
    def __init__(
        self,
        *,
        embeddings: EmbeddingModel,
        vector_store: VectorStore,
        maximum_context_characters: int,
    ) -> None:
        self._embeddings = embeddings
        self._vector_store = vector_store
        self._maximum_context_characters = maximum_context_characters

    async def retrieve(self, request: RetrievalRequest) -> RetrievalOutput:
        """Retrieve, filter, rank, and render approved context chunks."""

        query_vector = await self._embeddings.embed_query(request.query)
        candidates = await self._vector_store.search(query_vector, limit=request.fetch_k)
        accepted = tuple(
            chunk
            for chunk in candidates
            if chunk.relevance_score >= request.minimum_relevance_score
        )[: request.top_k]
        rendered = (
            f"[chunk_id={chunk.chunk_id}; source={chunk.source}; page={chunk.page_number}]\n"
            f"{chunk.text}"
            for chunk in accepted
        )
        context = join_bounded_text(
            rendered,
            max_characters=self._maximum_context_characters,
            separator="\n\n",
        )
        confidence = accepted[0].relevance_score if accepted else 0.0
        return RetrievalOutput(
            query=request.query,
            chunks=accepted,
            context_text=context,
            sufficient_context=bool(accepted and context),
            confidence=confidence,
        )


__all__ = ["KnowledgeRetriever"]
