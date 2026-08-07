"""Isolated Speech-to-Text agent."""

from ai.agents.speech.transcriber import Transcriber
from ai.schemas.speech import TranscriptionOutput, TranscriptionRequest


class SpeechToTextAgent:
    name = "speech_to_text"
    version = "1.0"

    def __init__(self, transcriber: Transcriber) -> None:
        self._transcriber = transcriber

    async def run(self, request: TranscriptionRequest) -> TranscriptionOutput:
        """Transcribe one validated, bounded audio window."""

        return await self._transcriber.transcribe(request)


__all__ = ["SpeechToTextAgent"]
