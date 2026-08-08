"""Application service coordinating knowledge loading, chunking, and indexing."""

from pathlib import Path

from ai.agents.rag.chunker import DocumentChunker
from ai.agents.rag.document_loader import KnowledgeDocumentLoader
from ai.agents.rag.indexer import KnowledgeIndexer
from ai.schemas.rag import IngestionResult
from ai.schemas.rag import DocumentMetadata, KnowledgeDocument
from ai.schemas.enums import DocumentType
from ai.utils.text import sha256_text


class DocumentService:
    def __init__(
        self,
        *,
        loader: KnowledgeDocumentLoader,
        chunker: DocumentChunker,
        indexer: KnowledgeIndexer,
        collection_name: str,
    ) -> None:
        self._loader = loader
        self._chunker = chunker
        self._indexer = indexer
        self._collection_name = collection_name

    async def ingest_paths(
        self,
        paths: list[Path],
        *,
        title: str | None = None,
        version: str | None = None,
        tags: tuple[str, ...] = (),
        attributes: dict[str, str | int | float | bool] | None = None,
    ) -> IngestionResult:
        """Ingest an explicit list of approved paths into the configured collection."""

        documents = []
        for path in paths:
            documents.extend(
                await self._loader.load(
                    path,
                    title=title,
                    version=version,
                    tags=tags,
                    attributes=attributes,
                )
            )
        chunks = self._chunker.split(documents)
        indexed = await self._indexer.index(chunks)
        return IngestionResult(
            source=", ".join(str(path) for path in paths),
            document_count=len(documents),
            chunk_count=indexed,
            collection_name=self._collection_name,
        )

    async def ingest_product_records(self, records: list[dict[str, object]]) -> IngestionResult:
        documents: list[KnowledgeDocument] = []
        for record in records:
            identifier = str(record.get("id") or "")
            name = str(record.get("name") or "").strip()
            terms = str(record.get("terms") or "").strip()
            if not identifier or not name or not terms:
                continue
            content = f"Product: {name}\nCategory: {record.get('type') or 'product'}\nApproved terms: {terms}"
            documents.append(
                KnowledgeDocument(
                    document_id=f"core-product:{identifier}",
                    content=content,
                    content_sha256=sha256_text(content),
                    metadata=DocumentMetadata(
                        source=f"core://products/{identifier}",
                        document_type=DocumentType.TEXT,
                        title=name,
                        version=str(record.get("updated_at") or "database-current"),
                        tags=(str(record.get("type") or "product"),),
                    ),
                )
            )
        chunks = self._chunker.split(documents)
        indexed = await self._indexer.index(chunks)
        return IngestionResult(
            source="core://approved-products",
            document_count=len(documents),
            chunk_count=indexed,
            collection_name=self._collection_name,
        )


__all__ = ["DocumentService"]
