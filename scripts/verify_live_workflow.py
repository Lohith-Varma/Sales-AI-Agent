"""Run the realistic Pay-in-3 workflow against the three local services."""

from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import UTC, datetime

import httpx
import websockets

CORE = os.getenv("QA_CORE_URL", "http://127.0.0.1:8000")
AI = os.getenv("QA_AI_URL", "http://127.0.0.1:8001")
WS = os.getenv("QA_AI_WS_URL", "ws://127.0.0.1:8001/ws/copilot")
TOKEN = os.getenv("QA_ACCESS_TOKEN")


async def request(client: httpx.AsyncClient, method: str, url: str, **kwargs):
    started = time.perf_counter()
    response = await client.request(method, url, **kwargs)
    elapsed_ms = (time.perf_counter() - started) * 1_000
    response.raise_for_status()
    return response.json(), elapsed_ms


async def open_session(call_id: str) -> tuple[websockets.ClientConnection, str, float]:
    started = time.perf_counter()
    socket = await websockets.connect(WS, open_timeout=10, close_timeout=5)
    await socket.send(
        json.dumps(
            {
                "type": "session_start",
                "sales_agent_id": "qa-live-agent",
                "external_lead_id": call_id,
                "language": "en",
                "access_token": TOKEN,
                "audio_config": {
                    "encoding": "pcm_s16le",
                    "sample_rate_hz": 16000,
                    "channels": 1,
                    "sample_width_bytes": 2,
                },
            }
        )
    )
    while True:
        event = json.loads(await asyncio.wait_for(socket.recv(), timeout=15))
        if event["type"] == "error":
            raise AssertionError(event)
        if event["type"] == "session_ready":
            return socket, event["session_id"], (time.perf_counter() - started) * 1_000


