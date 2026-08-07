from pathlib import Path

import pytest
from ai.agents.rag.chunker import DocumentChunker
from ai.agents.rag.document_loader import KnowledgeDocumentLoader


@pytest.mark.asyncio
async def test_text_loading_and_chunking(tmp_path: Path) -> None:
    source = tmp_path / "product.txt"
    source.write_text("Pay-in-3 approved product information. " * 40, encoding="utf-8")
    loader = KnowledgeDocumentLoader(supported_extensions=(".txt",), maximum_bytes=100_000)
    documents = await loader.load(source)
    chunks = DocumentChunker(chunk_size=200, chunk_overlap=30).split(documents)
    assert documents[0].metadata.source == str(source.resolve())
    assert len(chunks) > 1
    assert len({chunk.chunk_id for chunk in chunks}) == len(chunks)
