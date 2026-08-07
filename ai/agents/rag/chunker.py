"""Deterministic recursive chunking with source offsets and stable identifiers."""

from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter

from ai.schemas.rag import DocumentChunk, KnowledgeDocument
from ai.utils.text import sha256_text, stable_chunk_id


class DocumentChunker:
    """Split normalized documents while preserving overlap and provenance."""

    def __init__(self, *, chunk_size: int, chunk_overlap: int) -> None:
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        self._chunk_overlap = chunk_overlap
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
            length_function=len,
            keep_separator=True,
        )

    def split(self, documents: list[KnowledgeDocument]) -> list[DocumentChunk]:
        """Split documents in stable source order."""

        output: list[DocumentChunk] = []
        for document in documents:
            search_start = 0
            for chunk_index, text in enumerate(self._splitter.split_text(document.content)):
                cleaned = text.strip()
                if not cleaned:
                    continue
                start = document.content.find(
                    cleaned, max(0, search_start - self._chunk_overlap * 2)
                )
                if start < 0:
                    start = document.content.find(cleaned)
                if start < 0:
                    raise ValueError("chunk text could not be mapped to its source document")
                end = start + len(cleaned)
                output.append(
                    DocumentChunk(
                        chunk_id=stable_chunk_id(document.document_id, chunk_index, cleaned),
                        document_id=document.document_id,
                        text=cleaned,
                        content_sha256=sha256_text(cleaned),
                        chunk_index=chunk_index,
                        start_character=start,
                        end_character=end,
                        page_number=document.page_number,
                        metadata=document.metadata,
                    )
                )
                search_start = end
        return output


__all__ = ["DocumentChunker"]
