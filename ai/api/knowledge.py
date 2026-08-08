"""Approved knowledge-document ingestion endpoint."""

from __future__ import annotations

import tempfile
import hashlib
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile

from ai.api.dependencies import get_container
from ai.config.container import ApplicationContainer
from ai.schemas.responses_api import DocumentIngestionResponse
from ai.utils.exceptions import DocumentIngestionError, MessageTooLargeError

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("/ingest", response_model=DocumentIngestionResponse)
async def ingest_document(
    container: Annotated[ApplicationContainer, Depends(get_container)],
    file: Annotated[UploadFile, File(...)],
    title: Annotated[str | None, Form()] = None,
    version: Annotated[str | None, Form()] = None,
) -> DocumentIngestionResponse:
    """Persist an upload temporarily, validate it, and index approved text."""

    suffix = Path(file.filename or "upload").suffix.lower()
    if suffix not in container.settings.supported_document_extensions:
        raise DocumentIngestionError(f"Unsupported upload extension: {suffix}")
    payload = await file.read(container.settings.max_document_upload_bytes + 1)
    if len(payload) > container.settings.max_document_upload_bytes:
        raise MessageTooLargeError(len(payload), container.settings.max_document_upload_bytes)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
            handle.write(payload)
            temporary_path = Path(handle.name)
        result = await container.document_service.ingest_paths(
            [temporary_path], title=title, version=version
        )
        await container.core_persistence.register_knowledge_document(
            title=title or Path(file.filename or "upload").stem,
            source=file.filename or "upload",
            version=version,
            chunk_count=result.chunk_count,
            content_sha256=hashlib.sha256(payload).hexdigest(),
        )
        return DocumentIngestionResponse(result=result)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        await file.close()


__all__ = ["router"]
