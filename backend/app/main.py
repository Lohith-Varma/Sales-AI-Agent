import logging
import asyncio
import uuid
import datetime
import time
from collections import defaultdict, deque
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager, suppress
from fastapi import FastAPI, Depends, HTTPException, status, APIRouter, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.config import settings
from app.db.database import get_db, engine
from app.db.base import AgentSession, Base, Customer, Call, Transcript, ConsentLog, ProductOffer, KYCDoc, Lead, Note, User
from app.compliance.audit import log_pii_access
from app.platform_api import router as platform_router, _serialize_customer
from app.security import authenticate_request, hash_password, issue_access_token, verify_password
from app.scheduler.worker import scheduler_loop

# Initialize logger
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger(__name__)

# Startup & Shutdown event logging using lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=== Sales AI Backend Starting Up ===")
    if settings.APP_ENV == "production":
        if not settings.AUTH_REQUIRED or not settings.JWT_SECRET or not settings.INTERNAL_API_KEY:
            raise RuntimeError("Production requires AUTH_REQUIRED, JWT_SECRET, and INTERNAL_API_KEY")
    if settings.USE_SQLITE and not inspect(engine).get_table_names():
        # SQLite is the zero-configuration local fallback. Ensure a fresh local
        # database is usable even when Alembic has not been run yet. Existing
        # databases are migration-owned and must never be mutated by create_all.
        Base.metadata.create_all(bind=engine)
    scheduler_task = asyncio.create_task(scheduler_loop())
    try:
        yield
    finally:
        scheduler_task.cancel()
        with suppress(asyncio.CancelledError):
            await scheduler_task
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

_request_windows: dict[str, deque[float]] = defaultdict(deque)


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)
    now = time.monotonic()
    key = request.client.host if request.client else "unknown"
    window = _request_windows[key]
    while window and now - window[0] >= 60:
        window.popleft()
    if len(window) >= settings.RATE_LIMIT_REQUESTS_PER_MINUTE:
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
    window.append(now)
    public = request.url.path in {"/", "/api/health", "/api/auth/login", "/docs", "/redoc", "/openapi.json"}
    internal = request.url.path.startswith("/api/internal/") or (
        request.url.path == "/api/knowledge-documents" and request.method == "POST"
    )
    if request.url.path.startswith("/api/") and not public and not internal:
        try:
            request.state.user = authenticate_request(request)
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return await call_next(request)

# --- Request Models ---
class WrapUpRequest(BaseModel):
    summary: str
    outcome: str


class LoginRequest(BaseModel):
    email: str
    password: str


class UserCreateRequest(BaseModel):
    email: str
    display_name: str
    password: str
    role: str = "agent"


# --- API Routers ---
api_router = APIRouter(prefix="/api")


@api_router.post("/auth/login", tags=["Authentication"])
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.strip().lower()).first()
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"access_token": issue_access_token(user), "token_type": "bearer", "expires_in": settings.JWT_ACCESS_MINUTES * 60, "user": {"id": str(user.id), "email": user.email, "display_name": user.display_name, "role": user.role}}


@api_router.get("/auth/me", tags=["Authentication"])
def current_user(request: Request):
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication is disabled or no token was supplied")
    return {"id": str(user.id), "email": user.email, "display_name": user.display_name, "role": user.role}


@api_router.get("/users", tags=["Users"])
def list_users(request: Request, db: Session = Depends(get_db)):
    user = getattr(request.state, "user", None)
    if user is None or user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator role required")
    return [{"id": str(item.id), "email": item.email, "display_name": item.display_name, "role": item.role, "is_active": item.is_active, "created_at": item.created_at.isoformat()} for item in db.query(User).order_by(User.created_at.desc()).all()]


