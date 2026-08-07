"""Pydantic contracts for audio ingestion and speech transcription."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal, Self
from uuid import UUID, uuid4

from pydantic import Field, model_validator

from ai.schemas.common import Confidence, SchemaModel
from ai.schemas.enums import SpeakerRole


class AudioConfiguration(SchemaModel):
    """Audio format negotiated when a live WebSocket session starts."""

    encoding: Literal["pcm_s16le"] = "pcm_s16le"
    sample_rate_hz: Annotated[int, Field(ge=8_000, le=48_000)] = 16_000
    channels: Literal[1, 2] = 1
    sample_width_bytes: Literal[2] = 2

    @property
    def bytes_per_second(self) -> int:
        """Return the byte rate of this uncompressed PCM stream."""

        return self.sample_rate_hz * self.channels * self.sample_width_bytes


class AudioChunk(SchemaModel):
    """One ordered binary frame received from the live audio stream."""

    session_id: UUID
    sequence_number: Annotated[int, Field(ge=0)]
    audio_bytes: Annotated[bytes, Field(min_length=2, max_length=10_485_760)]
    received_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_complete_pcm_samples(self) -> Self:
        """Reject byte sequences that cannot contain complete 16-bit samples."""

        if len(self.audio_bytes) % 2 != 0:
            raise ValueError("PCM16 audio must contain an even number of bytes")
        return self


class TranscriptionRequest(SchemaModel):
    """A bounded audio window submitted to the Speech-to-Text agent."""

    session_id: UUID
    audio_bytes: Annotated[bytes, Field(min_length=2, max_length=20_000_000)]
    audio_config: AudioConfiguration = Field(default_factory=AudioConfiguration)
    language: Annotated[str, Field(min_length=2, max_length=16)] | None = "en"
    context_hint: Annotated[str, Field(max_length=1_000)] | None = None
    window_started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_audio_alignment(self) -> Self:
        """Require complete frames for the configured channel layout."""

        frame_width = self.audio_config.channels * self.audio_config.sample_width_bytes
        if len(self.audio_bytes) % frame_width != 0:
            raise ValueError("audio bytes are not aligned to the configured PCM frame width")
        return self

    @property
    def duration_seconds(self) -> float:
        """Return the exact duration represented by the PCM payload."""

        return len(self.audio_bytes) / self.audio_config.bytes_per_second


class TranscriptSegment(SchemaModel):
    """A timestamped utterance emitted by the transcription adapter."""

    segment_id: UUID = Field(default_factory=uuid4)
    speaker: SpeakerRole = SpeakerRole.UNKNOWN
    text: Annotated[str, Field(min_length=1, max_length=10_000)]
    start_seconds: Annotated[float, Field(ge=0)]
    end_seconds: Annotated[float, Field(gt=0)]
    confidence: Confidence | None = None
    language: Annotated[str, Field(min_length=2, max_length=16)]
    is_final: bool = True

    @model_validator(mode="after")
    def validate_timestamp_order(self) -> Self:
        """Ensure a segment ends after it begins."""

        if self.end_seconds <= self.start_seconds:
            raise ValueError("end_seconds must be greater than start_seconds")
        return self


class TranscriptionOutput(SchemaModel):
    """Validated Speech-to-Text output for one buffered audio window."""

    segments: Annotated[tuple[TranscriptSegment, ...], Field(min_length=1)]
    full_text: Annotated[str, Field(min_length=1, max_length=50_000)]
    detected_language: Annotated[str, Field(min_length=2, max_length=16)]
    audio_duration_seconds: Annotated[float, Field(gt=0)]
    processing_duration_ms: Annotated[float, Field(ge=0)]

    @model_validator(mode="after")
    def validate_segment_bounds(self) -> Self:
        """Ensure emitted timestamps do not extend beyond the audio window."""

        tolerance_seconds = 0.1
        if any(
            segment.end_seconds > self.audio_duration_seconds + tolerance_seconds
            for segment in self.segments
        ):
            raise ValueError("transcript segment extends beyond the supplied audio duration")
        return self


__all__ = [
    "AudioChunk",
    "AudioConfiguration",
    "TranscriptSegment",
    "TranscriptionOutput",
    "TranscriptionRequest",
]
