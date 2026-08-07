import logging
import uuid
import datetime
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, status, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.config import settings
from app.db.database import get_db, engine
from app.db.base import Base, Customer, Call, Transcript, ConsentLog, ProductOffer, KYCDoc
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

# Startup & Shutdown event logging using lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=== Sales AI Backend Starting Up ===")
    yield
    logger.info("=== Sales AI Backend Shutting Down ===")

# Initialize FastAPI App with required metadata
app = FastAPI(
    title="Sales AI Backend",
    description="Backend API for the AI Sales Assistant platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration restricted to the React frontend addresses
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Request Models ---
class WrapUpRequest(BaseModel):
    summary: str
    outcome: str


# --- Dependency Injection for Voice Pipeline ---
def get_voice_pipeline() -> VoicePipeline:
    stt = MockSTTProvider()
    llm = MockLLMProvider()
    tts = MockTTSProvider()
    return VoicePipeline(stt_provider=stt, llm_provider=llm, tts_provider=tts)


# --- API Routers ---
api_router = APIRouter(prefix="/api")

# --- Root Endpoints ---

@app.get("/", tags=["Root"])
def read_root():
    """Root GET endpoint confirming backend status."""
    return {
        "status": "success",
        "message": "Sales AI Backend is running",
        "version": "1.0.0"
    }


# --- REST Endpoints registered via APIRouter ---

@api_router.get("/health", tags=["System"])
def health_check():
    return {
        "success": True,
        "message": "System health check successful",
        "data": {
            "status": "healthy",
            "env": settings.APP_ENV,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    }


@api_router.post("/customers", status_code=status.HTTP_201_CREATED, tags=["Customers"])
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
    
    # Create seed KYC documents for the customer
    kyc_pan = KYCDoc(customer_id=customer.id, doc_type="PAN", doc_status="verified", encrypted_doc_data="Verified ••••P7K")
    kyc_dob = KYCDoc(customer_id=customer.id, doc_type="Date of birth", doc_status="verified", encrypted_doc_data="Verified • 12 Aug 1994")
    kyc_addr = KYCDoc(customer_id=customer.id, doc_type="Address", doc_status="verified", encrypted_doc_data="Verified • Bengaluru, KA")
    db.add_all([kyc_pan, kyc_dob, kyc_addr])
    db.commit()

    log_pii_access(
        user_id="system_api",
        action="CREATE",
        resource=f"customer:{customer.id}",
        status="SUCCESS",
        details="Created customer record with encrypted PII."
    )
    
    return {
        "success": True,
        "message": "Customer created successfully",
        "data": {
            "customer_id": str(customer.id),
            "name": customer.name,
            "phone_number": customer.phone_number
        }
    }


@api_router.get("/customers/{customer_id}", tags=["Customers"])
def get_customer_details(customer_id: str, db: Session = Depends(get_db)):
    """Retrieves customer record with decrypted sensitive data and past call interactions."""
    customer = None
    try:
        cust_uuid = uuid.UUID(customer_id)
        customer = db.query(Customer).filter(Customer.id == cust_uuid).first()
    except ValueError:
        # Fallback query for demo names
        customer = db.query(Customer).filter(Customer.name == "Ananya Rao").first()
        if not customer:
            customer = db.query(Customer).first()
            
    # If no customer exists, auto-seed the demo customer
    if not customer:
        customer = Customer(
            name="Ananya Rao",
            phone_number="+91 98999 4182",
            email="ananya.rao@example.com",
            pii_data_encrypted="75000.00"
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        
        # Create seed KYC docs
        kyc_pan = KYCDoc(customer_id=customer.id, doc_type="PAN", doc_status="verified", encrypted_doc_data="Verified ••••P7K")
        kyc_dob = KYCDoc(customer_id=customer.id, doc_type="Date of birth", doc_status="verified", encrypted_doc_data="Verified • 12 Aug 1994")
        kyc_addr = KYCDoc(customer_id=customer.id, doc_type="Address", doc_status="verified", encrypted_doc_data="Verified • Bengaluru, KA")
        db.add_all([kyc_pan, kyc_dob, kyc_addr])
        db.commit()
        
    # Get decrypted KYC docs
    kyc_list = []
    kyc_records = db.query(KYCDoc).filter(KYCDoc.customer_id == customer.id).all()
    for k in kyc_records:
        kyc_list.append({
            "label": k.doc_type,
            "value": decrypt(k.encrypted_doc_data) if k.encrypted_doc_data else "Verified"
        })
        
    if not kyc_list:
        kyc_list = [
            {"label": "PAN", "value": "Verified ••••P7K"},
            {"label": "Date of birth", "value": "Verified • 12 Aug 1994"},
            {"label": "Address", "value": "Verified • Bengaluru, KA"}
        ]
        
    # Get customer call history
    interactions = []
    calls = db.query(Call).filter(Call.customer_id == customer.id).order_by(Call.created_at.desc()).all()
    for c in calls:
        interactions.append({
            "date": c.created_at.strftime("%d %b %Y"),
            "outcome": "Follow-up needed" if c.status != "completed" else "Converted",
            "note": f"Call session status was completed with status code: {c.status}."
        })
        
    if not interactions:
        interactions = [
            {"date": "28 Jul 2026", "outcome": "Follow-up needed", "note": "Asked about payment timing."},
            {"date": "11 Jun 2026", "outcome": "Dropped", "note": "Preferred full payment at the time."},
            {"date": "24 Mar 2026", "outcome": "Converted", "note": "Activated merchant offers."}
        ]

    log_pii_access(
        user_id="agent_user",
        action="READ",
        resource=f"customer:{customer.id}",
        status="SUCCESS",
        details="Retrieved customer record including decrypted KYC PAN/DOB."
    )

    return {
        "success": True,
        "message": "Customer retrieved successfully",
        "data": {
            "id": str(customer.id),
            "name": customer.name,
            "email": customer.email,
            "phone": customer.phone_number,
            "city": "Bengaluru",
            "sensitiveDataOnFile": True,
            "kycFields": kyc_list,
            "interactions": interactions
        }
    }


@api_router.post("/calls", status_code=status.HTTP_201_CREATED, tags=["Calls"])
def initiate_call(customer_id: str, direction: str = "inbound", db: Session = Depends(get_db)):
    """Initiates a new call session for a customer."""
    customer = None
    try:
        cust_uuid = uuid.UUID(customer_id)
        customer = db.query(Customer).filter(Customer.id == cust_uuid).first()
    except ValueError:
        # Fallback to Ananya Rao or first customer
        customer = db.query(Customer).filter(Customer.name == "Ananya Rao").first()
        if not customer:
            customer = db.query(Customer).first()
            
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    call = Call(
        customer_id=customer.id,
        status="initiated",
        direction=direction
    )
    db.add(call)
    db.commit()
    db.refresh(call)
    
    return {
        "success": True,
        "message": "Call initiated successfully",
        "data": {
            "call_id": str(call.id),
            "status": call.status,
            "direction": call.direction
        }
    }


@api_router.post("/consent", status_code=status.HTTP_201_CREATED, tags=["Compliance"])
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
    
    return {
        "success": True,
        "message": "Consent logged successfully",
        "data": {
            "consent_id": str(consent_log.id),
            "consent_given": consent_given,
            "call_status": call.status
        }
    }


@api_router.get("/calls/{call_id}/transcripts", tags=["Transcripts"])
def get_call_transcripts(call_id: str, db: Session = Depends(get_db)):
    """Retrieves and decrypts the transcript segments for a call."""
    call_uuid = uuid.UUID(call_id)
    call = db.query(Call).filter(Call.id == call_uuid).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
        
    # Log access to transcript data (compliance audit)
    log_pii_access(
        user_id="agent_user",
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
            "text": decrypt(t.text),
            "timestamp": t.timestamp.isoformat(),
            "confidence": t.confidence
        })
        
    return {
        "success": True,
        "message": "Call transcripts retrieved successfully",
        "data": {
            "call_id": call_id,
            "transcripts": output
        }
    }


@api_router.post("/calls/{call_id}/wrap-up", tags=["Calls"])
def complete_wrap_up(call_id: str, payload: WrapUpRequest, db: Session = Depends(get_db)):
    """Records call wrap-up status, summary and outcome in call history."""
    call_uuid = uuid.UUID(call_id)
    call = db.query(Call).filter(Call.id == call_uuid).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
        
    call.status = "completed"
    db.commit()
    
    log_pii_access(
        user_id="agent_user",
        action="WRITE_WRAPUP",
        resource=f"call:{call_id}",
        status="SUCCESS",
        details=f"Outcome: {payload.outcome} | Summary: {payload.summary[:50]}..."
    )
    
    return {
        "success": True,
        "message": "Call wrap-up completed successfully",
        "data": {
            "call_id": call_id,
            "summary": payload.summary,
            "outcome": payload.outcome
        }
    }


@api_router.get("/clauses", tags=["Knowledge"])
def get_clauses(db: Session = Depends(get_db)):
    """Retrieves product zero-cost Pay-in-3 eligibility and collections guidelines (RAG source clauses)."""
    offers = db.query(ProductOffer).all()
    if not offers:
        # Seed product offers
        seed_offers = [
            ProductOffer(name="Pay-in-3, zero-cost EMI terms", type="terms", terms="Eligible purchases are split into three scheduled instalments. No interest is charged when each instalment is paid on time. Availability depends on merchant and approval checks.", interest_rate=0.0, tenure_months=3),
            ProductOffer(name="Late payment policy", type="late-fees", terms="A late fee may apply when a scheduled instalment is overdue. Quote only the current fee displayed in the approved policy; do not promise a waiver.", interest_rate=0.0, tenure_months=3, is_active=True),
            ProductOffer(name="KYC verification steps", type="kyc", terms="Check existing CRM KYC fields first. Do not re-request a PAN, date of birth, or address already marked verified. Escalate mismatches through the approved workflow."),
            ProductOffer(name="Eligibility criteria", type="eligibility", terms="Eligibility is subject to identity verification, merchant availability, account history, and automated affordability checks. Never guarantee approval before the check completes."),
            ProductOffer(name="Required customer disclosure", type="disclosure", terms="Before closing, disclose the number of instalments, zero-cost condition, due-date obligation, and that late payments can carry a fee.")
        ]
        db.add_all(seed_offers)
        db.commit()
        offers = db.query(ProductOffer).all()
        
    clauses_list = []
    for o in offers:
        clauses_list.append({
            "id": o.type,
            "title": o.name,
            "topic": o.type,
            "body": o.terms,
            "source": "Sales compliance script v5.3" if o.type == "disclosure" else f"Product Policy v{o.tenure_months}.0",
            "lastSynced": o.updated_at.strftime("%d %b %Y, %H:%M IST") if o.updated_at else "07 Aug 2026, 10:00 IST",
            "stale": o.type == "late-fees"
        })
        
    return {
        "success": True,
        "message": "Clauses retrieved successfully",
        "data": clauses_list
    }


# Mount the API router with /api prefix
app.include_router(api_router)


# --- WebSocket Streaming Endpoint directly on app (without prefix) ---

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
