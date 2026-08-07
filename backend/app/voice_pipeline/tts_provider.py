import io
import wave
import logging
from app.voice_pipeline.interfaces import TextToSpeechProvider

logger = logging.getLogger(__name__)

class MockTTSProvider(TextToSpeechProvider):
    """Generates valid, silent WAV audio chunks to mock Text-to-Speech response."""

    async def synthesize(self, text: str) -> bytes:
        logger.info(f"Mock TTS: Synthesizing response: '{text[:30]}...'")
        
        # Generate a small 0.5-second silent WAV file
        # Standard telephony format: 8000Hz, 16-bit, 1 channel (mono)
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)  # 2 bytes per sample (16-bit)
            wav.setframerate(8000)
            # Write 4000 silent frames (8000 bytes)
            wav.writeframes(b'\x00' * 8000)
            
        return wav_buffer.getvalue()
