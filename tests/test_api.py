from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_chat_route():
    resp = client.post("/chat", json={"message": "Hello"})
    assert resp.status_code == 200
    assert "response" in resp.json()
