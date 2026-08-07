from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Dict, Any, Optional

class SpeechToTextProvider(ABC):
    """Abstract interface for Speech-to-Text providers."""
    
    @abstractmethod
    async def transcribe_stream(
        self, 
        audio_generator: AsyncGenerator[bytes, None]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Ingest a stream of audio bytes and yield transcription segments.
        
        Yields:
            Dict containing:
                - "text": str (transcribed utterance)
                - "confidence": float
                - "is_final": bool
        """
        pass


class LLMProvider(ABC):
    """Abstract interface for Language Model providers."""

    @abstractmethod
    async def generate_response(
        self,
        prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        context_citations: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Generate a text response given a prompt, history, and optional RAG context.

        Returns:
            Dict containing:
                - "text": str (the generated response)
                - "citations": List[str] (list of cited source document chunks)
                - "confidence": float
        """
        pass


class TextToSpeechProvider(ABC):
    """Abstract interface for Text-to-Speech providers."""

    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        """
        Synthesize text into audio bytes (e.g. WAV or MP3 format).

        Returns:
            bytes containing the audio data.
        """
        pass
