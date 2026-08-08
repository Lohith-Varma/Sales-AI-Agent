import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base, Call, Customer, KYCDoc, Transcript
from app.db.database import get_db
from app.main import app


@pytest.fixture()
def api_database():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client, session
    finally:
        app.dependency_overrides.clear()
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_customer_endpoint_returns_transparently_decrypted_kyc(api_database):
    client, session = api_database
    create_response = client.post(
        "/api/customers",
        params={"name": "Test Customer", "phone_number": "+919000000001"},
    )
    assert create_response.status_code == 201

    customer_id = create_response.json()["data"]["customer_id"]
    session.add_all(
        [
            KYCDoc(customer_id=customer_id, doc_type="PAN", doc_status="verified", encrypted_doc_data="Verified ••••P7K"),
            KYCDoc(customer_id=customer_id, doc_type="Date of birth", doc_status="verified", encrypted_doc_data="Verified • 12 Aug 1994"),
            KYCDoc(customer_id=customer_id, doc_type="Address", doc_status="verified", encrypted_doc_data="Verified • Bengaluru, KA"),
        ]
    )
    session.commit()
    response = client.get(f"/api/customers/{customer_id}")

    assert response.status_code == 200
    assert response.json()["data"]["kycFields"] == [
        {"id": response.json()["data"]["kycFields"][0]["id"], "label": "PAN", "value": "Verified ••••P7K", "status": "verified"},
        {"id": response.json()["data"]["kycFields"][1]["id"], "label": "Date of birth", "value": "Verified • 12 Aug 1994", "status": "verified"},
        {"id": response.json()["data"]["kycFields"][2]["id"], "label": "Address", "value": "Verified • Bengaluru, KA", "status": "verified"},
    ]


def test_transcript_endpoint_returns_transparently_decrypted_text(api_database):
    client, session = api_database
    customer = Customer(name="Test Customer", phone_number="+919000000002")
    session.add(customer)
    session.commit()
    call = Call(customer_id=customer.id, status="active")
    session.add(call)
    session.commit()
    session.add(
        Transcript(
            call_id=call.id,
            speaker="customer",
            text="Please call me tomorrow.",
            confidence=0.98,
        )
    )
    session.commit()

    response = client.get(f"/api/calls/{call.id}/transcripts")

    assert response.status_code == 200
    assert response.json()["data"]["transcripts"][0]["text"] == "Please call me tomorrow."
