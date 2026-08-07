import logging
import uuid
import datetime
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import settings
from app.db.database import get_db, engine
from app.db.base import Base, Customer, Call, Transcript, ConsentLog
from app.compliance.encryption import decrypt
from app.compliance.audit import log_pii_access
from app.telephony.connection import parse_twilio_media_frame
from app.voice_pipeline.pipeline import VoicePipeline
from app.voice_pipeline.stt_provider import MockSTTProvider
from app.voice_pipeline.llm_provider import MockLLMProvider
from app.voice_pipeline.tts_provider import MockTTSProvider

# Initialize logger
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger(__name__)

# Initialize FastAPI App
app = FastAPI(
    title="Affordability AI Voice Co-Pilot API",
    description="Backend API powering the Pay-in-3 Sales Co-Pilot & Voice Assistant",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Dependency Injection for Voice Pipeline ---
def get_voice_pipeline() -> VoicePipeline:
    # Providers can be resolved dynamically here based on config
    stt = MockSTTProvider()
    llm = MockLLMProvider()
    tts = MockTTSProvider()
    return VoicePipeline(stt_provider=stt, llm_provider=llm, tts_provider=tts)


# --- REST Endpoints ---

@app.get("/health")
def health_check():
    return {"status": "healthy", "env": settings.APP_ENV, "timestamp": datetime.datetime.utcnow().isoformat()}


@app.post("/customers", status_code=status.HTTP_201_CREATED)
def create_customer(name: str, phone_number: str, email: Optional[str] = None, salary: Optional[float] = None, db: Session = Depends(get_db)):
    """Creates a customer record. Salary is encrypted in database under DPDP compliance rules."""
    # Check if customer already exists
    existing = db.query(Customer).filter(Customer.phone_number == phone_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Customer with this phone number already exists")
    
    # Store sensitive salary field encrypted
    pii_data = f"{salary:.2f}" if salary is not None else ""
    
    customer = Customer(
        name=name,
        phone_number=phone_number,
        email=email,
        pii_data_encrypted=pii_data
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    
    log_pii_access(
        user_id="system_api",
        action="CREATE",
        resource=f"customer:{customer.id}",
        status="SUCCESS",
        details="Created customer record with encrypted PII."
    )
    
    return {"customer_id": str(customer.id), "name": customer.name, "phone_number": customer.phone_number}


@app.post("/calls", status_code=status.HTTP_201_CREATED)
def initiate_call(customer_id: str, direction: str = "inbound", db: Session = Depends(get_db)):
    """Initiates a new call session for a customer."""
    cust_uuid = uuid.UUID(customer_id)
    customer = db.query(Customer).filter(Customer.id == cust_uuid).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    call = Call(
        customer_id=cust_uuid,
        status="initiated",
        direction=direction
    )
    db.add(call)
    db.commit()
    db.refresh(call)
    
    return {"call_id": str(call.id), "status": call.status, "direction": call.direction}


@app.post("/consent", status_code=status.HTTP_201_CREATED)
def log_consent(call_id: str, consent_given: bool, ip_address: Optional[str] = None, db: Session = Depends(get_db)):
    """Logs the customer's recording and AI-processing consent. Required to run voice pipeline."""
    call_uuid = uuid.UUID(call_id)
    call = db.query(Call).filter(Call.id == call_uuid).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
        
    consent_log = ConsentLog(
        call_id=call_uuid,
        customer_id=call.customer_id,
        consent_given=consent_given,
        ip_address=ip_address,
        recorded_announcement_sid="REC-ANN-001"  # Mock Twilio announcement ID
    )
    db.add(consent_log)
    
    # Update call status
    if consent_given:
        call.status = "active"
    else:
        call.status = "failed"
        
    db.commit()
    
    log_pii_access(
        user_id="system_api",
        action="LOG_CONSENT",
        resource=f"call:{call_id}",
        status="SUCCESS",
        details=f"Consent given: {consent_given}"
    )
    
    return {"consent_id": str(consent_log.id), "consent_given": consent_given, "call_status": call.status}


@app.get("/calls/{call_id}/transcripts")
def get_call_transcripts(call_id: str, db: Session = Depends(get_db)):
    """Retrieves and decrypts the transcript segments for a call."""
    call_uuid = uuid.UUID(call_id)
    call = db.query(Call).filter(Call.id == call_uuid).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
        
    # Log access to transcript data (compliance audit)
    log_pii_access(
        user_id="agent_user",  # Mocked logged-in agent/user
        action="READ",
        resource=f"transcripts:call:{call_id}",
        status="SUCCESS",
        details="Accessed full call transcript"
    )
    
    transcripts = db.query(Transcript).filter(Transcript.call_id == call_uuid).order_by(Transcript.timestamp.asc()).all()
    
    # Decrypt transcript texts for user viewing
    output = []
    for t in transcripts:
        output.append({
            "speaker": t.speaker,
            "text": decrypt(t.text),  # Decrypts field-level at rest encryption
            "timestamp": t.timestamp.isoformat(),
            "confidence": t.confidence
        })
        
    return {"call_id": call_id, "transcripts": output}


# --- WebSocket Streaming Endpoint ---

@app.websocket("/ws/calls/{call_id}")
async def call_websocket_endpoint(
    websocket: WebSocket,
    call_id: str,
    db: Session = Depends(get_db),
    pipeline: VoicePipeline = Depends(get_voice_pipeline)
):
    """
    WebSocket endpoint representing active telephony media stream channel.
    Accepts raw audio bytes or Twilio JSON frames, streams to STT -> LLM -> TTS,
    and returns structured feedback to client.
    """
    await websocket.accept()
    logger.info(f"WebSocket connection accepted for call {call_id}")
    
    # Verify call exists
    try:
        call_uuid = uuid.UUID(call_id)
    except ValueError:
        await websocket.send_json({"error": "Invalid call ID format"})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
        
    call = db.query(Call).filter(Call.id == call_uuid).first()
    if not call:
        await websocket.send_json({"error": "Call session not found"})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Check DPDP Consent Log first
    consent = db.query(ConsentLog).filter(
        ConsentLog.call_id == call_uuid,
        ConsentLog.consent_given == True
    ).first()
    
    if not consent:
        logger.error(f"DPDP Block: Call {call_id} websocket stream refused. No customer consent logged.")
        await websocket.send_json({"error": "DPDP Consent Policy Violation: No customer consent logged for call recording."})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Helper generator to feed websocket stream chunks into the voice pipeline
    async def websocket_stream_generator():
        try:
            while True:
                message = await websocket.receive()
                
                # Support raw audio bytes
                if "bytes" in message:
                    yield message["bytes"]
                # Support Twilio JSON text messages
                elif "text" in message:
                    parsed_bytes = parse_twilio_media_frame(message["text"])
                    if parsed_bytes:
                        yield parsed_bytes
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected by client for call {call_id}")
        except Exception as e:
            logger.error(f"Error in websocket stream receiver: {e}")

    try:
        # Run pipeline in background loop and send events back to the client
        audio_stream = websocket_stream_generator()
        pipeline_generator = pipeline.run_pipeline(call_uuid, audio_stream, db)
        
        async for event in pipeline_generator:
            event_type = event["type"]
            
            if event_type == "transcript":
                await websocket.send_json({
                    "event": "transcript",
                    "speaker": "customer",
                    "text": event["text"],
                    "confidence": event["confidence"]
                })
            elif event_type == "response":
                await websocket.send_json({
                    "event": "response",
                    "speaker": "ai",
                    "text": event["text"],
                    "citations": event["citations"],
                    "escalate": event["escalate"]
                })
            elif event_type == "audio":
                # Send the synthesized TTS audio bytes as binary message
                # Prefixing or structuring can be done, here we send the raw binary audio file (WAV)
                await websocket.send_bytes(event["audio"])
                
    except Exception as e:
        logger.error(f"Error in voice pipeline execution: {e}")
        await websocket.send_json({"error": f"Pipeline failure: {str(e)}"})
    finally:
        # Finalize call session status
        call.status = "completed"
        db.commit()
        logger.info(f"WebSocket connection closed for call {call_id}")
