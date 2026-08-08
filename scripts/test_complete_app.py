"""Complete application verification script."""

import urllib.request
import json
import asyncio
import websockets

def test_http_endpoints():
    print("=== Testing REST API Endpoints ===")
    
    # 1. Core Health
    resp1 = urllib.request.urlopen("http://127.0.0.1:8000/api/health")
    data1 = json.loads(resp1.read().decode())
    assert resp1.status == 200, f"Core health failed: {resp1.status}"
    print(f"[OK] Core Health: status={data1['data']['status']}, env={data1['data']['env']}")

    # 2. AI Health
    resp2 = urllib.request.urlopen("http://127.0.0.1:8000/api/ai/health")
    data2 = json.loads(resp2.read().decode())
    assert resp2.status == 200, f"AI health failed: {resp2.status}"
    print(f"[OK] AI Health: status={data2['status']}, elevenlabs={data2['elevenlabs']}, gemini={data2['gemini']}")

    # 3. AI Readiness
    resp3 = urllib.request.urlopen("http://127.0.0.1:8000/api/ai/ready")
    data3 = json.loads(resp3.read().decode())
    assert resp3.status == 200, f"AI readiness failed: {resp3.status}"
    print(f"[OK] AI Readiness: status={data3['status']}, chroma={data3['dependencies']['chroma']['detail']}")

    # 4. Customers API
    resp4 = urllib.request.urlopen("http://127.0.0.1:8000/api/customers")
    data4 = json.loads(resp4.read().decode())
    assert resp4.status == 200, f"Customers API failed: {resp4.status}"
    print(f"[OK] Customers API: count={len(data4['data']['items'])}")

    # 5. Dashboard API
    resp5 = urllib.request.urlopen("http://127.0.0.1:8000/api/dashboard")
    data5 = json.loads(resp5.read().decode())
    assert resp5.status == 200, f"Dashboard API failed: {resp5.status}"
    print(f"[OK] Dashboard API: revenue=INR {data5['data']['metrics']['revenue']:,.2f}, calls={data5['data']['metrics']['today_calls']}")

    # 6. Frontend App
    resp6 = urllib.request.urlopen("http://localhost:3000")
    assert resp6.status == 200, f"Frontend failed: {resp6.status}"
    print(f"[OK] Frontend App (Next.js): HTTP 200 OK")

async def test_websocket():
    print("\n=== Testing WebSocket Realtime Pipeline ===")
    uri = "ws://127.0.0.1:8000/ws/copilot"
    async with websockets.connect(uri) as ws:
        # Send session_start
        await ws.send(json.dumps({
            "type": "session_start",
            "sales_agent_id": "test-verifier",
            "language": "en"
        }))
        res1 = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
        assert res1["type"] == "session_ready", f"Unexpected WS response: {res1}"
        session_id = res1["session_id"]
        print(f"[OK] WebSocket Handshake: session_id={session_id}")

        # Send ping
        await ws.send(json.dumps({"type": "ping", "nonce": "test-nonce-123"}))
        res2 = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))
        assert res2["type"] == "pong" and res2["nonce"] == "test-nonce-123", f"Unexpected pong: {res2}"
        print(f"[OK] WebSocket Ping/Pong: nonce={res2['nonce']}")

if __name__ == "__main__":
    test_http_endpoints()
    asyncio.run(test_websocket())
    print("\n==========================================")
    print("ALL TEST CHECKS PASSED SUCCESSFULLY (100%)!")
    print("==========================================")
