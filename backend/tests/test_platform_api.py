import datetime as dt

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base, ProductOffer
from app.db.database import get_db
from app.main import app


@pytest.fixture()
def platform_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine)

    def override_get_db():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with factory() as session:
        session.add(ProductOffer(name="Pay-in-3", type="pay_in_3", terms="Three scheduled instalments subject to approval."))
        session.commit()
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_database_backed_call_to_crm_workflow(platform_client: TestClient):
    created = platform_client.post(
        "/api/customers",
        params={"name": "Database Customer", "phone_number": "+919100000001", "email": "db@example.com"},
    )
    assert created.status_code == 201
    customer_id = created.json()["data"]["customer_id"]

    assert platform_client.get("/api/customers/not-a-uuid").status_code == 422
    assert platform_client.get(f"/api/customers/{customer_id}").json()["data"]["kycFields"] == []
    customer_list = platform_client.get("/api/customers", params={"search": "Database"}).json()["data"]
    assert customer_list["total"] == 1

    call = platform_client.post("/api/calls", params={"customer_id": customer_id, "direction": "inbound"})
    assert call.status_code == 201
    call_id = call.json()["data"]["call_id"]
    assert platform_client.post("/api/consent", params={"call_id": call_id, "consent_given": True}).status_code == 201

    transcript = {
        "segments": [
            {
                "segment_id": "segment-1",
                "speaker": "customer",
                "text": "Can I use Pay-in-3?",
                "sequence_number": 0,
                "start_seconds": 0,
                "end_seconds": 1.2,
                "confidence": 0.97,
                "language": "en",
            }
        ]
    }
    first_write = platform_client.post(f"/api/calls/{call_id}/transcripts", json=transcript)
    duplicate_write = platform_client.post(f"/api/calls/{call_id}/transcripts", json=transcript)
    assert first_write.json()["data"]["inserted"] == 1
    assert duplicate_write.json()["data"]["inserted"] == 0
    transcript_rows = platform_client.get(f"/api/calls/{call_id}/transcripts").json()["data"]["transcripts"]
    bookmark = platform_client.patch(f"/api/transcripts/{transcript_rows[0]['id']}/bookmark", params={"bookmarked": True})
    assert bookmark.status_code == 200
    assert bookmark.json()["data"]["bookmarked"] is True

    result = {
        "sequence_number": 0,
        "intent": "interested",
        "sentiment": "positive",
        "latest_transcript": "Can I use Pay-in-3?",
        "confidence": 0.91,
        "suggested_response": {
            "text": "Explain the approved Pay-in-3 terms.",
            "citation_chunk_ids": ["core-product:pay-in-3:0"],
            "confidence": 0.92,
        },
        "next_best_action": {"action": "start_application"},
        "guardrail": {"is_safe": True, "grounding_coverage": 1.0},
    }
    persisted = platform_client.post(f"/api/calls/{call_id}/copilot-results", json={"result": result})
    assert persisted.status_code == 201
    assert platform_client.post(f"/api/calls/{call_id}/copilot-results", json={"result": result}).json()["data"]["duplicate"] is True

    follow_up_date = (dt.date.today() + dt.timedelta(days=1)).isoformat()
    summary = {
        "call_summary": "Customer agreed to continue the Pay-in-3 application.",
        "lead_score": {"score": 85},
        "lead_status": "application_ready",
        "follow_up_date": follow_up_date,
        "customer_concern": "Complete KYC",
    }
    crm = platform_client.post(f"/api/calls/{call_id}/crm-summary", json={"crm_summary": summary})
    assert crm.status_code == 200
    assert crm.json()["data"]["lead_score"] == 85

    profile = platform_client.get(f"/api/customers/{customer_id}").json()["data"]
    assert profile["leadScore"] == 85
    assert profile["stage"] == "application_ready"
    assert len(profile["conversationHistory"]) == 1
    assert len(profile["followUps"]) == 1

    call_detail = platform_client.get(f"/api/calls/{call_id}").json()["data"]
    assert len(call_detail["transcripts"]) == 1
    assert len(call_detail["insights"]) == 1
    assert len(call_detail["suggestions"]) == 1
    assert call_detail["summary"] == summary["call_summary"]

    dashboard = platform_client.get("/api/dashboard").json()["data"]
    assert dashboard["metrics"]["today_calls"] == 1
    assert dashboard["metrics"]["pending_follow_ups"] == 1
    assert dashboard["metrics"]["ai_suggestions"] == 1
    analytics = platform_client.get("/api/analytics").json()["data"]
    assert analytics["intent_distribution"] == [{"name": "interested", "value": 1}]

    tasks = platform_client.get("/api/tasks").json()["data"]
    assert any(item["title"] == "Complete customer follow-up" for item in tasks)
    follow_ups = platform_client.get("/api/follow-ups").json()["data"]
    assert len(follow_ups) == 1
    rescheduled = (dt.datetime.now() + dt.timedelta(days=2)).isoformat()
    edited = platform_client.patch(
        f"/api/follow-ups/{follow_ups[0]['id']}",
        json={"title": "Edited follow-up", "scheduled_at": rescheduled, "priority": "high"},
    )
    assert edited.status_code == 200
    assert edited.json()["data"]["title"] == "Edited follow-up"
    assert edited.json()["data"]["priority"] == "high"


def test_complete_sale_updates_revenue_and_purchase_history(platform_client: TestClient):
    customer = platform_client.post("/api/customers", params={"name": "Buyer", "phone_number": "+919100000002"}).json()["data"]
    call = platform_client.post("/api/calls", params={"customer_id": customer["customer_id"]}).json()["data"]
    sale = platform_client.post(
        f"/api/calls/{call['call_id']}/complete-sale",
        json={"product_name": "Pay-in-3", "amount": 9000, "currency": "INR", "offer_name": "Merchant offer"},
    )
    assert sale.status_code == 201
    replay = platform_client.post(
        f"/api/calls/{call['call_id']}/complete-sale",
        json={"product_name": "Pay-in-3", "amount": 9000, "currency": "INR", "offer_name": "Merchant offer"},
    )
    assert replay.status_code == 201
    assert replay.json()["data"]["purchase_id"] == sale.json()["data"]["purchase_id"]
    dashboard = platform_client.get("/api/dashboard").json()["data"]
    assert dashboard["metrics"]["revenue"] == 9000
    profile = platform_client.get(f"/api/customers/{customer['customer_id']}").json()["data"]
    assert len(profile["previousPurchases"]) == 1
    assert len(profile["pastOffers"]) == 1
    assert profile["previousPurchases"][0]["product"] == "Pay-in-3"
    assert profile["pastOffers"][0]["status"] == "accepted"
    notifications = platform_client.get("/api/notifications").json()["data"]
    assert len(notifications) == 1
    marked = platform_client.patch(f"/api/notifications/{notifications[0]['id']}/read")
    assert marked.status_code == 200
    assert marked.json()["data"]["read_at"] is not None
