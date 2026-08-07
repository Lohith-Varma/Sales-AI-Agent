import logging
from typing import AsyncGenerator, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.voice_pipeline.interfaces import SpeechToTextProvider, LLMProvider, TextToSpeechProvider
from app.db.base import Transcript, ConsentLog, Call

logger = logging.getLogger(__name__)

class VoicePipeline:
    def __init__(
        self,
        stt_provider: SpeechToTextProvider,
        llm_provider: LLMProvider,
        tts_provider: TextToSpeechProvider
    ):
        self.stt_provider = stt_provider
        self.llm_provider = llm_provider
        self.tts_provider = tts_provider

    async def run_pipeline(
        self,
        call_id: str,
        audio_stream: AsyncGenerator[bytes, None],
        db: Session
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Runs the streaming voice pipeline:
        1. Check DPDP compliance (Consent Log).
        2. Stream audio -> Transcribe -> Query LLM -> Synthesize response.
        3. Save transcripts to database.
        
        Yields:
            Dict containing:
                - "type": str ("transcript", "response", "audio")
                - "text": str (content)
                - "citations": List[str] (citations if response)
                - "audio": bytes (audio bytes if audio)
                - "escalate": bool (if LLM flagged for escalation)
        """
        # --- DPDP Guardrail: Check Consent ---
        # Look up the latest consent log for this call
        consent = db.query(ConsentLog).filter(
            ConsentLog.call_id == call_id,
            ConsentLog.consent_given == True
        ).first()
        
        if not consent:
            logger.error(f"DPDP Violation: Attempted to process call {call_id} without customer consent.")
            raise PermissionError("Customer consent must be logged before voice processing can begin.")
        
        logger.info(f"Consent verified for call {call_id}. Initiating streaming voice pipeline.")
        
        # Start transcription stream
        transcript_generator = self.stt_provider.transcribe_stream(audio_stream)
        
        async for segment in transcript_generator:
            if not segment.get("is_final"):
                continue
                
            customer_text = segment["text"]
            logger.info(f"STT Output (Customer): {customer_text}")
            
            # 1. Save customer transcript to DB
            customer_transcript = Transcript(
                call_id=call_id,
                speaker="customer",
                text=customer_text,
                confidence=segment.get("confidence", 1.0)
            )
            db.add(customer_transcript)
            db.commit()
            
            yield {
                "type": "transcript",
                "text": customer_text,
                "confidence": segment.get("confidence")
            }
            
            # 2. Query LLM for response (FAQ matching / RAG emulator)
            llm_result = await self.llm_provider.generate_response(customer_text)
            ai_text = llm_result["text"]
            citations = llm_result.get("citations", [])
            escalate = llm_result.get("escalate", False)
            
            logger.info(f"LLM Output (AI): {ai_text}")
            
            # 3. Save AI transcript to DB
            ai_transcript = Transcript(
                call_id=call_id,
                speaker="ai",
                text=ai_text,
                confidence=llm_result.get("confidence", 1.0)
            )
            db.add(ai_transcript)
            db.commit()
            
            yield {
                "type": "response",
                "text": ai_text,
                "citations": citations,
                "escalate": escalate
            }
            
            # 4. Synthesize response text into audio bytes
            audio_bytes = await self.tts_provider.synthesize(ai_text)
            
            yield {
                "type": "audio",
                "text": ai_text,
                "audio": audio_bytes
            }
