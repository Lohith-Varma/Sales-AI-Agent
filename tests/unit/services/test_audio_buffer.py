from uuid import uuid4

import pytest
from ai.schemas.speech import AudioChunk, AudioConfiguration
from ai.services.audio_buffer import AudioBuffer
from ai.utils.exceptions import InvalidAudioError


@pytest.mark.asyncio
async def test_buffer_preserves_order_and_drains() -> None:
    session_id = uuid4()
    buffer = AudioBuffer(configuration=AudioConfiguration(), maximum_bytes=100)
    await buffer.append(
        AudioChunk(session_id=session_id, sequence_number=0, audio_bytes=b"\x00\x00")
    )
    assert await buffer.drain() == b"\x00\x00"
    assert buffer.size_bytes == 0


@pytest.mark.asyncio
async def test_buffer_rejects_out_of_order_frames() -> None:
    buffer = AudioBuffer(configuration=AudioConfiguration(), maximum_bytes=100)
    with pytest.raises(InvalidAudioError):
        await buffer.append(
            AudioChunk(session_id=uuid4(), sequence_number=1, audio_bytes=b"\x00\x00")
        )
