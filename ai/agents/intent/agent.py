"""Gemini-backed customer-intent detection agent."""

import re

from ai.models.llm import StructuredLLM
from ai.prompts.intent import INTENT_SYSTEM_PROMPT
from ai.schemas.analysis import IntentDetectionRequest
from ai.schemas.common import TextEvidence
from ai.schemas.enums import IntentType
from ai.schemas.orchestration import IntentAnalysis
from ai.utils.json import dump_json

_FOLLOW_UP_PATTERN = re.compile(
    r"\b(think about it|get back to you|call me later|follow[ -]?up|not ready yet|need (?:some )?time)\b",
    re.IGNORECASE,
)


class IntentDetectionAgent:
    name = "intent_detection"
    version = "1.0"

    def __init__(self, llm: StructuredLLM, *, temperature: float = 0.0) -> None:
        self._llm = llm
        self._temperature = temperature

    async def run(self, request: IntentDetectionRequest) -> IntentAnalysis:
        # Common deferrals have a deterministic business meaning and do not
        # warrant a paid model call. This also keeps follow-up behavior stable
        # when the customer's wording is brief or sentiment is ambiguous.
        match = _FOLLOW_UP_PATTERN.search(request.latest_customer_utterance)
        if match:
            return IntentAnalysis(
                intent=IntentType.FOLLOW_UP,
                confidence=0.98,
                evidence=TextEvidence(
                    text=match.group(0),
                    start_character=match.start(),
                    end_character=match.end(),
                ),
            )
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
