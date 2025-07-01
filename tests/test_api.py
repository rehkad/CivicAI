import importlib
import json
from fastapi.testclient import TestClient
import pytest

import api.app as app_mod

client = TestClient(app_mod.app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_chat_route():
    resp = client.post("/chat", json={"message": "Hello"})
    assert resp.status_code == 200
    assert "response" in resp.json()


def test_chat_stream_returns_chunks():
    resp = client.post("/chat_stream", json={"message": "Hello"})
    assert resp.status_code == 200
    assert len(resp.text) >= 1


def test_scrape_file():
    content = "name,city\nAlice,Springfield"
    resp = client.post("/scrape", json={"file_content": content})
    assert resp.status_code == 200
    data = resp.json()
    assert "Alice" in data["text"]


def test_root_serves_ui():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "CivicAI Chat" in resp.text


def test_ingest_endpoint(monkeypatch):
    called = {}

    def fake_main(data_dir=None, db_dir=None):
        called["hit"] = True

    import types

    dummy = types.SimpleNamespace(main=fake_main)
    monkeypatch.setitem(importlib.sys.modules, "data.ingest", dummy)
    resp = client.post("/ingest")
    assert resp.json() == {"status": "completed"}
    assert called.get("hit") is True


def test_env_overrides_vector_db(monkeypatch, tmp_path):
    monkeypatch.setenv("VECTOR_DB_DIR", str(tmp_path / "db"))
    import api.config as cfg

    importlib.reload(cfg)
    importlib.reload(app_mod)
    assert cfg.settings.vector_db_dir == tmp_path / "db"


def test_chat_engine_env_models(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "foo")
    monkeypatch.setenv("OLLAMA_MODEL", "bar")
    import api.chat_engine as ce

    importlib.reload(ce)
    engine = ce.ChatEngine()
    assert engine.model == "foo"
    assert engine.ollama_model == "bar"


def test_scrape_rejects_bad_scheme():
    resp = client.post("/scrape", json={"url": "file:///etc/passwd"})
    assert resp.status_code == 400
