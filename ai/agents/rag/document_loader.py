"""Safe loaders for PDFs, FAQ JSON, Markdown, and plain-text knowledge files."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from ai.schemas.enums import DocumentType
from ai.schemas.rag import DocumentMetadata, KnowledgeDocument
from ai.utils.exceptions import DocumentIngestionError
from ai.utils.text import normalize_document_text, sha256_text


class KnowledgeDocumentLoader:
    """Load approved local files into normalized, provenance-rich documents."""

    def __init__(self, *, supported_extensions: tuple[str, ...], maximum_bytes: int) -> None:
        self._supported_extensions = frozenset(supported_extensions)
        self._maximum_bytes = maximum_bytes

    async def load(
        self,
        path: Path,
        *,
        title: str | None = None,
        version: str | None = None,
        tags: tuple[str, ...] = (),
        attributes: dict[str, str | int | float | bool] | None = None,
    ) -> list[KnowledgeDocument]:
        """Load one validated file without blocking the event loop."""

        resolved, size = await asyncio.to_thread(self._resolve_and_size, path)
        extension = resolved.suffix.lower()
        if extension not in self._supported_extensions:
            raise DocumentIngestionError(
                f"Unsupported extension: {extension}",
                public_message=f"Files of type {extension} are not supported.",
            )
        if size <= 0 or size > self._maximum_bytes:
            raise DocumentIngestionError(
                f"Document size {size} violates limit {self._maximum_bytes}",
                public_message="The document is empty or exceeds the upload limit.",
            )
        return await asyncio.to_thread(
            self._load_sync,
            resolved,
            title,
            version,
            tags,
            attributes or {},
        )

    @staticmethod
    def _resolve_and_size(path: Path) -> tuple[Path, int]:
        """Resolve and stat a path inside the worker thread."""

        resolved = path.resolve(strict=True)
        return resolved, resolved.stat().st_size

    def _load_sync(
        self,
        path: Path,
        title: str | None,
        version: str | None,
        tags: tuple[str, ...],
        attributes: dict[str, str | int | float | bool],
    ) -> list[KnowledgeDocument]:
        extension = path.suffix.lower()
        document_type = {
            ".pdf": DocumentType.PDF,
            ".json": DocumentType.FAQ,
            ".md": DocumentType.MARKDOWN,
            ".txt": DocumentType.TEXT,
        }[extension]
        metadata = DocumentMetadata(
            source=str(path),
            document_type=document_type,
            title=title or path.stem,
            version=version,
            tags=tags,
            attributes=attributes,
        )
        if extension == ".pdf":
            return self._load_pdf(path, metadata)
        if extension == ".json":
            return self._load_faq(path, metadata)
        text = normalize_document_text(path.read_text(encoding="utf-8"))
        return [self._make_document(path.stem, text, metadata)]

    def _load_pdf(self, path: Path, metadata: DocumentMetadata) -> list[KnowledgeDocument]:
        try:
            reader = PdfReader(str(path))
            if reader.is_encrypted:
                raise DocumentIngestionError("Encrypted PDFs are not supported")
            documents: list[KnowledgeDocument] = []
            for page_number, page in enumerate(reader.pages, start=1):
                text = normalize_document_text(page.extract_text() or "")
                if text:
                    documents.append(
                        self._make_document(
                            f"{path.stem}:page:{page_number}",
                            text,
                            metadata,
                            page_number=page_number,
                        )
                    )
            if not documents:
                raise DocumentIngestionError("PDF contains no extractable text")
            return documents
        except DocumentIngestionError:
            raise
        except Exception as exc:
            raise DocumentIngestionError(f"PDF parsing failed: {type(exc).__name__}") from exc

    def _load_faq(self, path: Path, metadata: DocumentMetadata) -> list[KnowledgeDocument]:
        try:
            value: Any = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DocumentIngestionError("FAQ file is not valid UTF-8 JSON") from exc
        entries = value.get("faqs") if isinstance(value, dict) and "faqs" in value else value
        if not isinstance(entries, list):
            raise DocumentIngestionError("FAQ JSON must be a list or contain a 'faqs' list")
        documents: list[KnowledgeDocument] = []
        for index, item in enumerate(entries):
            if not isinstance(item, dict):
                raise DocumentIngestionError(f"FAQ entry {index} must be an object")
            question = normalize_document_text(str(item.get("question", "")))
            answer = normalize_document_text(str(item.get("answer", "")))
            if not question or not answer:
                raise DocumentIngestionError(f"FAQ entry {index} requires question and answer")
            text = f"Question: {question}\nAnswer: {answer}"
            documents.append(self._make_document(f"{path.stem}:faq:{index}", text, metadata))
        if not documents:
            raise DocumentIngestionError("FAQ JSON contains no entries")
        return documents

    @staticmethod
    def _make_document(
        document_id: str,
        text: str,
        metadata: DocumentMetadata,
        *,
        page_number: int | None = None,
    ) -> KnowledgeDocument:
        if not text:
            raise DocumentIngestionError("Document contains no usable text")
        return KnowledgeDocument(
            document_id=document_id,
            content=text,
            content_sha256=sha256_text(text),
            metadata=metadata,
            page_number=page_number,
        )


__all__ = ["KnowledgeDocumentLoader"]
