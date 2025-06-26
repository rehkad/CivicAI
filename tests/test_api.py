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


def test_chat_stream_returns_chunks():
    """POST /chat_stream streams at least one token."""
    with client.stream("POST", "/chat_stream", json={"message": "Hello"}) as resp:
        assert resp.status_code == 200
        chunks = list(resp.iter_text())
    assert len(chunks) >= 1


def test_root_serves_ui():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "CivicAI Chat" in resp.text


def test_ingest_endpoint(monkeypatch):
    """POST /ingest returns completed status and calls ingest.main."""

    called = {}

    def fake_main():
        called["hit"] = True

    monkeypatch.setattr("data.ingest.main", fake_main)

    resp = client.post("/ingest")
    assert resp.status_code == 200
    assert resp.json() == {"status": "completed"}
    assert called.get("hit") is True
