import uuid
import json
import datetime
from typing import Optional, List
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
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
    
    # Encrypted field containing sensitive data (salary, PAN, credit info etc.)
    pii_data_encrypted = Column(EncryptedString(2048), nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    calls = relationship("Call", back_populates="customer")
    kyc_docs = relationship("KYCDoc", back_populates="customer")
    follow_ups = relationship("FollowUp", back_populates="customer")
    consent_logs = relationship("ConsentLog", back_populates="customer")


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
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    customer = relationship("Customer", back_populates="calls")
    agent_session = relationship("AgentSession", back_populates="calls")
    transcripts = relationship("Transcript", back_populates="call")
    follow_ups = relationship("FollowUp", back_populates="call")
    consent_logs = relationship("ConsentLog", back_populates="call")


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    call_id = Column(GUID, ForeignKey("calls.id"), nullable=False)
    speaker = Column(String(20), nullable=False)  # customer, agent, ai
    
    # Encrypted transcript text
    text = Column(EncryptedString(4096), nullable=False)
    
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    confidence = Column(Float, nullable=True)
    
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
