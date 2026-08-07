"""Index all supported product documents from a local directory."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from ai.config.container import build_container
from ai.config.logging import configure_logging, get_logger
from ai.config.settings import get_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=None, help="Knowledge directory")
    return parser.parse_args()


async def ingest(source: Path | None) -> None:
    settings = get_settings()
    configure_logging(settings)
    container = build_container(settings)
    directory = (source or settings.knowledge_document_directory).resolve(strict=True)
    if not directory.is_dir():
        raise ValueError(f"Knowledge source is not a directory: {directory}")
    paths = sorted(
        path
        for path in directory.rglob("*")
        if path.is_file() and path.suffix.lower() in settings.supported_document_extensions
    )
    if not paths:
        raise ValueError(f"No supported documents found in {directory}")
    result = await container.document_service.ingest_paths(paths)
    get_logger("ingestion").info(
        "knowledge_ingested",
        document_count=result.document_count,
        chunk_count=result.chunk_count,
        collection=result.collection_name,
    )


def main() -> None:
    args = parse_args()
    asyncio.run(ingest(args.source))


if __name__ == "__main__":
    main()
