"""Transcription boundary used by the Speech-to-Text agent."""

from typing import Protocol

from ai.models.whisper import SpeechModel
from ai.schemas.speech import TranscriptionOutput, TranscriptionRequest


class Transcriber(Protocol):
    async def transcribe(self, request: TranscriptionRequest) -> TranscriptionOutput: ...


class ModelTranscriber:
    """Thin adapter that keeps the agent independent of Whisper implementation details."""

    def __init__(self, model: SpeechModel) -> None:
        self._model = model

    async def transcribe(self, request: TranscriptionRequest) -> TranscriptionOutput:
        return await self._model.transcribe(request)


__all__ = ["ModelTranscriber", "Transcriber"]
