import os
import uuid
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.db.database import Base
from app.db.base import Customer, Call, Transcript, ConsentLog, ProductOffer

TEST_DB_URL = "sqlite:///./test_temp_db.db"

@pytest.fixture(name="db_session")
def fixture_db_session():
    # Setup SQLite test DB
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session
    
    session.close()
    Base.metadata.drop_all(bind=engine)
    # Clean up test DB file
    if os.path.exists("./test_temp_db.db"):
        try:
            os.remove("./test_temp_db.db")
        except Exception:
            pass


def test_customer_creation_and_encryption(db_session):
    """
    Verify that creating a customer encrypts their PII data at rest
    but returns it decrypted via SQLAlchemy.
    """
    customer_id = uuid.uuid4()
    salary_value = "50000.00"
    
    new_customer = Customer(
        id=customer_id,
        name="Lohith Varma",
        phone_number="+919876543210",
        email="lohith@example.com",
        pii_data_encrypted=salary_value
    )
    db_session.add(new_customer)
    db_session.commit()
    
    # 1. Verify read via SQLAlchemy automatically decrypts
    fetched = db_session.query(Customer).filter(Customer.id == customer_id).first()
    assert fetched.pii_data_encrypted == salary_value
    
    # 2. Verify raw SQL select shows encrypted ciphertext (at-rest check)
    raw_conn = db_session.bind.connect()
    result = raw_conn.execute(
        text("SELECT pii_data_encrypted FROM customers WHERE id = :cust_id"),
        {"cust_id": str(customer_id)}
    ).fetchone()
    raw_conn.close()
    
    raw_val = result[0]
    assert raw_val is not None
    assert raw_val != salary_value
    assert len(raw_val) > 40  # Fernet token length


def test_transcript_encryption(db_session):
    """Verify that transcript text is encrypted in the database."""
    customer = Customer(phone_number="+919999999999")
    db_session.add(customer)
    db_session.commit()
    
    call = Call(customer_id=customer.id, status="initiated")
    db_session.add(call)
    db_session.commit()
    
    sensitive_transcript = "My credit card number is 1234-5678-9012"
    transcript = Transcript(
        call_id=call.id,
        speaker="customer",
        text=sensitive_transcript
    )
    db_session.add(transcript)
    db_session.commit()
    
    # 1. Decrypted by SQLAlchemy ORM
    fetched = db_session.query(Transcript).filter(Transcript.call_id == call.id).first()
    assert fetched.text == sensitive_transcript
    
    # 2. Encrypted in raw DB
    raw_conn = db_session.bind.connect()
    result = raw_conn.execute(
        text("SELECT text FROM transcripts WHERE call_id = :call_id"),
        {"call_id": str(call.id)}
    ).fetchone()
    raw_conn.close()
    
    assert result[0] != sensitive_transcript


def test_consent_logging(db_session):
    """Verify that consent logging can be written and queried correctly."""
    customer = Customer(phone_number="+918888888888")
    db_session.add(customer)
    db_session.commit()
    
    call = Call(customer_id=customer.id, status="active")
    db_session.add(call)
    db_session.commit()
    
    consent = ConsentLog(
        call_id=call.id,
        customer_id=customer.id,
        consent_given=True,
        ip_address="192.168.1.1"
    )
    db_session.add(consent)
    db_session.commit()
    
    fetched = db_session.query(ConsentLog).filter(ConsentLog.call_id == call.id).first()
    assert fetched is not None
    assert fetched.consent_given is True
    assert fetched.ip_address == "192.168.1.1"


def test_safe_vector_type(db_session):
    """Verify that SafeVector stores and retrieves lists of floats."""
    embedding_data = [0.1, -0.2, 0.35, -0.99]
    offer = ProductOffer(
        name="Zero Interest Pay-in-3",
        type="pay_in_3",
        terms="Split into 3 equal parts",
        embedding=embedding_data
    )
    db_session.add(offer)
    db_session.commit()
    
    fetched = db_session.query(ProductOffer).filter(ProductOffer.name == "Zero Interest Pay-in-3").first()
    assert fetched is not None
    assert fetched.embedding == embedding_data
