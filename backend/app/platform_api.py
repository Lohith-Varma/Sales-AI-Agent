"""Database-backed CRM, work-management, call intelligence, and analytics APIs.

The original project exposed only a handful of demo endpoints.  This module keeps
the existing route shapes intact while adding the production workflow contracts
used by the sales workspace.  Every response is assembled from SQLAlchemy rows;
there are no synthetic dashboard values or fallback customers here.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import os
import uuid
from collections import Counter, defaultdict
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.db.base import (
    AISuggestion,
    AgentSession,
    Call,
    CallInsight,
    ConsentLog,
    Customer,
    CustomerOffer,
    FollowUp,
    KnowledgeDocument,
    KYCDoc,
    Lead,
    Note,
    Notification,
    ProductOffer,
    Purchase,
    Task,
    Transcript,
)
from app.db.database import get_db


router = APIRouter(prefix="/api", tags=["Platform"])


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC).replace(tzinfo=None)


def _uuid(value: str, resource: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"Invalid {resource} ID") from exc


def _get_customer(db: Session, customer_id: str) -> Customer:
    customer = db.get(Customer, _uuid(customer_id, "customer"))
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


def _get_call(db: Session, call_id: str) -> Call:
    call = db.get(Call, _uuid(call_id, "call"))
    if call is None:
        raise HTTPException(status_code=404, detail="Call not found")
    return call


def _internal_key_valid(value: str | None) -> bool:
    if settings.APP_ENV in {"development", "test"}:
        return True
    configured = getattr(settings, "INTERNAL_API_KEY", None)
    return bool(value and configured and value == configured)



def _require_internal_key(x_internal_api_key: str | None = Header(default=None)) -> None:
    if not _internal_key_valid(x_internal_api_key):
        raise HTTPException(status_code=401, detail="Invalid internal service credential")


def _call_duration(call: Call) -> int:
    if call.duration_seconds:
        return int(call.duration_seconds)
    started = call.started_at or call.created_at
    ended = call.ended_at
    if started and ended:
        return max(0, int((ended - started).total_seconds()))
    return 0


def _serialize_transcript(item: Transcript) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "segment_id": item.segment_id,
        "speaker": item.speaker,
        "text": item.text,
        "timestamp": item.timestamp.isoformat() if item.timestamp else None,
        "confidence": item.confidence,
        "sequence_number": item.sequence_number,
        "start_seconds": item.start_seconds,
        "end_seconds": item.end_seconds,
        "language": item.language,
        "is_final": item.is_final,
        "bookmarked": item.bookmarked,
    }


def _serialize_follow_up(item: FollowUp) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "call_id": str(item.call_id),
        "customer_id": str(item.customer_id),
        "customer_name": item.customer.name if item.customer else None,
        "title": item.title,
        "description": item.description,
        "scheduled_at": item.scheduled_at.isoformat(),
        "reminder_at": item.reminder_at.isoformat() if item.reminder_at else None,
        "completed_at": item.completed_at.isoformat() if item.completed_at else None,
        "status": item.status,
        "channel": item.channel,
        "priority": item.priority,
        "attempts": item.attempts,
    }


def _serialize_task(item: Task) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "customer_id": str(item.customer_id) if item.customer_id else None,
        "customer_name": item.customer.name if item.customer else None,
        "call_id": str(item.call_id) if item.call_id else None,
        "title": item.title,
        "description": item.description,
        "status": item.status,
        "priority": item.priority,
        "due_at": item.due_at.isoformat() if item.due_at else None,
        "completed_at": item.completed_at.isoformat() if item.completed_at else None,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def _serialize_customer(customer: Customer) -> dict[str, Any]:
    calls = sorted(customer.calls, key=lambda item: item.created_at or dt.datetime.min, reverse=True)
    kyc_docs = sorted(customer.kyc_docs, key=lambda item: item.created_at or dt.datetime.min)
    follow_ups = sorted(
        customer.follow_ups, key=lambda item: item.scheduled_at or dt.datetime.min, reverse=True
    )
    notes = sorted(customer.notes, key=lambda item: item.created_at or dt.datetime.min, reverse=True)
    purchases = sorted(
        customer.purchases, key=lambda item: item.purchased_at or dt.datetime.min, reverse=True
    )
    past_offers = sorted(
        customer.past_offers, key=lambda item: item.presented_at or dt.datetime.min, reverse=True
    )
    return {
        "id": str(customer.id),
        "photo": customer.photo_url,
        "name": customer.name,
        "phone": customer.phone_number,
        "email": customer.email,
        "occupation": customer.occupation,
        "city": customer.city,
        "location": customer.location or customer.city,
        "leadScore": customer.lead_score,
        "stage": customer.stage,
        "kycStatus": customer.kyc_status,
        "tags": customer.tags or [],
        "currentIntent": customer.current_intent,
        "currentSentiment": customer.current_sentiment,
        "riskLevel": customer.risk_level,
        "buyingSignals": customer.buying_signals or [],
        "objections": customer.objections or [],
        "sensitiveDataOnFile": bool(customer.pii_data_encrypted or kyc_docs),
        "kycFields": [
            {
                "id": str(item.id),
                "label": item.doc_type,
                "value": item.encrypted_doc_data,
                "status": item.doc_status,
            }
            for item in kyc_docs
        ],
        "previousCalls": [
            {
                "id": str(item.id),
                "date": item.created_at.isoformat() if item.created_at else None,
                "status": item.status,
                "outcome": item.outcome,
                "summary": item.summary,
                "durationSeconds": _call_duration(item),
                "intent": item.primary_intent,
                "sentiment": item.final_sentiment,
            }
            for item in calls
        ],
        "interactions": [
            {
                "date": (item.created_at or _utcnow()).strftime("%d %b %Y"),
                "outcome": item.outcome or item.status,
                "note": item.summary or "No call summary has been recorded.",
            }
            for item in calls
        ],
        "previousPurchases": [
            {
                "id": str(item.id),
                "product": item.product_name,
                "amount": item.amount,
                "currency": item.currency,
                "status": item.status,
                "purchasedAt": item.purchased_at.isoformat(),
            }
            for item in purchases
        ],
        "pastOffers": [
            {
                "id": str(item.id),
                "name": item.offer_name,
                "status": item.status,
                "presentedAt": item.presented_at.isoformat(),
                "acceptedAt": item.accepted_at.isoformat() if item.accepted_at else None,
            }
            for item in past_offers
        ],
        "followUps": [_serialize_follow_up(item) for item in follow_ups],
        "conversationHistory": [
            {
                "id": str(item.id),
                "body": item.body,
                "source": item.source,
                "callId": str(item.call_id) if item.call_id else None,
                "createdAt": item.created_at.isoformat() if item.created_at else None,
            }
            for item in notes
        ],
        "createdAt": customer.created_at.isoformat() if customer.created_at else None,
        "updatedAt": customer.updated_at.isoformat() if customer.updated_at else None,
    }


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    photo_url: str | None = Field(default=None, max_length=2048)
    occupation: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    stage: str | None = Field(default=None, max_length=50)
    tags: list[str] | None = Field(default=None, max_length=50)


class NoteUpsert(BaseModel):
    body: str = Field(min_length=1, max_length=8192)


class FollowUpCreate(BaseModel):
    call_id: str
    customer_id: str
    scheduled_at: dt.datetime
    title: str = Field(default="Customer follow-up", min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4096)
    channel: Literal["phone", "sms", "email", "whatsapp"] = "phone"
    priority: Literal["low", "normal", "high", "urgent"] = "normal"
    reminder_at: dt.datetime | None = None


class FollowUpUpdate(BaseModel):
    scheduled_at: dt.datetime | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4096)
    channel: Literal["phone", "sms", "email", "whatsapp"] | None = None
    priority: Literal["low", "normal", "high", "urgent"] | None = None
    status: Literal["pending", "scheduled", "completed", "failed"] | None = None
    reminder_at: dt.datetime | None = None


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4096)
    customer_id: str | None = None
    call_id: str | None = None
    priority: Literal["low", "normal", "high", "urgent"] = "normal"
    due_at: dt.datetime | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4096)
    priority: Literal["low", "normal", "high", "urgent"] | None = None
    status: Literal["upcoming", "today", "completed", "overdue"] | None = None
    due_at: dt.datetime | None = None


class TranscriptSegmentInput(BaseModel):
    segment_id: str = Field(min_length=1, max_length=100)
    speaker: str = Field(default="customer", max_length=20)
    text: str = Field(min_length=1, max_length=4096)
    sequence_number: int | None = Field(default=None, ge=0)
    start_seconds: float | None = Field(default=None, ge=0)
    end_seconds: float | None = Field(default=None, ge=0)
    confidence: float | None = Field(default=None, ge=0, le=1)
    language: str | None = Field(default=None, max_length=20)
    timestamp: dt.datetime | None = None


class TranscriptBatch(BaseModel):
    segments: list[TranscriptSegmentInput] = Field(min_length=1, max_length=100)


class SessionLink(BaseModel):
    ai_session_id: str = Field(min_length=1, max_length=100)


class CopilotResultInput(BaseModel):
    result: dict[str, Any]


class CRMSummaryInput(BaseModel):
    crm_summary: dict[str, Any]
    requires_human_review: bool = False


class KYCRecordInput(BaseModel):
    doc_type: str = Field(min_length=1, max_length=50)
    status: Literal["pending", "verified", "rejected"] = "pending"
    value: str | None = Field(default=None, max_length=4096)


class CompleteSaleInput(BaseModel):
    product_name: str = Field(min_length=1, max_length=255)
    amount: float = Field(gt=0)
    currency: str = Field(default="INR", min_length=3, max_length=10)
    offer_name: str | None = Field(default=None, max_length=255)
    summary: str | None = Field(default=None, min_length=10, max_length=8192)


@router.get("/customers")
def list_customers(
    search: str | None = None,
    stage: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    query = db.query(Customer)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            Customer.name.ilike(pattern)
            | Customer.phone_number.ilike(pattern)
            | Customer.email.ilike(pattern)
        )
    if stage:
        query = query.filter(Customer.stage == stage)
    total = query.count()
    rows = query.order_by(Customer.updated_at.desc()).offset(offset).limit(limit).all()
    return {"success": True, "message": "Customers retrieved", "data": {"items": [_serialize_customer(item) for item in rows], "total": total, "limit": limit, "offset": offset}}


@router.patch("/customers/{customer_id}")
def update_customer(customer_id: str, payload: CustomerUpdate, db: Session = Depends(get_db)) -> dict[str, Any]:
    customer = _get_customer(db, customer_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(customer, key, value)
    db.commit()
    db.refresh(customer)
    return {"success": True, "message": "Customer updated", "data": _serialize_customer(customer)}


@router.post("/customers/{customer_id}/kyc", status_code=status.HTTP_201_CREATED)
def create_kyc_record(customer_id: str, payload: KYCRecordInput, db: Session = Depends(get_db)) -> dict[str, Any]:
    customer = _get_customer(db, customer_id)
    existing = db.query(KYCDoc).filter(KYCDoc.customer_id == customer.id, KYCDoc.doc_type == payload.doc_type).order_by(KYCDoc.created_at.desc()).first()
    if existing is not None and existing.doc_status in {"pending", "verified"} and payload.status == "pending":
        return {"success": True, "message": "KYC workflow already exists", "data": {"id": str(existing.id), "doc_type": existing.doc_type, "status": existing.doc_status}}
    item = KYCDoc(customer_id=customer.id, doc_type=payload.doc_type, doc_status=payload.status, encrypted_doc_data=payload.value)
    db.add(item)
    db.flush()
    statuses = [record.doc_status for record in customer.kyc_docs]
    customer.kyc_status = "verified" if statuses and all(value == "verified" for value in statuses) else "rejected" if "rejected" in statuses else "in_progress"
    db.commit()
    db.refresh(item)
    return {"success": True, "message": "KYC record created", "data": {"id": str(item.id), "doc_type": item.doc_type, "status": item.doc_status}}


@router.patch("/kyc/{kyc_id}")
def update_kyc_record(kyc_id: str, payload: KYCRecordInput, db: Session = Depends(get_db)) -> dict[str, Any]:
    item = db.get(KYCDoc, _uuid(kyc_id, "KYC"))
    if item is None:
        raise HTTPException(status_code=404, detail="KYC record not found")
    item.doc_type = payload.doc_type
    item.doc_status = payload.status
    item.encrypted_doc_data = payload.value
    statuses = [record.doc_status for record in item.customer.kyc_docs]
    item.customer.kyc_status = "verified" if statuses and all(value == "verified" for value in statuses) else "rejected" if "rejected" in statuses else "in_progress"
    db.commit()
    return {"success": True, "message": "KYC record updated", "data": {"id": str(item.id), "doc_type": item.doc_type, "status": item.doc_status}}


@router.get("/leads")
def list_leads(stage: str | None = None, db: Session = Depends(get_db)) -> dict[str, Any]:
    query = db.query(Lead)
    if stage:
        query = query.filter(Lead.stage == stage)
    rows = query.order_by(Lead.updated_at.desc()).all()
    return {"success": True, "message": "Leads retrieved", "data": [{"id": str(item.id), "customer_id": str(item.customer_id), "customer_name": item.customer.name, "stage": item.stage, "status": item.status, "score": item.score, "source": item.source, "estimated_value": item.estimated_value, "updated_at": item.updated_at.isoformat()} for item in rows]}


@router.get("/calls")
def list_calls(
    call_status: str | None = Query(default=None, alias="status"),
    customer_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    query = db.query(Call)
    if call_status:
        query = query.filter(Call.status == call_status)
    if customer_id:
        query = query.filter(Call.customer_id == _uuid(customer_id, "customer"))
    calls = query.order_by(Call.created_at.desc()).limit(limit).all()
    return {"success": True, "message": "Calls retrieved", "data": [{"id": str(item.id), "customer_id": str(item.customer_id), "customer_name": item.customer.name if item.customer else None, "status": item.status, "direction": item.direction, "started_at": item.started_at.isoformat() if item.started_at else None, "ended_at": item.ended_at.isoformat() if item.ended_at else None, "duration_seconds": _call_duration(item), "summary": item.summary, "outcome": item.outcome, "intent": item.primary_intent, "sentiment": item.final_sentiment, "compliance_score": item.compliance_score, "agent_score": item.agent_score, "recording_url": item.recording_url, "revenue": item.revenue} for item in calls]}


@router.get("/calls/{call_id}")
def get_call_detail(call_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    call = _get_call(db, call_id)
    return {"success": True, "message": "Call retrieved", "data": {"id": str(call.id), "customer": _serialize_customer(call.customer), "status": call.status, "direction": call.direction, "ai_session_id": call.ai_session_id, "started_at": call.started_at.isoformat() if call.started_at else None, "ended_at": call.ended_at.isoformat() if call.ended_at else None, "duration_seconds": _call_duration(call), "summary": call.summary, "live_summary": call.live_summary, "outcome": call.outcome, "intent": call.primary_intent, "sentiment": call.final_sentiment, "compliance_status": call.compliance_status, "compliance_score": call.compliance_score, "agent_score": call.agent_score, "satisfaction_score": call.satisfaction_score, "recording_url": call.recording_url, "revenue": call.revenue, "transcripts": [_serialize_transcript(item) for item in sorted(call.transcripts, key=lambda value: value.timestamp or dt.datetime.min)], "insights": [item.payload for item in sorted(call.insights, key=lambda value: value.sequence_number)], "suggestions": [{"id": str(item.id), "text": item.text, "action": item.action, "citations": item.citations or [], "confidence": item.confidence, "accepted": item.accepted, "created_at": item.created_at.isoformat()} for item in call.suggestions], "notes": [{"id": str(item.id), "body": item.body, "source": item.source, "created_at": item.created_at.isoformat()} for item in call.notes], "follow_ups": [_serialize_follow_up(item) for item in call.follow_ups]}}


@router.put("/calls/{call_id}/note")
def upsert_call_note(call_id: str, payload: NoteUpsert, db: Session = Depends(get_db)) -> dict[str, Any]:
    call = _get_call(db, call_id)
    note = db.query(Note).filter(Note.call_id == call.id, Note.source == "agent").order_by(Note.created_at.desc()).first()
    if note is None:
        note = Note(call_id=call.id, customer_id=call.customer_id, body=payload.body, source="agent")
        db.add(note)
    else:
        note.body = payload.body
        note.updated_at = _utcnow()
    db.commit()
    db.refresh(note)
    return {"success": True, "message": "Note saved", "data": {"id": str(note.id), "updated_at": note.updated_at.isoformat()}}


@router.post("/calls/{call_id}/transcripts", status_code=status.HTTP_201_CREATED)
def persist_transcripts(call_id: str, payload: TranscriptBatch, db: Session = Depends(get_db)) -> dict[str, Any]:
    call = _get_call(db, call_id)
    inserted = 0
    for segment in payload.segments:
        if segment.segment_id and db.query(Transcript).filter(Transcript.segment_id == segment.segment_id).first():
            continue
        db.add(Transcript(call_id=call.id, speaker=segment.speaker, text=segment.text, timestamp=segment.timestamp or _utcnow(), confidence=segment.confidence, segment_id=segment.segment_id, sequence_number=segment.sequence_number, start_seconds=segment.start_seconds, end_seconds=segment.end_seconds, language=segment.language, is_final=True))
        inserted += 1

    if call.started_at is None:
        call.started_at = _utcnow()
    db.commit()
    return {"success": True, "message": "Transcript segments persisted", "data": {"inserted": inserted}}


def _derive_live_signals(result: dict[str, Any]) -> tuple[list[str], list[str], str, int]:
    intent = str(result.get("intent") or "unknown")
    sentiment = str(result.get("sentiment") or "unknown")
    buying = [intent] if intent in {"interested", "eligibility", "pricing", "kyc"} else []
    objections = [str(result.get("latest_transcript", ""))] if intent == "objection" else []
    guardrail = result.get("guardrail") or {}
    risk = "high" if not guardrail.get("is_safe", True) else "medium" if sentiment in {"negative", "frustrated"} else "low"
    base = 20 + {"interested": 35, "eligibility": 20, "pricing": 15, "kyc": 10, "product_inquiry": 10}.get(intent, 0)
    if sentiment == "positive":
        base += 10
    elif sentiment in {"negative", "frustrated"}:
        base -= 10
    return buying, objections, risk, max(0, min(100, base))


@router.post("/calls/{call_id}/copilot-results", status_code=status.HTTP_201_CREATED)
def persist_copilot_result(call_id: str, payload: CopilotResultInput, db: Session = Depends(get_db)) -> dict[str, Any]:
    call = _get_call(db, call_id)
    result = payload.result
    sequence = int(result.get("sequence_number", 0))
    existing = db.query(CallInsight).filter(CallInsight.call_id == call.id, CallInsight.sequence_number == sequence).first()
    if existing:
        return {"success": True, "message": "Copilot result already persisted", "data": {"id": str(existing.id), "duplicate": True}}
    buying, objections, risk, score = _derive_live_signals(result)
    next_action = result.get("next_best_action") or {}
    guardrail = result.get("guardrail") or {}
    insight = CallInsight(call_id=call.id, sequence_number=sequence, intent=result.get("intent"), sentiment=result.get("sentiment"), lead_score=score, risk_level=risk, buying_signals=buying, objections=objections, next_action=next_action.get("action"), compliance_safe=guardrail.get("is_safe"), confidence=result.get("confidence"), payload=result)
    db.add(insight)
    db.flush()
    suggestion = result.get("suggested_response") or {}
    if suggestion.get("text"):
        db.add(AISuggestion(call_id=call.id, insight_id=insight.id, text=suggestion["text"], action=next_action.get("action"), citations=suggestion.get("citation_chunk_ids") or [], confidence=suggestion.get("confidence")))
        call.ai_suggestion_count = (call.ai_suggestion_count or 0) + 1
    customer = call.customer
    customer.current_intent = result.get("intent")
    customer.current_sentiment = result.get("sentiment")
    customer.risk_level = risk
    customer.lead_score = score
    customer.buying_signals = list(dict.fromkeys([*(customer.buying_signals or []), *buying]))
    customer.objections = list(dict.fromkeys([*(customer.objections or []), *objections]))
    call.primary_intent = result.get("intent")
    call.final_sentiment = result.get("sentiment")
    call.compliance_status = "safe" if guardrail.get("is_safe") else "review_required"
    call.compliance_score = float(guardrail.get("grounding_coverage", 0.0)) * 100
    call.live_summary = result.get("latest_transcript")
    db.commit()
    return {"success": True, "message": "Copilot result persisted", "data": {"id": str(insight.id), "duplicate": False}}


@router.post("/calls/{call_id}/crm-summary")
def persist_crm_summary(call_id: str, payload: CRMSummaryInput, db: Session = Depends(get_db)) -> dict[str, Any]:
    call = _get_call(db, call_id)
    summary = payload.crm_summary
    call.summary = summary.get("call_summary")
    call.live_summary = summary.get("call_summary")
    call.status = "completed"
    call.ended_at = _utcnow()
    call.duration_seconds = _call_duration(call)
    call.outcome = summary.get("lead_status")
    score_data = summary.get("lead_score") or {}
    score = int(score_data.get("score", call.customer.lead_score or 0))
    call.customer.lead_score = score
    call.customer.stage = str(summary.get("lead_status") or call.customer.stage)
    lead = db.query(Lead).filter(Lead.customer_id == call.customer_id, Lead.status == "open").order_by(Lead.created_at.desc()).first()
    if lead is None:
        lead = Lead(customer_id=call.customer_id)
        db.add(lead)
    lead.score = score
    lead.stage = call.customer.stage
    if summary.get("call_summary"):
        db.add(Note(customer_id=call.customer_id, call_id=call.id, body=summary["call_summary"], source="ai_summary"))
    follow_up_date = summary.get("follow_up_date")
    follow_up_id = None
    if follow_up_date:
        try:
            scheduled = dt.datetime.fromisoformat(str(follow_up_date))
        except ValueError:
            scheduled = dt.datetime.combine(dt.date.fromisoformat(str(follow_up_date)), dt.time(hour=9))
        existing = db.query(FollowUp).filter(FollowUp.call_id == call.id, FollowUp.status.in_(["pending", "scheduled"])).first()
        if existing is None:
            existing = FollowUp(call_id=call.id, customer_id=call.customer_id, scheduled_at=scheduled, reminder_at=scheduled - dt.timedelta(hours=1), title="AI-recommended customer follow-up", description=summary.get("customer_concern"), status="scheduled", priority="high" if score >= 70 else "normal")
            db.add(existing)
        db.flush()
        follow_up_id = str(existing.id)
        task = db.query(Task).filter(Task.call_id == call.id, Task.title == "Complete customer follow-up").first()
        if task is None:
            db.add(Task(customer_id=call.customer_id, call_id=call.id, title="Complete customer follow-up", description=summary.get("customer_concern"), status="upcoming", priority=existing.priority, due_at=scheduled))
    db.commit()
    return {"success": True, "message": "CRM summary persisted", "data": {"call_id": call_id, "lead_score": score, "follow_up_id": follow_up_id}}


@router.post("/calls/{call_id}/suggestions/{suggestion_id}/usage")
def record_suggestion_usage(call_id: str, suggestion_id: str, accepted: bool, db: Session = Depends(get_db)) -> dict[str, Any]:
    call = _get_call(db, call_id)
    suggestion = db.get(AISuggestion, _uuid(suggestion_id, "suggestion"))
    if suggestion is None or suggestion.call_id != call.id:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    if suggestion.accepted is not True and accepted:
        call.ai_suggestion_used_count = (call.ai_suggestion_used_count or 0) + 1
    suggestion.accepted = accepted
    db.commit()
    return {"success": True, "message": "Suggestion usage recorded", "data": {"accepted": accepted}}


@router.post("/calls/{call_id}/complete-sale", status_code=status.HTTP_201_CREATED)
def complete_sale(call_id: str, payload: CompleteSaleInput, db: Session = Depends(get_db)) -> dict[str, Any]:
    call = _get_call(db, call_id)
    existing = db.query(Purchase).filter(Purchase.call_id == call.id).first()
    if existing is not None:
        if existing.product_name != payload.product_name or existing.currency != payload.currency or abs(existing.amount - payload.amount) > 0.001:
            raise HTTPException(status_code=409, detail="This call already has a different completed sale")
        return {"success": True, "message": "Sale already completed", "data": {"purchase_id": str(existing.id), "call_id": call_id, "revenue": call.revenue}}
    now = _utcnow()
    purchase = Purchase(customer_id=call.customer_id, call_id=call.id, product_name=payload.product_name, amount=payload.amount, currency=payload.currency, purchased_at=now, status="completed")
    db.add(purchase)
    if payload.offer_name:
        db.add(CustomerOffer(customer_id=call.customer_id, offer_name=payload.offer_name, status="accepted", presented_at=now, accepted_at=now))
    call.status = "completed"
    call.outcome = "converted"
    call.revenue = payload.amount
    if payload.summary:
        call.summary = payload.summary
        db.add(Note(customer_id=call.customer_id, call_id=call.id, body=payload.summary, source="agent_wrap_up"))
    call.ended_at = call.ended_at or now
    call.duration_seconds = _call_duration(call)
    call.customer.stage = "converted"
    lead = db.query(Lead).filter(Lead.customer_id == call.customer_id, Lead.status == "open").order_by(Lead.created_at.desc()).first()
    if lead:
        lead.stage = "converted"
        lead.status = "won"
        lead.estimated_value = payload.amount
    db.add(Notification(kind="sale_completed", title=f"Sale completed for {call.customer.name}", body=f"{payload.product_name} · {payload.currency} {payload.amount:.2f}", related_type="call", related_id=call.id))
    db.commit()
    db.refresh(purchase)
    return {"success": True, "message": "Sale completed", "data": {"purchase_id": str(purchase.id), "call_id": call_id, "revenue": call.revenue}}


@router.patch("/transcripts/{transcript_id}/bookmark")
def bookmark_transcript(transcript_id: str, bookmarked: bool, db: Session = Depends(get_db)) -> dict[str, Any]:
    item = db.query(Transcript).filter(Transcript.segment_id == transcript_id).first()
    if item is None:
        try:
            item = db.get(Transcript, _uuid(transcript_id, "transcript"))
        except HTTPException:
            item = None
    if item is None:
        raise HTTPException(status_code=404, detail="Transcript segment not found")
    item.bookmarked = bookmarked
    db.commit()
    return {"success": True, "message": "Bookmark updated", "data": {"bookmarked": bookmarked}}


@router.get("/follow-ups")
def list_follow_ups(follow_up_status: str | None = Query(default=None, alias="status"), db: Session = Depends(get_db)) -> dict[str, Any]:
    query = db.query(FollowUp)
    if follow_up_status:
        query = query.filter(FollowUp.status == follow_up_status)
    rows = query.order_by(FollowUp.scheduled_at.asc()).all()
    return {"success": True, "message": "Follow-ups retrieved", "data": [_serialize_follow_up(item) for item in rows]}


@router.post("/follow-ups", status_code=status.HTTP_201_CREATED)
def create_follow_up(payload: FollowUpCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    call = _get_call(db, payload.call_id)
    customer = _get_customer(db, payload.customer_id)
    if call.customer_id != customer.id:
        raise HTTPException(status_code=409, detail="Call does not belong to customer")
    item = FollowUp(call_id=call.id, customer_id=customer.id, scheduled_at=payload.scheduled_at, title=payload.title, description=payload.description, channel=payload.channel, priority=payload.priority, reminder_at=payload.reminder_at, status="scheduled")
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"success": True, "message": "Follow-up created", "data": _serialize_follow_up(item)}


@router.patch("/follow-ups/{follow_up_id}")
def update_follow_up(follow_up_id: str, payload: FollowUpUpdate, db: Session = Depends(get_db)) -> dict[str, Any]:
    item = db.get(FollowUp, _uuid(follow_up_id, "follow-up"))
    if item is None:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    if item.status == "completed" and item.completed_at is None:
        item.completed_at = _utcnow()
    db.commit()
    db.refresh(item)
    return {"success": True, "message": "Follow-up updated", "data": _serialize_follow_up(item)}


@router.get("/tasks")
def list_tasks(task_status: str | None = Query(default=None, alias="status"), db: Session = Depends(get_db)) -> dict[str, Any]:
    query = db.query(Task)
    if task_status:
        query = query.filter(Task.status == task_status)
    rows = query.order_by(Task.due_at.asc().nullslast(), Task.created_at.desc()).all()
    return {"success": True, "message": "Tasks retrieved", "data": [_serialize_task(item) for item in rows]}


@router.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    customer_id = _uuid(payload.customer_id, "customer") if payload.customer_id else None
    call_id = _uuid(payload.call_id, "call") if payload.call_id else None
    item = Task(customer_id=customer_id, call_id=call_id, title=payload.title, description=payload.description, priority=payload.priority, due_at=payload.due_at, status="upcoming")
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"success": True, "message": "Task created", "data": _serialize_task(item)}


@router.patch("/tasks/{task_id}")
def update_task(task_id: str, payload: TaskUpdate, db: Session = Depends(get_db)) -> dict[str, Any]:
    item = db.get(Task, _uuid(task_id, "task"))
    if item is None:
        raise HTTPException(status_code=404, detail="Task not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    if item.status == "completed" and item.completed_at is None:
        item.completed_at = _utcnow()
    db.commit()
    db.refresh(item)
    return {"success": True, "message": "Task updated", "data": _serialize_task(item)}


@router.get("/products")
def list_products(active_only: bool = True, db: Session = Depends(get_db)) -> dict[str, Any]:
    query = db.query(ProductOffer)
    if active_only:
        query = query.filter(ProductOffer.is_active.is_(True))
    rows = query.order_by(ProductOffer.name).all()
    return {"success": True, "message": "Products retrieved", "data": [{"id": str(item.id), "name": item.name, "type": item.type, "terms": item.terms, "interest_rate": item.interest_rate, "tenure_months": item.tenure_months, "is_active": item.is_active, "updated_at": item.updated_at.isoformat() if item.updated_at else None} for item in rows]}


@router.get("/internal/products", dependencies=[Depends(_require_internal_key)])
def internal_products(db: Session = Depends(get_db)) -> dict[str, Any]:
    rows = db.query(ProductOffer).filter(ProductOffer.is_active.is_(True)).order_by(ProductOffer.name).all()
    return {"success": True, "message": "Approved products retrieved", "data": [{"id": str(item.id), "name": item.name, "type": item.type, "terms": item.terms, "interest_rate": item.interest_rate, "tenure_months": item.tenure_months, "updated_at": item.updated_at.isoformat() if item.updated_at else None} for item in rows]}


@router.get("/knowledge-documents")
def list_knowledge_documents(db: Session = Depends(get_db)) -> dict[str, Any]:
    rows = db.query(KnowledgeDocument).order_by(KnowledgeDocument.updated_at.desc()).all()
    return {"success": True, "message": "Knowledge documents retrieved", "data": [{"id": str(item.id), "title": item.title, "source": item.source, "version": item.version, "category": item.category, "chunk_count": item.chunk_count, "status": item.status, "indexed_at": item.indexed_at.isoformat()} for item in rows]}


@router.post("/knowledge-documents", status_code=status.HTTP_201_CREATED)
def register_knowledge_document(title: str, source: str, chunk_count: int = 0, version: str | None = None, category: str | None = None, content_sha256: str | None = None, db: Session = Depends(get_db), _: None = Depends(_require_internal_key)) -> dict[str, Any]:
    digest = content_sha256 or hashlib.sha256(f"{source}:{version or ''}".encode()).hexdigest()
    item = db.query(KnowledgeDocument).filter(KnowledgeDocument.content_sha256 == digest).first()
    if item is None:
        item = KnowledgeDocument(title=title, source=source, version=version, category=category, content_sha256=digest, chunk_count=chunk_count)
        db.add(item)
    else:
        item.title = title
        item.source = source
        item.version = version
        item.category = category
        item.chunk_count = chunk_count
        item.updated_at = _utcnow()
    db.commit()
    db.refresh(item)
    return {"success": True, "message": "Knowledge document registered", "data": {"id": str(item.id)}}


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)) -> dict[str, Any]:
    now = _utcnow()
    today = now.date()
    calls = db.query(Call).all()
    today_calls = [item for item in calls if item.created_at and item.created_at.date() == today]
    completed = [item for item in calls if item.status == "completed"]
    converted = [item for item in completed if str(item.outcome or "").casefold() in {"converted", "application_ready", "interested"}]
    durations = [_call_duration(item) for item in completed if _call_duration(item) > 0]
    pending_follow_ups = db.query(FollowUp).filter(FollowUp.status.in_(["pending", "scheduled"])).count()
    revenue = sum(float(item.revenue or 0) for item in completed)
    satisfaction = [float(item.satisfaction_score) for item in completed if item.satisfaction_score is not None]
    suggestion_total = sum(int(item.ai_suggestion_count or 0) for item in calls)
    suggestion_used = sum(int(item.ai_suggestion_used_count or 0) for item in calls)
    stages = Counter(item.stage for item in db.query(Lead).all())
    recent = sorted(calls, key=lambda item: item.updated_at or dt.datetime.min, reverse=True)[:10]
    return {"success": True, "message": "Dashboard metrics retrieved", "data": {"metrics": {"today_calls": len(today_calls), "active_calls": sum(item.status == "active" for item in calls), "conversion_rate": round(len(converted) / len(completed) * 100, 2) if completed else 0.0, "average_duration_seconds": round(sum(durations) / len(durations), 2) if durations else 0.0, "pending_follow_ups": pending_follow_ups, "revenue": round(revenue, 2), "customer_satisfaction": round(sum(satisfaction) / len(satisfaction), 2) if satisfaction else None, "ai_suggestion_usage_rate": round(suggestion_used / suggestion_total * 100, 2) if suggestion_total else 0.0, "ai_suggestions": suggestion_total}, "lead_funnel": [{"stage": stage, "count": count} for stage, count in sorted(stages.items())], "recent_activity": [{"call_id": str(item.id), "customer_id": str(item.customer_id), "customer_name": item.customer.name if item.customer else None, "status": item.status, "outcome": item.outcome, "updated_at": item.updated_at.isoformat() if item.updated_at else None} for item in recent], "upcoming_follow_ups": [_serialize_follow_up(item) for item in db.query(FollowUp).filter(FollowUp.status.in_(["pending", "scheduled"]), FollowUp.scheduled_at >= now).order_by(FollowUp.scheduled_at.asc()).limit(10).all()]}}


@router.get("/analytics")
def analytics(days: int = Query(default=30, ge=1, le=365), db: Session = Depends(get_db)) -> dict[str, Any]:
    since = _utcnow() - dt.timedelta(days=days)
    calls = db.query(Call).filter(Call.created_at >= since).all()
    insights = db.query(CallInsight).filter(CallInsight.created_at >= since).all()
    daily: dict[str, dict[str, int]] = defaultdict(lambda: {"inbound": 0, "outbound": 0, "total": 0})
    for call in calls:
        key = call.created_at.date().isoformat()
        daily[key][call.direction if call.direction in {"inbound", "outbound"} else "inbound"] += 1
        daily[key]["total"] += 1
    intent = Counter(item.intent or "unknown" for item in insights)
    sentiment = Counter(item.sentiment or "unknown" for item in insights)
    durations = [_call_duration(item) for item in calls if _call_duration(item) > 0]
    agent_stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"calls": 0, "conversions": 0, "score_total": 0.0, "score_count": 0})
    for call in calls:
        name = call.agent_session.agent_name if call.agent_session else "Unassigned"
        row = agent_stats[name]
        row["calls"] += 1
        row["conversions"] += str(call.outcome or "").casefold() in {"converted", "application_ready", "interested"}
        if call.agent_score is not None:
            row["score_total"] += call.agent_score
            row["score_count"] += 1
    return {"success": True, "message": "Analytics retrieved", "data": {"period_days": days, "call_volume": [{"date": day, **values} for day, values in sorted(daily.items())], "intent_distribution": [{"name": key, "value": value} for key, value in intent.most_common()], "sentiment_distribution": [{"name": key, "value": value} for key, value in sentiment.most_common()], "call_duration": {"average_seconds": round(sum(durations) / len(durations), 2) if durations else 0.0, "minimum_seconds": min(durations) if durations else 0, "maximum_seconds": max(durations) if durations else 0}, "lead_funnel": [{"stage": key, "value": value} for key, value in Counter(item.stage for item in db.query(Lead).all()).most_common()], "agent_performance": [{"agent": name, "calls": values["calls"], "conversion_rate": round(values["conversions"] / values["calls"] * 100, 2) if values["calls"] else 0.0, "average_score": round(values["score_total"] / values["score_count"], 2) if values["score_count"] else None} for name, values in agent_stats.items()]}}


@router.get("/notifications")
def list_notifications(db: Session = Depends(get_db)) -> dict[str, Any]:
    rows = db.query(Notification).order_by(Notification.created_at.desc()).limit(100).all()
    return {"success": True, "message": "Notifications retrieved", "data": [{"id": str(item.id), "kind": item.kind, "title": item.title, "body": item.body, "related_type": item.related_type, "related_id": str(item.related_id) if item.related_id else None, "read_at": item.read_at.isoformat() if item.read_at else None, "created_at": item.created_at.isoformat()} for item in rows]}


@router.patch("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    item = db.get(Notification, _uuid(notification_id, "notification"))
    if item is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    if item.read_at is None:
        item.read_at = _utcnow()
        db.commit()
    return {"success": True, "message": "Notification marked read", "data": {"id": notification_id, "read_at": item.read_at.isoformat()}}


@router.post("/internal/calls/{call_id}/session", dependencies=[Depends(_require_internal_key)])
def link_ai_session(call_id: str, payload: SessionLink, db: Session = Depends(get_db)) -> dict[str, Any]:
    call = _get_call(db, call_id)
    call.ai_session_id = payload.ai_session_id
    if call.started_at is None:
        call.started_at = _utcnow()
    call.status = "active"
    db.commit()
    return {"success": True, "message": "AI session linked", "data": {"call_id": call_id}}


@router.get("/internal/calls/{call_id}/context", dependencies=[Depends(_require_internal_key)])
def get_ai_session_context(call_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    call = _get_call(db, call_id)
    transcripts = sorted(call.transcripts, key=lambda item: (item.sequence_number, item.timestamp or dt.datetime.min))
    insights = sorted(call.insights, key=lambda item: item.sequence_number)
    return {
        "success": True,
        "message": "AI session context retrieved",
        "data": {
            "call_id": call_id,
            "customer": {
                "name": call.customer.name,
                "occupation": call.customer.occupation,
                "city": call.customer.city,
                "current_intent": call.customer.current_intent,
                "current_sentiment": call.customer.current_sentiment,
            },
            "transcripts": [_serialize_transcript(item) for item in transcripts[-100:]],
            "last_result": insights[-1].payload if insights else None,
        },
    }


@router.post("/internal/calls/{call_id}/transcripts", dependencies=[Depends(_require_internal_key)])
def internal_persist_transcripts(call_id: str, payload: TranscriptBatch, db: Session = Depends(get_db)) -> dict[str, Any]:
    return persist_transcripts(call_id, payload, db)


@router.post("/internal/calls/{call_id}/copilot-results", dependencies=[Depends(_require_internal_key)])
def internal_persist_copilot(call_id: str, payload: CopilotResultInput, db: Session = Depends(get_db)) -> dict[str, Any]:
    return persist_copilot_result(call_id, payload, db)


@router.post("/internal/calls/{call_id}/crm-summary", dependencies=[Depends(_require_internal_key)])
def internal_persist_crm(call_id: str, payload: CRMSummaryInput, db: Session = Depends(get_db)) -> dict[str, Any]:
    return persist_crm_summary(call_id, payload, db)


__all__ = ["router", "_serialize_customer"]
