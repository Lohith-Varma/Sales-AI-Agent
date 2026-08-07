"""Google Gemini structured-output adapter."""

from __future__ import annotations

import asyncio
from typing import Protocol, TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

from ai.utils.exceptions import ModelUnavailableError
from ai.utils.json import StructuredJSONError, validate_json_model

StructuredOutputT = TypeVar("StructuredOutputT", bound=BaseModel)


class StructuredLLM(Protocol):
    """Provider-neutral interface for validated structured generation."""

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_type: type[StructuredOutputT],
        temperature: float,
    ) -> StructuredOutputT: ...


class GeminiStructuredLLM:
    """Generate schema-constrained JSON with the Google GenAI SDK."""

    def __init__(
        self,
        *,
        api_key: str,
        model_name: str,
        timeout_seconds: float,
        max_retries: int,
    ) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model_name = model_name
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_type: type[StructuredOutputT],
        temperature: float,
    ) -> StructuredOutputT:
        """Generate and validate one Pydantic object, retrying transient failures."""

        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                async with asyncio.timeout(self._timeout_seconds):
                    response = await self._client.aio.models.generate_content(
                        model=self._model_name,
                        contents=user_prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=system_prompt,
                            temperature=temperature,
                            response_mime_type="application/json",
                            response_schema=output_type,
                        ),
                    )
                if not response.text:
                    raise StructuredJSONError("Gemini returned an empty response")
                return validate_json_model(response.text, output_type)
            except Exception as exc:
                last_error = exc
                if attempt < self._max_retries:
                    await asyncio.sleep(min(0.25 * (2**attempt), 1.0))

        raise ModelUnavailableError(
            "gemini",
            type(last_error).__name__ if last_error is not None else "unknown error",
        ) from last_error


__all__ = ["GeminiStructuredLLM", "StructuredLLM"]
