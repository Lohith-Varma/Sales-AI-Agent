"""ElevenLabs service abstraction for the AI service runtime."""

from __future__ import annotations

import base64
from typing import AsyncGenerator, Optional
import httpx
from pydantic import SecretStr

from ai.config.logging import get_logger

_logger = get_logger("services.elevenlabs")


class ElevenLabsService:
    """Service abstraction for ElevenLabs TTS and STT APIs in AI container."""

    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(
        self,
        api_key: Optional[SecretStr] = None,
        default_voice_id: str = "21m00Tcm4TlvDq8ikWAM",
        default_model_id: str = "eleven_flash_v2_5",
        timeout_seconds: float = 15.0,
    ) -> None:
        self.api_key_secret = api_key
        self.default_voice_id = default_voice_id
        self.default_model_id = default_model_id
        self.timeout_seconds = timeout_seconds

    @property
    def api_key(self) -> Optional[str]:
        if not self.api_key_secret:
            return None
        raw = self.api_key_secret.get_secret_value().strip()
        if not raw or raw == "replace-with-your-provider-key":
            return None
        return raw

    def is_configured(self) -> bool:
        return self.api_key is not None

    def _headers(self) -> dict[str, str]:
        key = self.api_key
        if not key:
            raise ValueError("ElevenLabs API key is missing or not configured.")
        return {
            "xi-api-key": key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }

    async def generate_speech(
        self,
        text: str,
        voice_id: Optional[str] = None,
        model_id: Optional[str] = None,
    ) -> bytes:
        """Convert text to speech audio bytes (MP3 format)."""
        if not text or not text.strip():
            return b""
        if not self.is_configured():
            _logger.info("elevenlabs_tts_skipped", reason="unconfigured")
            return b""

        target_voice = voice_id or self.default_voice_id
        target_model = model_id or self.default_model_id

        url = f"{self.BASE_URL}/text-to-speech/{target_voice}"
        payload = {
            "text": text,
            "model_id": target_model,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            },
        }

        _logger.info("elevenlabs_tts_started", text_length=len(text), voice_id=target_voice)
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            try:
                response = await client.post(url, headers=self._headers(), json=payload)
                response.raise_for_status()
                audio_bytes = response.content
                _logger.info("elevenlabs_tts_completed", bytes_count=len(audio_bytes))
                return audio_bytes
            except httpx.HTTPStatusError as exc:
                _logger.error(
                    "elevenlabs_api_error",
                    status_code=exc.response.status_code,
                    detail=exc.response.text,
                )
                raise RuntimeError(f"ElevenLabs API error: HTTP {exc.response.status_code}") from exc
            except Exception as exc:
                _logger.error("elevenlabs_tts_failed", exception=type(exc).__name__, error=str(exc))
                raise RuntimeError(f"ElevenLabs TTS request failed: {exc}") from exc

    async def generate_speech_base64(
        self,
        text: str,
        voice_id: Optional[str] = None,
        model_id: Optional[str] = None,
    ) -> str:
        """Get base64 encoded string for streaming over WebSocket."""
        audio_bytes = await self.generate_speech(text, voice_id=voice_id, model_id=model_id)
        if not audio_bytes:
            return ""
        return base64.b64encode(audio_bytes).decode("utf-8")

    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        language: str = "en",
    ) -> str:
        """Transcribe audio bytes using ElevenLabs STT API if configured."""
        key = self.api_key
        if not audio_bytes or not key:
            return ""

        url = f"{self.BASE_URL}/speech-to-text"
        headers = {"xi-api-key": key}
        files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
        data = {"model_id": "scribe_v1", "language_code": language}

        _logger.info("elevenlabs_stt_started", audio_bytes=len(audio_bytes))
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            try:
                response = await client.post(url, headers=headers, files=files, data=data)
                if response.status_code == 200:
                    result = response.json()
                    transcript = result.get("text", "")
                    _logger.info("elevenlabs_stt_completed", transcript_length=len(transcript))
                    return transcript
                else:
                    _logger.warning("elevenlabs_stt_status_error", status_code=response.status_code)
                    return ""
            except Exception as exc:
                _logger.warning("elevenlabs_stt_failed", exception=type(exc).__name__)
                return ""


__all__ = ["ElevenLabsService"]
