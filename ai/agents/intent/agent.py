"""Gemini-backed customer-intent detection agent."""

from ai.models.llm import StructuredLLM
from ai.prompts.intent import INTENT_SYSTEM_PROMPT
from ai.schemas.analysis import IntentDetectionRequest
from ai.schemas.orchestration import IntentAnalysis
from ai.utils.json import dump_json


class IntentDetectionAgent:
    name = "intent_detection"
    version = "1.0"

    def __init__(self, llm: StructuredLLM, *, temperature: float = 0.0) -> None:
        self._llm = llm
        self._temperature = temperature

    async def run(self, request: IntentDetectionRequest) -> IntentAnalysis:
        payload = {
            "latest_customer_utterance": request.latest_customer_utterance,
            "conversation_context": request.conversation_context,
        }
        return await self._llm.generate(
            system_prompt=INTENT_SYSTEM_PROMPT,
            user_prompt=dump_json(payload),
            output_type=IntentAnalysis,
            temperature=self._temperature,
        )


__all__ = ["IntentDetectionAgent"]
