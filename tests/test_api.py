import importlib
import pytest
from fastapi.testclient import TestClient

import api.app as app_mod

client = TestClient(app_mod.app)


def test_create_app() -> None:
    """create_app should return a new FastAPI instance each call."""
    app1 = app_mod.create_app()
    app2 = app_mod.create_app()
    assert app1 is not app2


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


def test_scrape_html_sanitization():
    html = "<html><body><h1>Hello</h1><p>World</p></body></html>"
    resp = client.post("/scrape", json={"file_content": html})
    assert resp.status_code == 200
    assert resp.json()["text"] == "Hello World"


def test_scrape_requires_data():
    """scrape should reject requests without url or file_content."""
    resp = client.post("/scrape", json={})
    assert resp.status_code == 422


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


def test_settings_env(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    monkeypatch.setenv("CORS_ORIGINS", "https://a.com,https://b.com")
    monkeypatch.setenv("HOST", "127.0.0.1")
    monkeypatch.setenv("PORT", "1234")
    import api.config as cfg

    importlib.reload(cfg)
    assert cfg.settings.log_level == "WARNING"
    assert cfg.settings.allowed_origins == ["https://a.com", "https://b.com"]
    assert cfg.settings.server_host == "127.0.0.1"
    assert cfg.settings.server_port == 1234


def test_scrape_rejects_bad_scheme():
    resp = client.post("/scrape", json={"url": "file:///etc/passwd"})
    assert resp.status_code == 422


def test_scrape_rejects_private_ip():
    resp = client.post("/scrape", json={"url": "http://127.0.0.1"})
    assert resp.status_code == 400


def test_scrape_settings_env(monkeypatch):
    monkeypatch.setenv("SCRAPE_TIMEOUT", "5.5")
    monkeypatch.setenv("SCRAPE_MAX_BYTES", "123")
    import importlib
    import api.config as cfg

    importlib.reload(cfg)
    assert cfg.settings.scrape_timeout == 5.5
    assert cfg.settings.scrape_max_bytes == 123


def test_scrape_truncates_by_max_bytes(monkeypatch):
    monkeypatch.setattr(app_mod.settings, "scrape_max_bytes", 5)
    resp = client.post("/scrape", json={"file_content": "abcdefg"})
    assert resp.status_code == 200
    assert resp.json()["text"] == "abcde"


def test_fallback_message_env(monkeypatch):
    monkeypatch.setenv("FALLBACK_MESSAGE", "hello")
    import importlib
    import api.config as cfg
    import api.chat_engine as ce

    importlib.reload(cfg)
    importlib.reload(ce)
    engine = ce.ChatEngine()
    assert engine.fallback_message == "hello"
    assert cfg.settings.fallback_message == "hello"


def test_max_message_bytes_env(monkeypatch):
    monkeypatch.setenv("MAX_MESSAGE_BYTES", "12")
    import importlib
    import api.config as cfg

    importlib.reload(cfg)
    assert cfg.settings.max_message_bytes == 12


def test_build_prompt_with_vectordb():
    from api.app import build_prompt

    class Doc:
        def __init__(self, text: str) -> None:
            self.page_content = text

    class DummyDB:
        def similarity_search(self, _query: str, k: int = 3):
            return [Doc("context1"), Doc("context2")]

    prompt = build_prompt("hello", DummyDB())
    assert "context1" in prompt and "User: hello" in prompt


def test_setup_logging_sets_level(monkeypatch):
    import logging
    from importlib import reload
    import api.logging_utils as lu

    reload(lu)
    lu.setup_logging("DEBUG")
    assert logging.getLogger().getEffectiveLevel() == logging.DEBUG


def test_env_file(monkeypatch, tmp_path):
    env = tmp_path / ".env"
    env.write_text("PORT=4321\n")
    monkeypatch.chdir(tmp_path)
    import importlib
    import api.config as cfg

    importlib.reload(cfg)
    assert cfg.settings.server_port == 4321


def test_scrape_request_model_validation():
    from pydantic import ValidationError
    from api.app import ScrapeRequest

    with pytest.raises(ValidationError):
        ScrapeRequest()


def test_chat_request_length_validation(monkeypatch):
    monkeypatch.setenv("MAX_MESSAGE_BYTES", "5")
    import importlib
    import api.config as cfg
    import api.app as app_mod

    importlib.reload(cfg)
    importlib.reload(app_mod)
    client = TestClient(app_mod.app)
    resp = client.post("/chat", json={"message": "abcdef"})
    assert resp.status_code == 422


def test_chat_engine_demo_mode(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    import importlib
    import api.chat_engine as ce

    importlib.reload(ce)
    engine = ce.ChatEngine()
    assert engine.demo_mode is True


@pytest.mark.asyncio
async def test_chat_engine_generate_async():
    from api.chat_engine import ChatEngine

    engine = ChatEngine()
    text = await engine.generate_async("hi", timeout=1.0)
    assert text


@pytest.mark.asyncio
async def test_chat_engine_stream_async():
    from api.chat_engine import ChatEngine

    engine = ChatEngine()
    parts = []
    async for chunk in engine.stream_async("hi", timeout=1.0):
        parts.append(chunk)
    assert "".join(parts)


def test_html_to_text():
    from api.utils import html_to_text

    text = html_to_text("<div>Hello <b>world</b></div>")
    assert text == "Hello world"


def test_html_to_text_strips_script_style():
    from api.utils import html_to_text

    html = "<div>Good</div><script>bad()</script><style>.x{}</style>Bye"
    assert html_to_text(html) == "Good Bye"


def test_settings_port_validation(monkeypatch):
    monkeypatch.setenv("PORT", "70000")
    import importlib
    with pytest.raises(ValueError):
        import api.config as cfg
        importlib.reload(cfg)


@pytest.mark.asyncio
async def test_chat_engine_concurrent():
    from api.chat_engine import ChatEngine

    engine = ChatEngine()

    async def call():
        return await engine.generate_async("hi", timeout=1.0)

    r1, r2 = await asyncio.gather(call(), call())
    assert r1 and r2