@api_router.post("/users", status_code=status.HTTP_201_CREATED, tags=["Users"])
def create_user(payload: UserCreateRequest, request: Request, db: Session = Depends(get_db)):
    actor = getattr(request.state, "user", None)
    if actor is None or actor.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator role required")
    if payload.role not in {"agent", "manager", "admin"}:
        raise HTTPException(status_code=422, detail="Invalid role")
    email = payload.email.strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="User already exists")
    try:
        password_hash = hash_password(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    user = User(email=email, display_name=payload.display_name.strip(), password_hash=password_hash, role=payload.role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": str(user.id), "email": user.email, "display_name": user.display_name, "role": user.role, "is_active": user.is_active}

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
            "auth_required": settings.AUTH_REQUIRED,
            "database": engine.dialect.name,
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
    db.flush()
    # Customer creation opens a real lead. KYC rows are written only by the KYC
    # workflow; the API must never fabricate verified documents.
    db.add(Lead(customer_id=customer.id, source="inbound", stage="new", status="open"))
    db.commit()
    db.refresh(customer)

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
    try:
        cust_uuid = uuid.UUID(customer_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid customer ID") from exc
    customer = db.query(Customer).filter(Customer.id == cust_uuid).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

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
        "data": _serialize_customer(customer)
    }


@api_router.post("/calls", status_code=status.HTTP_201_CREATED, tags=["Calls"])
def initiate_call(customer_id: str, request: Request, direction: str = "inbound", db: Session = Depends(get_db)):
    """Initiates a new call session for a customer."""
    try:
        cust_uuid = uuid.UUID(customer_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid customer ID") from exc
    customer = db.query(Customer).filter(Customer.id == cust_uuid).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    if direction not in {"inbound", "outbound"}:
        raise HTTPException(status_code=422, detail="Direction must be inbound or outbound")
        
    agent_session = None
    authenticated_user = getattr(request.state, "user", None)
    if authenticated_user is not None:
        agent_name = f"{authenticated_user.display_name} ({authenticated_user.email})"
        agent_session = db.query(AgentSession).filter(AgentSession.agent_name == agent_name).first()
        if agent_session is None:
            agent_session = AgentSession(agent_name=agent_name, status="active")
            db.add(agent_session)
            db.flush()
        else:
            agent_session.status = "active"

    call = Call(
        customer_id=customer.id,
        agent_session_id=agent_session.id if agent_session else None,
        status="initiated",
        direction=direction,
        started_at=datetime.datetime.utcnow(),
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
        recorded_announcement_sid=None
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
    
    # EncryptedString transparently decrypts values when SQLAlchemy loads them.
    output = []
    for t in transcripts:
        output.append({
            "id": str(t.id),
            "segment_id": t.segment_id,
            "speaker": t.speaker,
            "text": t.text,
            "timestamp": t.timestamp.isoformat(),
            "confidence": t.confidence,
            "bookmarked": t.bookmarked,
            "sequence": t.sequence_number,
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
    call.summary = payload.summary
    call.outcome = payload.outcome
    call.ended_at = datetime.datetime.utcnow()
    started = call.started_at or call.created_at
    if started:
        call.duration_seconds = max(0, int((call.ended_at - started).total_seconds()))
    db.add(Note(customer_id=call.customer_id, call_id=call.id, body=payload.summary, source="agent_wrap_up"))
    db.commit()
    
    log_pii_access(
        user_id="agent_user",
        action="WRITE_WRAPUP",
        resource=f"call:{call_id}",
        status="SUCCESS",
        details=f"Outcome: {payload.outcome}; summary stored encrypted."
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
    clauses_list = []
    for o in offers:
        clauses_list.append({
            "id": o.type,
            "title": o.name,
            "topic": o.type,
            "body": o.terms,
            "source": f"Database product offer {o.id}",
            "lastSynced": (o.updated_at or o.created_at).isoformat(),
            "stale": not o.is_active
        })
        
    return {
        "success": True,
        "message": "Clauses retrieved successfully",
        "data": clauses_list
    }


# Mount the API router with /api prefix
app.include_router(api_router)
app.include_router(platform_router)
