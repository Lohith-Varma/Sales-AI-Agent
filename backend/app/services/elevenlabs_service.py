"""ElevenLabs service abstraction for Text-to-Speech and Speech-to-Text."""

from __future__ import annotations

import base64
import logging
from typing import AsyncGenerator, Optional
import httpx

logger = logging.getLogger(__name__)


class ElevenLabsService:
    """Service abstraction for ElevenLabs TTS and STT APIs."""

    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_voice_id: str = "21m00Tcm4TlvDq8ikWAM",
        default_model_id: str = "eleven_flash_v2_5",
        timeout_seconds: float = 15.0,
    ) -> None:
        self.api_key = api_key.strip() if api_key and api_key.strip() else None
        self.default_voice_id = default_voice_id
        self.default_model_id = default_model_id
        self.timeout_seconds = timeout_seconds

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key != "replace-with-your-provider-key")

    def _headers(self) -> dict[str, str]:
        if not self.is_configured():
            raise ValueError("ElevenLabs API key is missing or not configured.")
        return {
            "xi-api-key": self.api_key,
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
            logger.warning("ElevenLabs TTS skipped: API key is not configured.")
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

        logger.info("ElevenLabs TTS started for text snippet")
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            try:
                response = await client.post(url, headers=self._headers(), json=payload)
                response.raise_for_status()
                audio_bytes = response.content
                logger.info(f"ElevenLabs TTS completed: {len(audio_bytes)} bytes generated")
                return audio_bytes
            except httpx.HTTPStatusError as exc:
                logger.error(f"ElevenLabs API error: HTTP {exc.response.status_code} - {exc.response.text}")
                raise RuntimeError(f"ElevenLabs API error: HTTP {exc.response.status_code}") from exc
            except Exception as exc:
                logger.error(f"ElevenLabs TTS failed: {exc}")
                raise RuntimeError(f"ElevenLabs TTS request failed: {exc}") from exc

    async def stream_speech(
        self,
        text: str,
        voice_id: Optional[str] = None,
        model_id: Optional[str] = None,
        chunk_size: int = 4096,
    ) -> AsyncGenerator[bytes, None]:
        """Stream speech audio bytes from ElevenLabs TTS API."""
        if not text or not text.strip():
            return
        if not self.is_configured():
            logger.warning("ElevenLabs streaming TTS skipped: API key is not configured.")
            return

        target_voice = voice_id or self.default_voice_id
        target_model = model_id or self.default_model_id

        url = f"{self.BASE_URL}/text-to-speech/{target_voice}/stream"
        payload = {
            "text": text,
            "model_id": target_model,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            },
        }

        logger.info("ElevenLabs TTS streaming started")
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            try:
                async with client.stream("POST", url, headers=self._headers(), json=payload) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_bytes(chunk_size=chunk_size):
                        if chunk:
                            yield chunk
                logger.info("ElevenLabs TTS streaming completed")
            except Exception as exc:
                logger.error(f"ElevenLabs streaming TTS failed: {exc}")
                raise RuntimeError(f"ElevenLabs streaming TTS failed: {exc}") from exc

    async def generate_speech_base64(
        self,
        text: str,
        voice_id: Optional[str] = None,
        model_id: Optional[str] = None,
    ) -> str:
        """Helper to get base64 encoded audio string for WebSocket delivery."""
        raw_bytes = await self.generate_speech(text, voice_id=voice_id, model_id=model_id)
        if not raw_bytes:
            return ""
        return base64.b64encode(raw_bytes).decode("utf-8")

    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        language: str = "en",
    ) -> str:
        """Transcribe audio bytes using ElevenLabs STT API if supported/configured."""
        if not audio_bytes or not self.is_configured():
            return ""

        url = f"{self.BASE_URL}/speech-to-text"
        headers = {
            "xi-api-key": self.api_key,
        }
        files = {
            "file": ("audio.wav", audio_bytes, "audio/wav"),
        }
        data = {
            "model_id": "scribe_v1",
            "language_code": language,
        }

        logger.info("ElevenLabs STT started")
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            try:
                response = await client.post(url, headers=headers, files=files, data=data)
                if response.status_code == 200:
                    result = response.json()
                    transcript = result.get("text", "")
                    logger.info("Transcript received via ElevenLabs STT")
                    return transcript
                else:
                    logger.warning(f"ElevenLabs STT HTTP {response.status_code}: {response.text}")
                    return ""
            except Exception as exc:
                logger.warning(f"ElevenLabs STT request skipped/failed: {exc}")
                return ""
