"""Sentence Transformers embedding adapter."""

from __future__ import annotations

import asyncio
from typing import Protocol

from sentence_transformers import SentenceTransformer

from ai.utils.exceptions import ModelUnavailableError


class EmbeddingModel(Protocol):
    """Provider-neutral dense embedding interface."""

    @property
    def dimension(self) -> int: ...

    async def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    async def embed_query(self, text: str) -> list[float]: ...


class SentenceTransformerEmbeddingModel:
    """Lazy, asynchronous wrapper around a local Sentence Transformer model."""

    def __init__(
        self,
        *,
        model_name: str,
        device: str,
        batch_size: int,
        normalize: bool,
    ) -> None:
        self._model_name = model_name
        self._device = device
        self._batch_size = batch_size
        self._normalize = normalize
        self._model: SentenceTransformer | None = None
        self._load_lock = asyncio.Lock()

    async def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            async with self._load_lock:
                if self._model is None:
                    try:
                        self._model = await asyncio.to_thread(
                            SentenceTransformer,
                            self._model_name,
                            device=self._device,
                        )
                    except Exception as exc:
                        raise ModelUnavailableError(
                            "sentence_transformers", type(exc).__name__, retryable=False
                        ) from exc
        if self._model is None:  # pragma: no cover - defensive after guarded load
            raise ModelUnavailableError("sentence_transformers", "model did not load")
        return self._model

    @property
    def dimension(self) -> int:
        if self._model is None:
            raise RuntimeError("embedding dimension is unavailable before model loading")
        dimension = self._model.get_sentence_embedding_dimension()
        if dimension is None:
            raise RuntimeError("embedding model did not report a dimension")
        return int(dimension)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed non-empty document text in a worker thread."""

        if not texts or any(not text.strip() for text in texts):
            raise ValueError("texts must contain at least one non-blank document")
        model = await self._get_model()
        try:
            vectors = await asyncio.to_thread(
                model.encode,
                texts,
                batch_size=self._batch_size,
                normalize_embeddings=self._normalize,
                show_progress_bar=False,
            )
            return [[float(value) for value in vector] for vector in vectors]
        except Exception as exc:
            raise ModelUnavailableError("sentence_transformers", type(exc).__name__) from exc

    async def embed_query(self, text: str) -> list[float]:
        """Embed one semantic search query."""

        vectors = await self.embed_documents([text])
        return vectors[0]


__all__ = ["EmbeddingModel", "SentenceTransformerEmbeddingModel"]
