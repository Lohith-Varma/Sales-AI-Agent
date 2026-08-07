from uuid import uuid4

import pytest
from ai.agents.speech.agent import SpeechToTextAgent
from ai.schemas.speech import TranscriptionOutput, TranscriptionRequest, TranscriptSegment


class FakeTranscriber:
    async def transcribe(self, request: TranscriptionRequest) -> TranscriptionOutput:
        return TranscriptionOutput(
            segments=(
                TranscriptSegment(text="Hello", start_seconds=0, end_seconds=0.1, language="en"),
            ),
            full_text="Hello",
            detected_language="en",
            audio_duration_seconds=request.duration_seconds,
            processing_duration_ms=1,
        )


@pytest.mark.asyncio
async def test_speech_agent_delegates_to_transcriber() -> None:
    request = TranscriptionRequest(session_id=uuid4(), audio_bytes=b"\x00\x00" * 1600)
    result = await SpeechToTextAgent(FakeTranscriber()).run(request)
    assert result.full_text == "Hello"
