import asyncio
from typing import AsyncGenerator, Dict, Any, List, Optional
from app.voice_pipeline.interfaces import SpeechToTextProvider

class MockSTTProvider(SpeechToTextProvider):
    """Simulates real-time transcription by yielding pre-configured customer utterances."""
    
    def __init__(self, utterances: Optional[List[str]] = None):
        # Default scenario for testing our fintech affordability product
        self.utterances = utterances or [
            "Hi, is it true that you offer pay-in-3 zero-cost EMI?",
            "What documents do I need to submit for KYC verification?",
            "What happens if I miss an EMI payment? Is there a late fee?",
            "Okay, sounds good. Can we start the application process?"
        ]
        
    async def transcribe_stream(
        self, 
        audio_generator: AsyncGenerator[bytes, None]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Consumes the audio generator, and for every few chunks, yields a simulated transcription.
        """
        utterance_idx = 0
        chunk_counter = 0
        
        async for chunk in audio_generator:
            # We simulate that every 10 audio chunks represents a complete utterance spoken by the customer
            chunk_counter += 1
            if chunk_counter >= 10:
                if utterance_idx < len(self.utterances):
                    yield {
                        "text": self.utterances[utterance_idx],
                        "confidence": 0.95,
                        "is_final": True
                    }
                    utterance_idx += 1
                chunk_counter = 0
                
            # Keep the streaming behavior non-blocking
            await asyncio.sleep(0.01)
            
        # Yield any remaining utterances if the audio generator completes
        if utterance_idx < len(self.utterances):
            for i in range(utterance_idx, len(self.utterances)):
                yield {
                    "text": self.utterances[i],
                    "confidence": 0.95,
                    "is_final": True
                }
