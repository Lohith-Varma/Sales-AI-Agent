"""Lazy OpenAI Whisper transcription adapter for PCM16 audio windows."""

from __future__ import annotations

import asyncio
import math
from typing import Any, Protocol, cast

import numpy as np
import whisper  # type: ignore[import-untyped]

from ai.schemas.speech import TranscriptionOutput, TranscriptionRequest, TranscriptSegment
from ai.utils.exceptions import TranscriptionError
from ai.utils.time import MonotonicTimer


class SpeechModel(Protocol):
    """Provider-neutral speech transcription interface."""

    async def transcribe(self, request: TranscriptionRequest) -> TranscriptionOutput: ...


class WhisperSpeechModel:
    """Transcribe short PCM16 windows with a lazily loaded Whisper model."""

    def __init__(self, *, model_name: str, device: str) -> None:
        self._model_name = model_name
        self._device = device
        self._model: Any | None = None
        self._load_lock = asyncio.Lock()
        self._inference_lock = asyncio.Lock()

    async def _get_model(self) -> Any:
        if self._model is None:
            async with self._load_lock:
                if self._model is None:
                    try:
                        self._model = await asyncio.to_thread(
                            whisper.load_model, self._model_name, device=self._device
                        )
                    except Exception as exc:
                        raise TranscriptionError(
                            f"Whisper model load failed: {type(exc).__name__}", retryable=False
                        ) from exc
        return self._model

    async def transcribe(self, request: TranscriptionRequest) -> TranscriptionOutput:
        """Convert little-endian signed PCM16 samples into transcript segments."""

        if request.audio_config.sample_rate_hz != 16_000:
            raise TranscriptionError("Whisper adapter requires 16 kHz PCM audio", retryable=False)
        if request.audio_config.channels != 1:
            raise TranscriptionError("Whisper adapter requires mono PCM audio", retryable=False)

        samples = np.frombuffer(request.audio_bytes, dtype="<i2").astype(np.float32) / 32768.0
        model = await self._get_model()
        timer = MonotonicTimer()
        try:
            async with self._inference_lock:
                raw = await asyncio.to_thread(
                    model.transcribe,
                    samples,
                    language=request.language,
                    initial_prompt=request.context_hint,
                    fp16=self._device.startswith("cuda"),
                    verbose=False,
                )
        except Exception as exc:
            raise TranscriptionError(f"Whisper inference failed: {type(exc).__name__}") from exc

        raw_segments = cast(list[dict[str, Any]], raw.get("segments", []))
        duration = request.duration_seconds
        segments: list[TranscriptSegment] = []
        for item in raw_segments:
            text = str(item.get("text", "")).strip()
            if not text:
                continue
            start = max(0.0, float(item.get("start", 0.0)))
            end = min(duration, max(start + 0.001, float(item.get("end", duration))))
            average_log_probability = float(item.get("avg_logprob", -1.0))
            confidence = min(1.0, max(0.0, math.exp(average_log_probability)))
            segments.append(
                TranscriptSegment(
                    text=text,
                    start_seconds=start,
                    end_seconds=end,
                    confidence=confidence,
                    language=str(raw.get("language") or request.language or "unknown"),
                )
            )

        full_text = str(raw.get("text", "")).strip()
        if not segments or not full_text:
            return TranscriptionOutput(
                segments=(),
                full_text="",
                detected_language=str(raw.get("language") or request.language or "unknown"),
                audio_duration_seconds=duration,
                processing_duration_ms=timer.elapsed_milliseconds,
            )
        return TranscriptionOutput(
            segments=tuple(segments),
            full_text=full_text,
            detected_language=str(raw.get("language") or request.language or "unknown"),
            audio_duration_seconds=duration,
            processing_duration_ms=timer.elapsed_milliseconds,
        )


__all__ = ["SpeechModel", "WhisperSpeechModel"]