async def main() -> None:
    headers = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}
    async with httpx.AsyncClient(headers=headers, timeout=90) as client:
        suffix = str(int(time.time() * 1_000))[-10:]
        customer_payload, create_customer_ms = await request(
            client,
            "POST",
            f"{CORE}/api/customers",
            params={
                "name": f"QA Pay-in-3 Customer {suffix}",
                "phone_number": f"+91{suffix}",
                "email": f"qa-{suffix}@example.test",
                "salary": 60000,
            },
        )
        customer_id = customer_payload["data"]["customer_id"]
        call_payload, create_call_ms = await request(
            client,
            "POST",
            f"{CORE}/api/calls",
            params={"customer_id": customer_id, "direction": "inbound"},
        )
        call_id = call_payload["data"]["call_id"]
        _, consent_ms = await request(
            client,
            "POST",
            f"{CORE}/api/consent",
            params={"call_id": call_id, "consent_given": True},
        )

        socket, session_id, connect_ms = await open_session(call_id)
        ping_started = time.perf_counter()
        await socket.send(json.dumps({"type": "ping", "nonce": "qa-heartbeat"}))
        while True:
            event = json.loads(await asyncio.wait_for(socket.recv(), timeout=10))
            if event.get("type") == "pong":
                break
        heartbeat_ms = (time.perf_counter() - ping_started) * 1_000

        utterances = [
            "I heard about Pay-in-3. Can you tell me if I'm eligible?",
            "What documents do I need?",
            "I'll think about it.",
        ]
        analyses: list[dict] = []
        analysis_latencies: list[float] = []
        for sequence_number, utterance in enumerate(utterances):
            turn, turn_ms = await request(
                client,
                "POST",
                f"{AI}/api/v1/copilot/analyze-text",
                json={
                    "session_id": session_id,
                    "sequence_number": sequence_number,
                    "customer_utterance": utterance,
                },
            )
            analyses.append(turn)
            analysis_latencies.append(turn_ms)

        eligibility, kyc_turn, follow_up = analyses
        assert eligibility["intent"] == "eligibility"
        assert eligibility["retrieved_context"], "Eligibility RAG returned no context"
        assert eligibility["suggested_response"]["citation_chunk_ids"]
        assert not eligibility["suggested_response"]["is_fallback"]
        assert kyc_turn["intent"] == "kyc"
        assert kyc_turn["retrieved_context"], "KYC RAG returned no context"
        assert kyc_turn["suggested_response"]["citation_chunk_ids"]
        assert follow_up["intent"] == "follow_up"
        assert follow_up["next_best_action"]["action"] == "schedule_follow_up"
        assert follow_up["next_best_action"]["requires_confirmation"] is True
        assert all(turn["guardrail"]["is_safe"] for turn in analyses)
        analysis = follow_up

        call_after_ai, db_read_ms = await request(client, "GET", f"{CORE}/api/calls/{call_id}")
        assert len(call_after_ai["data"]["transcripts"]) == 3
        assert len(call_after_ai["data"]["insights"]) == 3
        assert len(call_after_ai["data"]["suggestions"]) == 3
        suggestion_id = call_after_ai["data"]["suggestions"][-1]["id"]
        await request(
            client,
            "POST",
            f"{CORE}/api/calls/{call_id}/suggestions/{suggestion_id}/usage",
            params={"accepted": True},
        )

        await socket.close()
        recovered_socket, recovered_session_id, reconnect_ms = await open_session(call_id)
        crm, crm_ms = await request(
            client,
            "POST",
            f"{AI}/api/v1/copilot/complete",
            json={"session_id": recovered_session_id, "ended_at": datetime.now(UTC).isoformat()},
        )
        await recovered_socket.close()
        assert crm["crm_summary"]["call_summary"]

        kyc, kyc_ms = await request(
            client,
            "POST",
            f"{CORE}/api/customers/{customer_id}/kyc",
            json={"doc_type": "identity_verification", "status": "pending"},
        )
        assert kyc["data"]["status"] == "pending"

        products, products_ms = await request(client, "GET", f"{CORE}/api/products")
        product = next(item for item in products["data"] if item["type"] == "terms")
        sale, sale_ms = await request(
            client,
            "POST",
            f"{CORE}/api/calls/{call_id}/complete-sale",
            json={
                "product_name": product["name"],
                "offer_name": product["name"],
                "amount": 9000,
                "currency": "INR",
                "summary": crm["crm_summary"]["call_summary"],
            },
        )
        assert sale["data"]["revenue"] == 9000
        replay, _ = await request(
            client,
            "POST",
            f"{CORE}/api/calls/{call_id}/complete-sale",
            json={
                "product_name": product["name"],
                "offer_name": product["name"],
                "amount": 9000,
                "currency": "INR",
                "summary": crm["crm_summary"]["call_summary"],
            },
        )
        assert replay["data"]["purchase_id"] == sale["data"]["purchase_id"]

        profile, profile_ms = await request(client, "GET", f"{CORE}/api/customers/{customer_id}")
        calls, calls_ms = await request(client, "GET", f"{CORE}/api/calls", params={"customer_id": customer_id})
        dashboard, dashboard_ms = await request(client, "GET", f"{CORE}/api/dashboard")
        analytics, analytics_ms = await request(client, "GET", f"{CORE}/api/analytics", params={"days": 30})
        follow_ups, follow_up_ms = await request(client, "GET", f"{CORE}/api/follow-ups")
        notifications, notifications_ms = await request(client, "GET", f"{CORE}/api/notifications")

        customer = profile["data"]
        call = calls["data"][0]
        assert customer["name"].startswith("QA Pay-in-3 Customer")
        assert customer["kycStatus"] == "in_progress"
        assert len(customer["previousPurchases"]) == 1
        assert call["status"] == "completed" and call["outcome"] == "converted"
        assert call["revenue"] == 9000
        assert dashboard["data"]["metrics"]["revenue"] >= 9000
        assert analytics["data"]["call_volume"]
        assert any(item["call_id"] == call_id for item in follow_ups["data"]), "Follow-up was not created"
        assert any(item["related_id"] == call_id for item in notifications["data"])

        result = {
            "customer_id": customer_id,
            "call_id": call_id,
            "session_id": session_id,
            "recovered_session_id": recovered_session_id,
            "intent": analysis["intent"],
            "sentiment": analysis["sentiment"],
            "next_action": analysis["next_best_action"]["action"],
            "turns": [
                {
                    "intent": turn["intent"],
                    "sentiment": turn["sentiment"],
                    "retrieved_chunks": len(turn["retrieved_context"]),
                    "next_action": turn["next_best_action"]["action"],
                }
                for turn in analyses
            ],
            "retrieved_chunks": sum(len(turn["retrieved_context"]) for turn in analyses),
            "citations": [
                citation
                for turn in analyses
                for citation in turn["suggested_response"]["citation_chunk_ids"]
            ],
            "lead_score": crm["crm_summary"]["lead_score"]["score"],
            "follow_up_date": crm["crm_summary"]["follow_up_date"],
            "latency_ms": {
                "create_customer_api": round(create_customer_ms, 1),
                "create_call_api": round(create_call_ms, 1),
                "consent_api": round(consent_ms, 1),
                "websocket_connect": round(connect_ms, 1),
                "websocket_heartbeat": round(heartbeat_ms, 1),
                "copilot_analysis_turns": [round(value, 1) for value in analysis_latencies],
                "copilot_analysis_total": round(sum(analysis_latencies), 1),
                "database_call_read": round(db_read_ms, 1),
                "websocket_reconnect_and_recovery": round(reconnect_ms, 1),
                "crm_generation_and_persistence": round(crm_ms, 1),
                "kyc_write": round(kyc_ms, 1),
                "products_read": round(products_ms, 1),
                "sale_transaction": round(sale_ms, 1),
                "profile_read": round(profile_ms, 1),
                "calls_read": round(calls_ms, 1),
                "dashboard_read": round(dashboard_ms, 1),
                "analytics_read": round(analytics_ms, 1),
                "follow_ups_read": round(follow_up_ms, 1),
                "notifications_read": round(notifications_ms, 1),
            },
        }
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
