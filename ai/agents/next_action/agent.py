"""Gemini-backed controlled next-best-action agent."""

from ai.models.llm import StructuredLLM
from ai.prompts.next_action import NEXT_ACTION_SYSTEM_PROMPT
from ai.schemas.analysis import NextActionRequest
from ai.schemas.orchestration import NextActionRecommendation
from ai.utils.json import dump_json


class NextBestActionAgent:
    name = "next_best_action"
    version = "1.0"

    def __init__(self, llm: StructuredLLM, *, temperature: float = 0.0) -> None:
        self._llm = llm
        self._temperature = temperature

    async def run(self, request: NextActionRequest) -> NextActionRecommendation:
        return await self._llm.generate(
            system_prompt=NEXT_ACTION_SYSTEM_PROMPT,
            user_prompt=dump_json(request.model_dump(mode="json")),
            output_type=NextActionRecommendation,
            temperature=self._temperature,
        )


__all__ = ["NextBestActionAgent"]
