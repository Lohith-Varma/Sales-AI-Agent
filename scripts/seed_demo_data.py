"""Seed realistic demonstration data into the Sales AI SQLite database without changing application logic."""

import sys
import os
import uuid
import datetime

# Add project root and backend path
sys.path.insert(0, os.path.abspath("backend"))
sys.path.insert(0, os.path.abspath("."))

from app.db.database import engine, Base, SessionLocal
from app.db.base import (
    Customer,
    Call,
    Transcript,
    Lead,
    Purchase,
    ProductOffer,
    CustomerOffer,
    KYCDoc,
    FollowUp,
    ConsentLog,
    Note,
    Task,
    Notification,
    User,
    AgentSession,
)

def seed_database():
    print("=== Seeding Demo Data into Sales AI Database ===")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 1. Ensure Agent User
        user = db.query(User).filter(User.email == "demo@salescopilot.ai").first()
        if not user:
            user = User(
                id=uuid.uuid4(),
                email="demo@salescopilot.ai",
                display_name="Sarah Connor",
                password_hash="pbkdf2:sha256:1000$demo$hash",
                role="agent",
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # 2. Agent Session
        session = db.query(AgentSession).first()
        if not session:
            session = AgentSession(
                id=uuid.uuid4(),
                agent_name="Sarah Connor",
                status="active",
                websocket_connected=True,
            )
            db.add(session)
            db.commit()
            db.refresh(session)

        # 3. Product Offers
        offers_data = [
            {
                "name": "Pay-in-3 Zero Cost Plan",
                "type": "pay_in_3",
                "terms": "0% interest, 3 equal monthly installments. No hidden fees, instant approval for monthly salary > ₹45,000.",
                "interest_rate": 0.0,
                "tenure_months": 3,
            },
            {
                "name": "Pay-in-6 Low APR Flexi Plan",
                "type": "zero_cost_emi",
                "terms": "6% annual interest rate over 6 monthly payments. Minimal documentation required.",
                "interest_rate": 6.0,
                "tenure_months": 6,
            },
            {
                "name": "Pay-in-12 Festival Special EMI",
                "type": "pay_in_12",
                "terms": "Zero processing fee, 12 month payment schedule for major electronics and high value purchases.",
                "interest_rate": 8.5,
                "tenure_months": 12,
            },
        ]
        created_offers = []
        for o in offers_data:
            offer = db.query(ProductOffer).filter(ProductOffer.name == o["name"]).first()
            if not offer:
                offer = ProductOffer(
                    id=uuid.uuid4(),
                    name=o["name"],
                    type=o["type"],
                    terms=o["terms"],
                    interest_rate=o["interest_rate"],
                    tenure_months=o["tenure_months"],
                    is_active=True,
                )
                db.add(offer)
                db.commit()
                db.refresh(offer)
            created_offers.append(offer)

        # 4. Demo Customers
        customers_data = [
            {
                "name": "Priya Sharma",
                "phone_number": "+919876543210",
                "email": "priya.sharma@techcorp.in",
                "occupation": "Staff Software Engineer",
                "city": "Bengaluru",
                "location": "Indiranagar, Bengaluru",
                "lead_score": 92,
                "stage": "qualified",
                "kyc_status": "verified",
                "tags": ["high-value", "pay-in-3-eligible", "tech-worker"],
                "current_intent": "pricing",
                "current_sentiment": "positive",
                "risk_level": "low",
                "buying_signals": ["Inquired about 0% interest", "Ready to upload PAN", "Requested immediate approval"],
                "objections": [],
            },
            {
                "name": "Rahul Verma",
                "phone_number": "+919812345678",
                "email": "rahul.verma@designstudio.com",
                "occupation": "Senior UI/UX Designer",
                "city": "Mumbai",
                "location": "Bandra West, Mumbai",
                "lead_score": 78,
                "stage": "contacted",
                "kyc_status": "pending",
                "tags": ["design-lead", "kyc-pending"],
                "current_intent": "kyc",
                "current_sentiment": "neutral",
                "risk_level": "low",
                "buying_signals": ["Asking about document verification timeline"],
                "objections": ["Worried about security of uploaded PAN card"],
            },
            {
                "name": "Ananya Patel",
                "phone_number": "+919988776655",
                "email": "ananya.patel@fintech.io",
                "occupation": "Product Director",
                "city": "Delhi NCR",
                "location": "DLF Phase 5, Gurgaon",
                "lead_score": 95,
                "stage": "negotiation",
                "kyc_status": "verified",
                "tags": ["vip", "pre-approved", "high-income"],
                "current_intent": "eligibility",
                "current_sentiment": "positive",
                "risk_level": "low",
                "buying_signals": ["Wants ₹1,50,000 credit line", "Asking for 12-month zero cost EMI"],
                "objections": [],
            },
            {
                "name": "Vikram Singh",
                "phone_number": "+919765432109",
                "email": "vikram.singh@cloudops.org",
                "occupation": "DevOps Architect",
                "city": "Hyderabad",
                "location": "Gachibowli, Hyderabad",
                "lead_score": 84,
                "stage": "converted",
                "kyc_status": "verified",
                "tags": ["existing-customer", "pay-in-3-active"],
                "current_intent": "interested",
                "current_sentiment": "positive",
                "risk_level": "low",
                "buying_signals": ["Completed first Pay-in-3 installment early"],
                "objections": [],
            },
            {
                "name": "Sneha Reddy",
                "phone_number": "+919654321098",
                "email": "sneha.reddy@marketinghub.com",
                "occupation": "Marketing Director",
                "city": "Chennai",
                "location": "Adyar, Chennai",
                "lead_score": 70,
                "stage": "new",
                "kyc_status": "pending",
                "tags": ["inbound-inquiry"],
                "current_intent": "product_inquiry",
                "current_sentiment": "neutral",
                "risk_level": "medium",
                "buying_signals": ["Visited pricing page 4 times"],
                "objections": ["Asked if there is an annual maintenance charge"],
            },
        ]

        created_customers = []
        for c in customers_data:
            customer = db.query(Customer).filter(Customer.phone_number == c["phone_number"]).first()
            if not customer:
                customer = Customer(
                    id=uuid.uuid4(),
                    name=c["name"],
                    phone_number=c["phone_number"],
                    email=c["email"],
                    occupation=c["occupation"],
                    city=c["city"],
                    location=c["location"],
                    lead_score=c["lead_score"],
                    stage=c["stage"],
                    kyc_status=c["kyc_status"],
                    tags=c["tags"],
                    current_intent=c["current_intent"],
                    current_sentiment=c["current_sentiment"],
                    risk_level=c["risk_level"],
                    buying_signals=c["buying_signals"],
                    objections=c["objections"],
                )
                db.add(customer)
                db.commit()
                db.refresh(customer)
            created_customers.append(customer)

        priya, rahul, ananya, vikram, sneha = created_customers

        # 5. KYC Documents
        if not db.query(KYCDoc).filter(KYCDoc.customer_id == priya.id).first():
            db.add(KYCDoc(id=uuid.uuid4(), customer_id=priya.id, doc_type="PAN", doc_status="verified"))
            db.add(KYCDoc(id=uuid.uuid4(), customer_id=priya.id, doc_type="Aadhaar", doc_status="verified"))
        if not db.query(KYCDoc).filter(KYCDoc.customer_id == rahul.id).first():
            db.add(KYCDoc(id=uuid.uuid4(), customer_id=rahul.id, doc_type="PAN", doc_status="pending"))
        if not db.query(KYCDoc).filter(KYCDoc.customer_id == ananya.id).first():
            db.add(KYCDoc(id=uuid.uuid4(), customer_id=ananya.id, doc_type="PAN", doc_status="verified"))
            db.add(KYCDoc(id=uuid.uuid4(), customer_id=ananya.id, doc_type="Passport", doc_status="verified"))
        db.commit()

        # 6. Calls & Transcripts
        now = datetime.datetime.utcnow()

        # Call 1: Priya Sharma (Completed)
        call_priya = db.query(Call).filter(Call.customer_id == priya.id).first()
        if not call_priya:
            call_priya = Call(
                id=uuid.uuid4(),
                customer_id=priya.id,
                agent_session_id=session.id,
                status="completed",
                direction="inbound",
                started_at=now - datetime.timedelta(hours=2, minutes=15),
                ended_at=now - datetime.timedelta(hours=2),
                duration_seconds=900,
                summary="Customer inquired about zero-cost Pay-in-3 for high-end laptop purchase (₹45,000). Confirmed salary meets eligibility threshold of ₹45,000/mo. Grounded AI recommendation accepted.",
                outcome="interested",
                primary_intent="eligibility",
                final_sentiment="positive",
                compliance_status="safe",
                compliance_score=0.98,
                agent_score=0.95,
                satisfaction_score=4.9,
                revenue=45000.0,
                ai_suggestion_count=4,
                ai_suggestion_used_count=4,
            )
            db.add(call_priya)
            db.commit()
            db.refresh(call_priya)

            # Transcripts for Priya
            transcripts_priya = [
                ("customer", "Hi, I want to buy a MacBook Pro for ₹45,000 and use Pay-in-3. Are there any interest charges?"),
                ("agent", "Hello Priya! Pay-in-3 is completely zero cost with 0% interest when split into 3 monthly installments of ₹15,000."),
                ("customer", "That sounds great! Is there any processing fee or annual charge?"),
                ("agent", "No processing fee or hidden charges. We just verify your monthly income and PAN for instant setup."),
                ("customer", "Perfect, I have uploaded my PAN card. Let's proceed!"),
            ]
            for idx, (spk, txt) in enumerate(transcripts_priya, 1):
                db.add(Transcript(
                    id=uuid.uuid4(),
                    call_id=call_priya.id,
                    speaker=spk,
                    text=txt,
                    timestamp=now - datetime.timedelta(hours=2, minutes=15 - idx),
                    confidence=0.96,
                    sequence_number=idx,
                ))

        # Call 2: Ananya Patel (Completed)
        call_ananya = db.query(Call).filter(Call.customer_id == ananya.id).first()
        if not call_ananya:
            call_ananya = Call(
                id=uuid.uuid4(),
                customer_id=ananya.id,
                agent_session_id=session.id,
                status="completed",
                direction="outbound",
                started_at=now - datetime.timedelta(hours=5),
                ended_at=now - datetime.timedelta(hours=4, minutes=40),
                duration_seconds=1200,
                summary="Discussed ₹1,50,000 credit line approval for home workstation setup. Recommended 12-month zero-cost EMI special offer.",
                outcome="converted",
                primary_intent="pricing",
                final_sentiment="positive",
                compliance_status="safe",
                compliance_score=1.0,
                agent_score=0.98,
                satisfaction_score=5.0,
                revenue=150000.0,
                ai_suggestion_count=6,
                ai_suggestion_used_count=5,
            )
            db.add(call_ananya)
            db.commit()

        # Call 3: Rahul Verma (Completed)
        call_rahul = db.query(Call).filter(Call.customer_id == rahul.id).first()
        if not call_rahul:
            call_rahul = Call(
                id=uuid.uuid4(),
                customer_id=rahul.id,
                agent_session_id=session.id,
                status="completed",
                direction="inbound",
                started_at=now - datetime.timedelta(days=1, hours=3),
                ended_at=now - datetime.timedelta(days=1, hours=2, minutes=45),
                duration_seconds=900,
                summary="Explained DPDP-compliant data security for PAN verification. Customer scheduled follow-up after salary receipt.",
                outcome="follow_up_scheduled",
                primary_intent="kyc",
                final_sentiment="neutral",
                compliance_status="safe",
                compliance_score=0.95,
                agent_score=0.90,
                satisfaction_score=4.5,
                revenue=28000.0,
                ai_suggestion_count=3,
                ai_suggestion_used_count=3,
            )
            db.add(call_rahul)
            db.commit()

        # 7. Leads
        if not db.query(Lead).filter(Lead.customer_id == priya.id).first():
            db.add(Lead(id=uuid.uuid4(), customer_id=priya.id, owner_user_id=user.id, source="inbound_call", stage="qualified", status="open", score=92, estimated_value=45000.0))
        if not db.query(Lead).filter(Lead.customer_id == ananya.id).first():
            db.add(Lead(id=uuid.uuid4(), customer_id=ananya.id, owner_user_id=user.id, source="website_lead", stage="negotiation", status="open", score=95, estimated_value=150000.0))
        if not db.query(Lead).filter(Lead.customer_id == rahul.id).first():
            db.add(Lead(id=uuid.uuid4(), customer_id=rahul.id, owner_user_id=user.id, source="inbound_call", stage="contacted", status="open", score=78, estimated_value=28000.0))
        if not db.query(Lead).filter(Lead.customer_id == vikram.id).first():
            db.add(Lead(id=uuid.uuid4(), customer_id=vikram.id, owner_user_id=user.id, source="referral", stage="converted", status="won", score=84, estimated_value=60000.0))
        db.commit()

        # 8. Purchases
        if not db.query(Purchase).filter(Purchase.customer_id == vikram.id).first():
            db.add(Purchase(id=uuid.uuid4(), customer_id=vikram.id, product_name="Pay-in-3 Smart TV Purchase", amount=60000.0, currency="INR", status="completed"))
        if not db.query(Purchase).filter(Purchase.customer_id == ananya.id).first():
            db.add(Purchase(id=uuid.uuid4(), customer_id=ananya.id, product_name="Pay-in-12 Workstation EMI", amount=150000.0, currency="INR", status="completed"))
        db.commit()

        # 9. Customer Offers
        if created_offers and not db.query(CustomerOffer).filter(CustomerOffer.customer_id == priya.id).first():
            db.add(CustomerOffer(id=uuid.uuid4(), customer_id=priya.id, product_offer_id=created_offers[0].id, offer_name="Pay-in-3 Zero Cost Plan", status="accepted"))
        if created_offers and not db.query(CustomerOffer).filter(CustomerOffer.customer_id == ananya.id).first():
            db.add(CustomerOffer(id=uuid.uuid4(), customer_id=ananya.id, product_offer_id=created_offers[2].id, offer_name="Pay-in-12 Festival Special EMI", status="accepted"))
        db.commit()

        # 10. Consent Logs
        if call_priya and not db.query(ConsentLog).filter(ConsentLog.customer_id == priya.id).first():
            db.add(ConsentLog(id=uuid.uuid4(), call_id=call_priya.id, customer_id=priya.id, consent_given=True, ip_address="127.0.0.1"))
        if call_ananya and not db.query(ConsentLog).filter(ConsentLog.customer_id == ananya.id).first():
            db.add(ConsentLog(id=uuid.uuid4(), call_id=ananya.id, customer_id=ananya.id, consent_given=True, ip_address="127.0.0.1"))
        db.commit()

        # 11. FollowUps
        if call_rahul and not db.query(FollowUp).filter(FollowUp.customer_id == rahul.id).first():
            db.add(FollowUp(
                id=uuid.uuid4(),
                call_id=call_rahul.id,
                customer_id=rahul.id,
                scheduled_at=now + datetime.timedelta(hours=24),
                status="pending",
                title="PAN verification callback",
                description="Follow up with Rahul regarding completed PAN card upload for ₹28,000 credit limit.",
                channel="phone",
                priority="high",
                assigned_user_id=user.id,
            ))
        if call_priya and not db.query(FollowUp).filter(FollowUp.customer_id == priya.id).first():
            db.add(FollowUp(
                id=uuid.uuid4(),
                call_id=call_priya.id,
                customer_id=priya.id,
                scheduled_at=now + datetime.timedelta(hours=48),
                status="pending",
                title="First installment reminder & feedback",
                description="Check in with Priya after laptop delivery for first Pay-in-3 installment schedule.",
                channel="phone",
                priority="normal",
                assigned_user_id=user.id,
            ))
        db.commit()

        # 12. Tasks
        tasks_data = [
            (priya.id, "Send Pay-in-3 official terms brochure", "Email zero interest 3-month schedule to Priya.", "upcoming", "high", now + datetime.timedelta(hours=4)),
            (rahul.id, "Verify PAN card document status", "Check KYC portal for Rahul's uploaded PAN.", "upcoming", "urgent", now + datetime.timedelta(hours=2)),
            (ananya.id, "Generate ₹1,50,000 credit agreement", "Prepare 12-month EMI agreement document for e-signature.", "completed", "normal", now - datetime.timedelta(hours=1)),
            (sneha.id, "Initial outreach call for Pay-in-3 inquiry", "Contact Sneha regarding website inquiry on pricing page.", "upcoming", "normal", now + datetime.timedelta(hours=6)),
        ]
        for cid, title, desc, st, pri, due in tasks_data:
            if not db.query(Task).filter(Task.customer_id == cid, Task.title == title).first():
                db.add(Task(
                    id=uuid.uuid4(),
                    customer_id=cid,
                    call_id=call_priya.id if cid == priya.id else None,
                    assigned_user_id=user.id,
                    title=title,
                    description=desc,
                    status=st,
                    priority=pri,
                    due_at=due,
                ))
        db.commit()

        # 13. Notes
        notes_data = [
            (priya.id, "Customer is extremely satisfied with zero interest clarity. High probability of recurring Pay-in-3 usage.", "agent"),
            (ananya.id, "Approved for maximum credit limit ₹1,50,000. Customer opted for 12-month installment plan.", "ai_copilot"),
            (rahul.id, "Expressed hesitation about document security. Reassured customer regarding AES-256 encryption & DPDP compliance.", "agent"),
        ]
        for cid, body, src in notes_data:
            if not db.query(Note).filter(Note.customer_id == cid, Note.body == body).first():
                db.add(Note(
                    id=uuid.uuid4(),
                    customer_id=cid,
                    body=body,
                    source=src,
                ))
        db.commit()

        # 14. Notifications
        notifications_data = [
            ("call_summary", "Call Wrap-Up Completed", "Priya Sharma call summary recorded with ₹45,000 revenue attribution."),
            ("kyc_verified", "KYC Verification Success", "Ananya Patel's PAN & Passport documents successfully verified."),
            ("follow_up_due", "Upcoming Callback Due", "Rahul Verma callback scheduled for tomorrow at 2:00 PM."),
        ]
        for kind, title, body in notifications_data:
            if not db.query(Notification).filter(Notification.title == title).first():
                db.add(Notification(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    kind=kind,
                    title=title,
                    body=body,
                ))
        db.commit()

        print("SUCCESS: Demo data seeded successfully!")
        print(f"Loaded {len(created_customers)} Customers, 3 Calls, 3 Product Offers, 4 Leads, 2 Follow-Ups, 4 Tasks!")

    except Exception as exc:
        db.rollback()
        print(f"ERROR Seeding database: {exc}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
