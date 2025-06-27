import threading
import time
import json
import urllib.request
from api.app import app
import uvicorn

server = None
thread = None


def setup_module(module):
    global server, thread
    config = uvicorn.Config(app, host="127.0.0.1", port=5000, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    time.sleep(1)


def teardown_module(module):
    server.should_exit = True
    thread.join()


def _post(path, payload=None):
    url = f"http://127.0.0.1:5000{path}"
    headers = {}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode()


def _get(path):
    url = f"http://127.0.0.1:5000{path}"
    with urllib.request.urlopen(url) as resp:
        return resp.read().decode()


def test_health():
    data = json.loads(_get("/health"))
    assert data == {"status": "ok"}


def test_chat_route():
    data = json.loads(_post("/chat", {"message": "Hello"}))
    assert "response" in data


def test_chat_stream_returns_chunks():
    text = _post("/chat_stream", {"message": "Hello"})
    assert len(text) >= 1


def test_scrape_file():
    content = "name,city\nAlice,Springfield"
    text = _post("/scrape", {"file_content": content})
    data = json.loads(text)
    assert "Alice" in data["text"]


def test_root_serves_ui():
    html = _get("/")
    assert "CivicAI Chat" in html


def test_ingest_endpoint(monkeypatch):
    called = {}
    def fake_main():
        called["hit"] = True
    import types
    import sys
    dummy = types.SimpleNamespace(main=fake_main)
    monkeypatch.setitem(sys.modules, "data.ingest", dummy)
    data = json.loads(_post("/ingest"))
    assert data == {"status": "completed"}
    assert called.get("hit") is True
