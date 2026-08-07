"""Asynchronous boundary around persistent ChromaDB operations."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Protocol, cast

import chromadb
from chromadb.api.models.Collection import Collection

from ai.schemas.rag import DocumentChunk, RetrievedChunk
from ai.utils.exceptions import RetrievalError


class VectorStore(Protocol):
    """Storage interface consumed by RAG indexer and retriever components."""

    async def upsert(self, chunks: list[DocumentChunk], embeddings: list[list[float]]) -> None: ...
    async def search(self, embedding: list[float], *, limit: int) -> list[RetrievedChunk]: ...
    async def count(self) -> int: ...


class ChromaVectorStore:
    """Persistent cosine-similarity Chroma collection."""

    def __init__(self, *, persist_directory: Path, collection_name: str) -> None:
        persist_directory.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(persist_directory))
        self._collection: Collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self._lock = asyncio.Lock()

    async def upsert(self, chunks: list[DocumentChunk], embeddings: list[list[float]]) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have identical lengths")
        if not chunks:
            return
        metadatas: list[dict[str, str | int | float | bool]] = []
        for chunk in chunks:
            metadata: dict[str, str | int | float | bool] = {
                "document_id": chunk.document_id,
                "source": chunk.metadata.source,
                "title": chunk.metadata.title,
                "document_type": chunk.metadata.document_type.value,
                "chunk_index": chunk.chunk_index,
                "content_sha256": chunk.content_sha256,
            }
            if chunk.page_number is not None:
                metadata["page_number"] = chunk.page_number
            if chunk.section is not None:
                metadata["section"] = chunk.section
            metadatas.append(metadata)
        try:
            async with self._lock:
                await asyncio.to_thread(
                    self._collection.upsert,
                    ids=[chunk.chunk_id for chunk in chunks],
                    documents=[chunk.text for chunk in chunks],
                    embeddings=cast(Any, embeddings),
                    metadatas=cast(Any, metadatas),
                )
        except Exception as exc:
            raise RetrievalError(f"Chroma upsert failed: {type(exc).__name__}") from exc

    async def search(self, embedding: list[float], *, limit: int) -> list[RetrievedChunk]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        try:
            result = await asyncio.to_thread(
                self._collection.query,
                query_embeddings=cast(Any, [embedding]),
                n_results=limit,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            raise RetrievalError(f"Chroma query failed: {type(exc).__name__}") from exc

        ids = cast(list[list[str]], result.get("ids") or [[]])[0]
        documents = cast(list[list[str]], result.get("documents") or [[]])[0]
        metadatas = cast(list[list[dict[str, Any]]], result.get("metadatas") or [[]])[0]
        distances = cast(list[list[float]], result.get("distances") or [[]])[0]
        chunks: list[RetrievedChunk] = []
        for chunk_id, text, metadata, distance in zip(
            ids, documents, metadatas, distances, strict=True
        ):
            score = min(1.0, max(0.0, 1.0 - float(distance)))
            chunks.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    document_id=str(metadata["document_id"]),
                    text=text,
                    source=str(metadata["source"]),
                    title=str(metadata["title"]),
                    page_number=int(metadata["page_number"]) if "page_number" in metadata else None,
                    section=str(metadata["section"]) if "section" in metadata else None,
                    relevance_score=score,
                )
            )
        return chunks

    async def count(self) -> int:
        try:
            return int(await asyncio.to_thread(self._collection.count))
        except Exception as exc:
            raise RetrievalError(f"Chroma count failed: {type(exc).__name__}") from exc


__all__ = ["ChromaVectorStore", "VectorStore"]
