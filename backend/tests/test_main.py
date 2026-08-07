from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_root():
    """Verify that GET / returns the configured root message and HTTP 200."""
    response = client.get("/")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"
    assert "Sales AI Backend is running" in json_data["message"]
    assert json_data["version"] == "1.0.0"

def test_docs_and_redoc_endpoints():
    """Verify that Swagger /docs and ReDoc /redoc endpoints are accessible."""
    response_docs = client.get("/docs")
    assert response_docs.status_code == 200
    assert "swagger" in response_docs.text.lower() or "openapi" in response_docs.text.lower()
    
    response_redoc = client.get("/redoc")
    assert response_redoc.status_code == 200
    assert "redoc" in response_redoc.text.lower()
