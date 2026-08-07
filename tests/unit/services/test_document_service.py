from pathlib import Path

import pytest
from ai.schemas.enums import DocumentType
from ai.schemas.rag import DocumentMetadata, KnowledgeDocument
from ai.services.document_service import DocumentService
from ai.utils.text import sha256_text


class FakeLoader:
    async def load(self, path: Path, **kwargs: object) -> list[KnowledgeDocument]:
        text = "Approved product information"
        return [
            KnowledgeDocument(
                document_id="d1",
                content=text,
                content_sha256=sha256_text(text),
                metadata=DocumentMetadata(
                    source=str(path), document_type=DocumentType.TEXT, title="Product"
                ),
            )
        ]


class FakeChunker:
    def split(self, documents: list[KnowledgeDocument]) -> list[object]:
        return [object()]


class FakeIndexer:
    async def index(self, chunks: list[object]) -> int:
        return len(chunks)


@pytest.mark.asyncio
async def test_document_service_reports_counts(tmp_path: Path) -> None:
    service = DocumentService(
        loader=FakeLoader(), chunker=FakeChunker(), indexer=FakeIndexer(), collection_name="test"
    )  # type: ignore[arg-type]
    result = await service.ingest_paths([tmp_path / "product.txt"])
    assert result.document_count == 1
    assert result.chunk_count == 1
