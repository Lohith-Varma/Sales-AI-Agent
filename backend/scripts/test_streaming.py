import asyncio
import os
import sys

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.database import SessionLocal, Base, engine
from app.db.base import Customer, Call, ConsentLog, Transcript
from app.compliance.encryption import decrypt
from app.telephony.mock_source import mock_audio_stream
from app.voice_pipeline.pipeline import VoicePipeline
from app.voice_pipeline.stt_provider import MockSTTProvider
from app.voice_pipeline.llm_provider import MockLLMProvider
from app.voice_pipeline.tts_provider import MockTTSProvider

async def main():
    print("=" * 60)
    print("AI VOICE CO-PILOT - PHASE 0 & 1 STREAMING VERIFICATION")
    print("=" * 60)
    
    # 1. Setup local database session
    db = SessionLocal()
    
    # Seed data
    phone = "+919555555555"
    print(f"[1/5] Checking if customer with phone {phone} exists...")
    customer = db.query(Customer).filter(Customer.phone_number == phone).first()
    if not customer:
        customer = Customer(
            name="Varma Lohith",
            phone_number=phone,
            email="varma.lohith@example.com",
            pii_data_encrypted="75000.00"  # salary
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        print(f"Created customer: {customer.name} (ID: {customer.id})")
    else:
        print(f"Found customer: {customer.name} (ID: {customer.id})")
        
    # Create call session
    call = Call(customer_id=customer.id, status="initiated", direction="inbound")
    db.add(call)
    db.commit()
    db.refresh(call)
    print(f"[2/5] Initiated call session. Call ID: {call.id}")
    
    # Check compliance guardrail: Attempting to run voice pipeline without consent
    print("[3/5] Testing consent guardrail (expecting block)...")
    pipeline = VoicePipeline(
        stt_provider=MockSTTProvider(),
        llm_provider=MockLLMProvider(),
        tts_provider=MockTTSProvider()
    )
    
    try:
        audio_stream = mock_audio_stream(num_chunks=5)
        async for event in pipeline.run_pipeline(call.id, audio_stream, db):
            pass
    except PermissionError as e:
        print(f"[OK] Consent guardrail active! Blocked voice pipeline: '{e}'")
    except Exception as ex:
        print(f"[FAIL] Unexpected error testing consent block: {ex}")
        
    # Log consent
    print("[4/5] Logging customer consent in database...")
    consent = ConsentLog(
        call_id=call.id,
        customer_id=customer.id,
        consent_given=True,
        ip_address="127.0.0.1"
    )
    db.add(consent)
    call.status = "active"
    db.commit()
    print("[OK] Consent logged successfully. Call status set to active.")
    
    # Run streaming pipeline
    print("[5/5] Starting live audio stream simulation...")
    print("-" * 60)
    
    # We stream 45 chunks, which will trigger all mock utterances
    audio_stream = mock_audio_stream(num_chunks=45)
    
    try:
        async for event in pipeline.run_pipeline(call.id, audio_stream, db):
            event_type = event["type"]
            if event_type == "transcript":
                print(f"\n[STT] Customer: {event['text']} (Confidence: {event['confidence']})")
            elif event_type == "response":
                print(f"[LLM] Suggested Response: {event['text']}")
                print(f"[LLM] Citations: {event['citations']}")
                if event.get("escalate"):
                    print("[LLM] ⚠ ALERT: Escalate to human specialist requested.")
            elif event_type == "audio":
                print(f"[TTS] Generated synthesized audio: {len(event['audio'])} bytes of WAV format.")
    except Exception as e:
        print(f"[FAIL] Error during voice pipeline execution: {e}")
        
    print("-" * 60)
    
    # Post-call transcript check
    print("\n--- POST-CALL VERIFICATION ---")
    # Fetch transcript from DB
    transcripts = db.query(Transcript).filter(Transcript.call_id == call.id).order_by(Transcript.timestamp.asc()).all()
    print(f"Saved transcript count in DB: {len(transcripts)} entries.")
    
    # Query raw DB database value bypassing SQLAlchemy to prove encryption at rest
    raw_conn = db.bind.connect()
    from sqlalchemy import text
    raw_res = raw_conn.execute(
        text("SELECT speaker, text FROM transcripts WHERE call_id = :call_id"),
        {"call_id": str(call.id)}
    ).fetchall()
    raw_conn.close()
    
    print("\nRaw database values (proving encryption at rest):")
    for row in raw_res:
        speaker, cipher_text = row
        print(f"Speaker: {speaker} | Text (Encrypted): {cipher_text[:50]}...")
        
    print("\nDecrypted values (fetched via SQLAlchemy ORM):")
    for t in transcripts:
        print(f"Speaker: {t.speaker} | Text (Decrypted): {t.text}")
        
    db.close()
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
