"""Gemini-backed customer entity extraction agent."""

from ai.models.llm import StructuredLLM
from ai.prompts.entity import ENTITY_SYSTEM_PROMPT
from ai.schemas.entities import EntityExtractionOutput, EntityExtractionRequest
from ai.utils.json import dump_json


class EntityExtractionAgent:
    name = "entity_extraction"
    version = "1.0"

    def __init__(self, llm: StructuredLLM, *, temperature: float = 0.0) -> None:
        self._llm = llm
        self._temperature = temperature

    async def run(self, request: EntityExtractionRequest) -> EntityExtractionOutput:
        return await self._llm.generate(
            system_prompt=ENTITY_SYSTEM_PROMPT,
            user_prompt=dump_json(request.model_dump(mode="json")),
            output_type=EntityExtractionOutput,
            temperature=self._temperature,
        )


__all__ = ["EntityExtractionAgent"]
