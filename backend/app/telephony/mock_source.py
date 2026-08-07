import asyncio
from typing import AsyncGenerator

async def mock_audio_stream(num_chunks: int = 50) -> AsyncGenerator[bytes, None]:
    """
    Generates a sequence of mock audio chunks.
    This simulates audio streaming from Twilio or a local microphone.
    """
    for _ in range(num_chunks):
        # 320 bytes of silent PCM data (equivalent to 20ms of 8000Hz 16-bit audio)
        yield b'\x00' * 320
        # Wait a short duration to simulate real-time streaming cadence
        await asyncio.sleep(0.02)
