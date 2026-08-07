from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from ai.config.settings import Settings


class FakeStructuredLLM:
    """Deterministic structured LLM fake returning queued Pydantic values."""

    def __init__(self, *outputs: Any) -> None:
        self.outputs = list(outputs)
        self.calls: list[dict[str, Any]] = []

    async def generate(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if not self.outputs:
            raise AssertionError("FakeStructuredLLM has no queued output")
        return self.outputs.pop(0)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        gemini_api_key="test-key",
        chroma_persist_directory=tmp_path / "chroma",
        knowledge_document_directory=tmp_path / "documents",
        app_env="test",
        log_format="console",
    )


@pytest.fixture
def fake_llm_factory() -> Iterator[type[FakeStructuredLLM]]:
    yield FakeStructuredLLM
