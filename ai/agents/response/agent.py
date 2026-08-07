"""Generate representative suggestions using only retrieved product context."""

from ai.models.llm import StructuredLLM
from ai.prompts.response import RESPONSE_SYSTEM_PROMPT
from ai.schemas.responses import (
    ResponseGenerationOutput,
    ResponseGenerationRequest,
    SuggestedResponse,
)
from ai.utils.json import dump_json


class ResponseGenerationAgent:
    name = "response_generation"
    version = "1.0"

    def __init__(
        self,
        llm: StructuredLLM,
        *,
        safe_fallback: str,
        temperature: float = 0.2,
    ) -> None:
        self._llm = llm
        self._safe_fallback = safe_fallback
        self._temperature = temperature

    async def run(self, request: ResponseGenerationRequest) -> ResponseGenerationOutput:
        if not request.retrieval.sufficient_context:
            return ResponseGenerationOutput(
                suggestion=SuggestedResponse(
                    text=self._safe_fallback,
                    is_fallback=True,
                    requires_human_review=True,
                    confidence=1.0,
                ),
                source_chunk_count=0,
            )
        payload = request.model_dump(mode="json")
        payload["safe_fallback"] = self._safe_fallback
        suggestion = await self._llm.generate(
            system_prompt=RESPONSE_SYSTEM_PROMPT,
            user_prompt=dump_json(payload),
            output_type=SuggestedResponse,
            temperature=self._temperature,
        )
        return ResponseGenerationOutput(
            suggestion=suggestion,
            source_chunk_count=len(request.retrieval.chunks),
        )


__all__ = ["ResponseGenerationAgent"]
