import uuid
import json
import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator, CHAR

from app.db.database import Base
from app.compliance.encryption import EncryptedString

# --- Platform Independent Types ---

class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(36), storing as stringified hex.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            from sqlalchemy.dialects.postgresql import UUID
            return dialect.type_descriptor(UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        elif dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, uuid.UUID):
                return str(value)
            else:
                return str(uuid.UUID(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if not isinstance(value, uuid.UUID):
            return uuid.UUID(value)
        return value


class SafeVector(TypeDecorator):
    """
    Custom type that maps to pgvector.sqlalchemy.Vector in Postgres
    and to SQLAlchemy.String/Text in SQLite (as a JSON-serialized list of floats).
    """
    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            try:
                from pgvector.sqlalchemy import Vector
                return dialect.type_descriptor(Vector(384))
            except ImportError:
                return dialect.type_descriptor(String(2048))
        else:
            return dialect.type_descriptor(String(2048))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value  # pgvector handles list of floats directly
        else:
            return json.dumps(value)  # SQLite handles as JSON string

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        else:
            try:
                return json.loads(value)
            except Exception:
                return []


# --- SQLAlchemy Models ---

class Customer(Base):
    __tablename__ = "customers"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=True)
    phone_number = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), nullable=True)
    photo_url = Column(String(2048), nullable=True)
    occupation = Column(String(255), nullable=True)
    city = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    lead_score = Column(Integer, default=0, nullable=False)
    stage = Column(String(50), default="new", nullable=False)
    kyc_status = Column(String(50), default="pending", nullable=False)
    tags = Column(JSON, default=list, nullable=False)
    current_intent = Column(String(50), nullable=True)
    current_sentiment = Column(String(50), nullable=True)
    risk_level = Column(String(50), default="low", nullable=False)
    buying_signals = Column(JSON, default=list, nullable=False)
    objections = Column(JSON, default=list, nullable=False)
    
    # Encrypted field containing sensitive data (salary, PAN, credit info etc.)
    pii_data_encrypted = Column(EncryptedString(2048), nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    calls = relationship("Call", back_populates="customer")
    kyc_docs = relationship("KYCDoc", back_populates="customer")
    follow_ups = relationship("FollowUp", back_populates="customer")
    consent_logs = relationship("ConsentLog", back_populates="customer")
    leads = relationship("Lead", back_populates="customer", cascade="all, delete-orphan")
    purchases = relationship("Purchase", back_populates="customer", cascade="all, delete-orphan")
    past_offers = relationship("CustomerOffer", back_populates="customer", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="customer", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="customer", cascade="all, delete-orphan")


class AgentSession(Base):
    __tablename__ = "agent_sessions"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agent_name = Column(String(255), nullable=False)
    status = Column(String(50), default="idle")  # idle, active, offline
    websocket_connected = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    calls = relationship("Call", back_populates="agent_session")


class Call(Base):
    __tablename__ = "calls"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    customer_id = Column(GUID, ForeignKey("customers.id"), nullable=False)
    agent_session_id = Column(GUID, ForeignKey("agent_sessions.id"), nullable=True)
    
    status = Column(String(50), default="initiated")  # initiated, active, completed, failed
    direction = Column(String(20), default="inbound")  # inbound, outbound
    twilio_sid = Column(String(100), nullable=True)
    ai_session_id = Column(String(100), nullable=True, index=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, default=0, nullable=False)
    summary = Column(EncryptedString(8192), nullable=True)
    live_summary = Column(EncryptedString(8192), nullable=True)
    outcome = Column(String(100), nullable=True)
    primary_intent = Column(String(50), nullable=True)
    final_sentiment = Column(String(50), nullable=True)
    compliance_status = Column(String(50), nullable=True)
    compliance_score = Column(Float, nullable=True)
    agent_score = Column(Float, nullable=True)
    satisfaction_score = Column(Float, nullable=True)
    revenue = Column(Float, default=0.0, nullable=False)
    recording_url = Column(String(2048), nullable=True)
    ai_suggestion_count = Column(Integer, default=0, nullable=False)
    ai_suggestion_used_count = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    customer = relationship("Customer", back_populates="calls")
    agent_session = relationship("AgentSession", back_populates="calls")
    transcripts = relationship("Transcript", back_populates="call")
    follow_ups = relationship("FollowUp", back_populates="call")
    consent_logs = relationship("ConsentLog", back_populates="call")
    insights = relationship("CallInsight", back_populates="call", cascade="all, delete-orphan")
    suggestions = relationship("AISuggestion", back_populates="call", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="call", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="call", cascade="all, delete-orphan")


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    call_id = Column(GUID, ForeignKey("calls.id"), nullable=False)
    speaker = Column(String(20), nullable=False)  # customer, agent, ai
    
    # Encrypted transcript text
    text = Column(EncryptedString(4096), nullable=False)
    
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    confidence = Column(Float, nullable=True)
    segment_id = Column(String(100), nullable=True, unique=True, index=True)
    sequence_number = Column(Integer, nullable=True)
    start_seconds = Column(Float, nullable=True)
    end_seconds = Column(Float, nullable=True)
    language = Column(String(20), nullable=True)
    is_final = Column(Boolean, default=True, nullable=False)
    bookmarked = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    call = relationship("Call", back_populates="transcripts")


class ProductOffer(Base):
    __tablename__ = "products_offers"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # pay_in_3, zero_cost_emi
    terms = Column(Text, nullable=False)
    interest_rate = Column(Float, default=0.0)
    tenure_months = Column(Integer, default=3)
    is_active = Column(Boolean, default=True)
    
    # Embeddings for RAG search
    embedding = Column(SafeVector, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class KYCDoc(Base):
    __tablename__ = "kyc_docs"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    customer_id = Column(GUID, ForeignKey("customers.id"), nullable=False)
    doc_type = Column(String(50), nullable=False)  # PAN, Aadhaar, Passport
    doc_status = Column(String(50), default="pending")  # pending, verified, rejected
    
    # Encrypted document contents/metadata
    encrypted_doc_data = Column(EncryptedString(4096), nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    customer = relationship("Customer", back_populates="kyc_docs")


class FollowUp(Base):
    __tablename__ = "follow_ups"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    call_id = Column(GUID, ForeignKey("calls.id"), nullable=False)
    customer_id = Column(GUID, ForeignKey("customers.id"), nullable=False)
    
    scheduled_at = Column(DateTime, nullable=False)
    status = Column(String(50), default="pending")  # pending, scheduled, completed, failed
    attempts = Column(Integer, default=0)
    title = Column(String(255), default="Customer follow-up", nullable=False)
    description = Column(EncryptedString(4096), nullable=True)
    channel = Column(String(30), default="phone", nullable=False)
    priority = Column(String(20), default="normal", nullable=False)
    reminder_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    assigned_user_id = Column(GUID, ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    call = relationship("Call", back_populates="follow_ups")
    customer = relationship("Customer", back_populates="follow_ups")


class ConsentLog(Base):
    __tablename__ = "consent_logs"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    call_id = Column(GUID, ForeignKey("calls.id"), nullable=False)
    customer_id = Column(GUID, ForeignKey("customers.id"), nullable=False)
    
    consent_given = Column(Boolean, nullable=False)
    consent_timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    ip_address = Column(String(100), nullable=True)
    recorded_announcement_sid = Column(String(100), nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    call = relationship("Call", back_populates="consent_logs")
    customer = relationship("Customer", back_populates="consent_logs")


class User(Base):
    __tablename__ = "users"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    display_name = Column(String(255), nullable=False)
    password_hash = Column(String(512), nullable=False)
    role = Column(String(50), default="agent", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class Lead(Base):
    __tablename__ = "leads"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    customer_id = Column(GUID, ForeignKey("customers.id"), nullable=False, index=True)
    owner_user_id = Column(GUID, ForeignKey("users.id"), nullable=True)
    source = Column(String(100), default="inbound", nullable=False)
    stage = Column(String(50), default="new", nullable=False, index=True)
    status = Column(String(50), default="open", nullable=False)
    score = Column(Integer, default=0, nullable=False)
    estimated_value = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    customer = relationship("Customer", back_populates="leads")


class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    customer_id = Column(GUID, ForeignKey("customers.id"), nullable=False, index=True)
    call_id = Column(GUID, ForeignKey("calls.id"), nullable=True, unique=True, index=True)
    product_name = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    purchased_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    status = Column(String(50), default="completed", nullable=False)

    customer = relationship("Customer", back_populates="purchases")


class CustomerOffer(Base):
    __tablename__ = "customer_offers"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    customer_id = Column(GUID, ForeignKey("customers.id"), nullable=False, index=True)
    product_offer_id = Column(GUID, ForeignKey("products_offers.id"), nullable=True)
    offer_name = Column(String(255), nullable=False)
    status = Column(String(50), default="presented", nullable=False)
    presented_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    accepted_at = Column(DateTime, nullable=True)

    customer = relationship("Customer", back_populates="past_offers")


class Note(Base):
    __tablename__ = "notes"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    customer_id = Column(GUID, ForeignKey("customers.id"), nullable=False, index=True)
    call_id = Column(GUID, ForeignKey("calls.id"), nullable=True, index=True)
    author_user_id = Column(GUID, ForeignKey("users.id"), nullable=True)
    body = Column(EncryptedString(8192), nullable=False)
    source = Column(String(50), default="agent", nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    customer = relationship("Customer", back_populates="notes")
    call = relationship("Call", back_populates="notes")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    customer_id = Column(GUID, ForeignKey("customers.id"), nullable=True, index=True)
    call_id = Column(GUID, ForeignKey("calls.id"), nullable=True, index=True)
    assigned_user_id = Column(GUID, ForeignKey("users.id"), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(EncryptedString(4096), nullable=True)
    status = Column(String(50), default="upcoming", nullable=False, index=True)
    priority = Column(String(20), default="normal", nullable=False)
    due_at = Column(DateTime, nullable=True, index=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    customer = relationship("Customer", back_populates="tasks")
    call = relationship("Call", back_populates="tasks")


class CallInsight(Base):
    __tablename__ = "call_insights"
    __table_args__ = (UniqueConstraint("call_id", "sequence_number", name="uq_call_insight_sequence"),)

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    call_id = Column(GUID, ForeignKey("calls.id"), nullable=False, index=True)
    sequence_number = Column(Integer, nullable=False)
    intent = Column(String(50), nullable=True)
    sentiment = Column(String(50), nullable=True)
    lead_score = Column(Integer, nullable=True)
    risk_level = Column(String(50), nullable=True)
    buying_signals = Column(JSON, default=list, nullable=False)
    objections = Column(JSON, default=list, nullable=False)
    next_action = Column(String(100), nullable=True)
    compliance_safe = Column(Boolean, nullable=True)
    confidence = Column(Float, nullable=True)
    payload = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    call = relationship("Call", back_populates="insights")


class AISuggestion(Base):
    __tablename__ = "ai_suggestions"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    call_id = Column(GUID, ForeignKey("calls.id"), nullable=False, index=True)
    insight_id = Column(GUID, ForeignKey("call_insights.id"), nullable=True)
    text = Column(EncryptedString(8192), nullable=False)
    action = Column(String(100), nullable=True)
    citations = Column(JSON, default=list, nullable=False)
    confidence = Column(Float, nullable=True)
    accepted = Column(Boolean, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    call = relationship("Call", back_populates="suggestions")


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    source = Column(String(2048), nullable=False)
    version = Column(String(100), nullable=True)
    category = Column(String(100), nullable=True)
    content_sha256 = Column(String(64), nullable=False, unique=True)
    chunk_count = Column(Integer, default=0, nullable=False)
    status = Column(String(50), default="active", nullable=False)
    indexed_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, ForeignKey("users.id"), nullable=True, index=True)
    kind = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    body = Column(String(2048), nullable=True)
    related_type = Column(String(50), nullable=True)
    related_id = Column(GUID, nullable=True)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
