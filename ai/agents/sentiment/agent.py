"""Gemini-backed customer-sentiment agent."""

from ai.models.llm import StructuredLLM
from ai.prompts.sentiment import SENTIMENT_SYSTEM_PROMPT
from ai.schemas.analysis import SentimentDetectionRequest
from ai.schemas.orchestration import SentimentAnalysis
from ai.utils.json import dump_json


class SentimentAgent:
    name = "sentiment"
    version = "1.0"

    def __init__(self, llm: StructuredLLM, *, temperature: float = 0.0) -> None:
        self._llm = llm
        self._temperature = temperature

    async def run(self, request: SentimentDetectionRequest) -> SentimentAnalysis:
        return await self._llm.generate(
            system_prompt=SENTIMENT_SYSTEM_PROMPT,
            user_prompt=dump_json(request.model_dump(mode="json")),
            output_type=SentimentAnalysis,
            temperature=self._temperature,
        )


__all__ = ["SentimentAgent"]
