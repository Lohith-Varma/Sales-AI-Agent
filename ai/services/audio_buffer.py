"""Concurrency-safe, bounded PCM audio buffering for one live session."""

from __future__ import annotations

import asyncio

from ai.schemas.speech import AudioChunk, AudioConfiguration
from ai.utils.exceptions import InvalidAudioError, MessageTooLargeError


class AudioBuffer:
    """Accumulate ordered PCM frames until an utterance is ready to transcribe."""

    def __init__(self, *, configuration: AudioConfiguration, maximum_bytes: int) -> None:
        if maximum_bytes <= 0:
            raise ValueError("maximum_bytes must be positive")
        self._configuration = configuration
        self._maximum_bytes = maximum_bytes
        self._chunks: list[bytes] = []
        self._size = 0
        self._last_sequence = -1
        self._lock = asyncio.Lock()

    @property
    def configuration(self) -> AudioConfiguration:
        return self._configuration

    @property
    def size_bytes(self) -> int:
        return self._size

    @property
    def duration_seconds(self) -> float:
        return self._size / self._configuration.bytes_per_second

    async def append(self, chunk: AudioChunk) -> None:
        """Append exactly the next frame and enforce the memory ceiling."""

        async with self._lock:
            expected = self._last_sequence + 1
            if chunk.sequence_number != expected:
                raise InvalidAudioError(
                    f"Out-of-order audio frame: expected {expected}, got {chunk.sequence_number}",
                    public_message="Audio frames arrived out of order.",
                )
            new_size = self._size + len(chunk.audio_bytes)
            if new_size > self._maximum_bytes:
                raise MessageTooLargeError(new_size, self._maximum_bytes)
            self._chunks.append(chunk.audio_bytes)
            self._size = new_size
            self._last_sequence = chunk.sequence_number

    async def drain(self) -> bytes:
        """Atomically return all buffered bytes and reset only the byte payload."""

        async with self._lock:
            payload = b"".join(self._chunks)
            self._chunks.clear()
            self._size = 0
            return payload

    async def clear(self) -> None:
        """Discard buffered audio while retaining sequence continuity."""

        async with self._lock:
            self._chunks.clear()
            self._size = 0


__all__ = ["AudioBuffer"]
