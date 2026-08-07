import os
import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db.base import Customer, Call, ConsentLog, Transcript
from app.compliance.encryption import decrypt
from app.telephony.mock_source import mock_audio_stream
from app.voice_pipeline.pipeline import VoicePipeline
from app.voice_pipeline.stt_provider import MockSTTProvider
from app.voice_pipeline.llm_provider import MockLLMProvider
from app.voice_pipeline.tts_provider import MockTTSProvider

TEST_DB_URL = "sqlite:///./test_pipeline_db.db"

@pytest.fixture(name="db_session")
def fixture_db_session():
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session
    
    session.close()
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test_pipeline_db.db"):
        try:
            os.remove("./test_pipeline_db.db")
        except Exception:
            pass


@pytest.mark.asyncio
async def test_pipeline_consent_violation_raises(db_session):
    """
    Verify that running the voice pipeline on a call without consent
    raises a PermissionError (DPDP compliance check).
    """
    # Create customer and call (no consent log created)
    customer = Customer(name="Test User", phone_number="+911111111111")
    db_session.add(customer)
    db_session.commit()
    
    call = Call(customer_id=customer.id, status="initiated")
    db_session.add(call)
    db_session.commit()
    
    pipeline = VoicePipeline(
        stt_provider=MockSTTProvider(),
        llm_provider=MockLLMProvider(),
        tts_provider=MockTTSProvider()
    )
    
    # Executing the pipeline should immediately raise a PermissionError
    audio_stream = mock_audio_stream(num_chunks=5)
    with pytest.raises(PermissionError) as exc_info:
        # We need to iterate or call next on the async generator to trigger the execution start
        async for _ in pipeline.run_pipeline(call.id, audio_stream, db_session):
            pass
            
    assert "consent must be logged" in str(exc_info.value)


@pytest.mark.asyncio
async def test_pipeline_streaming_success(db_session):
    """
    Verify that running the voice pipeline on a call with consent
    correctly yields transcripts, answers, and audio bytes, and persists
    the conversation segments in the database.
    """
    # 1. Create customer, call, and log consent
    customer = Customer(name="Test User", phone_number="+912222222222")
    db_session.add(customer)
    db_session.commit()
    
    call = Call(customer_id=customer.id, status="initiated")
    db_session.add(call)
    db_session.commit()
    
    consent = ConsentLog(call_id=call.id, customer_id=customer.id, consent_given=True)
    db_session.add(consent)
    db_session.commit()
    
    # 2. Setup pipeline and stream 25 chunks (which will trigger at least two simulated utterances)
    pipeline = VoicePipeline(
        stt_provider=MockSTTProvider(),
        llm_provider=MockLLMProvider(),
        tts_provider=MockTTSProvider()
    )
    
    events = []
    audio_stream = mock_audio_stream(num_chunks=25)
    async for event in pipeline.run_pipeline(call.id, audio_stream, db_session):
        events.append(event)
        
    # Check that events were generated
    assert len(events) > 0
    
    # Check that we received transcripts and responses
    event_types = [e["type"] for e in events]
    assert "transcript" in event_types
    assert "response" in event_types
    assert "audio" in event_types
    
    # Verify that transcript events contain valid text
    transcripts_received = [e["text"] for e in events if e["type"] == "transcript"]
    assert len(transcripts_received) > 0
    assert "pay-in-3" in transcripts_received[0] or "documents" in transcripts_received[0] or "verification" in transcripts_received[0]
    
    # Verify that audio bytes are yielded
    audio_events = [e for e in events if e["type"] == "audio"]
    assert len(audio_events) > 0
    assert len(audio_events[0]["audio"]) > 44  # WAV header is at least 44 bytes
    
    # Verify that transcripts were persisted in DB
    db_transcripts = db_session.query(Transcript).filter(Transcript.call_id == call.id).all()
    assert len(db_transcripts) >= 2
    
    # Verify that saved text is encrypted at rest, but decrypted upon fetch (through SQL Alchemy)
    # The first transcript in DB
    assert db_transcripts[0].text is not None
    # SQLAlchemy decrypts automatically
    assert any(term in db_transcripts[0].text.lower() for term in ["pay-in-3", "documents", "kyc", "late", "miss"])
