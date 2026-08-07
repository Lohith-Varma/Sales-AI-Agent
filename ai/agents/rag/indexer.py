"""Batch embedding and Chroma indexing component."""

from ai.models.embeddings import EmbeddingModel
from ai.schemas.rag import DocumentChunk
from ai.services.chroma_store import VectorStore


class KnowledgeIndexer:
    def __init__(
        self,
        *,
        embeddings: EmbeddingModel,
        vector_store: VectorStore,
        batch_size: int,
    ) -> None:
        self._embeddings = embeddings
        self._vector_store = vector_store
        self._batch_size = batch_size

    async def index(self, chunks: list[DocumentChunk]) -> int:
        """Embed and idempotently upsert chunks in bounded batches."""

        indexed = 0
        for start in range(0, len(chunks), self._batch_size):
            batch = chunks[start : start + self._batch_size]
            vectors = await self._embeddings.embed_documents([chunk.text for chunk in batch])
            await self._vector_store.upsert(batch, vectors)
            indexed += len(batch)
        return indexed


__all__ = ["KnowledgeIndexer"]
