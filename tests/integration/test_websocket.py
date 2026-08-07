from ai.config.settings import Settings
from ai.main import create_app
from fastapi.testclient import TestClient


def test_websocket_session_and_ping(settings: Settings) -> None:
    with (
        TestClient(create_app(settings)) as client,
        client.websocket_connect("/ws/copilot") as websocket,
    ):
        websocket.send_json({"type": "session_start", "sales_agent_id": "agent-1"})
        ready = websocket.receive_json()
        assert ready["type"] == "session_ready"
        websocket.send_json({"type": "ping", "nonce": "n1"})
        assert websocket.receive_json() == {"type": "pong", "nonce": "n1"}
