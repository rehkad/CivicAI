import json
import urllib.request
import urllib.error


def _get(path: str) -> tuple[int, str]:
    url = f"http://127.0.0.1:8000{path}"
    try:
        with urllib.request.urlopen(url) as resp:
            return resp.getcode(), resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def _post(path: str, payload: dict, headers: dict | None = None) -> tuple[int, str]:
    url = f"http://127.0.0.1:8000{path}"
    data = json.dumps(payload).encode()
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.getcode(), resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def test_models_endpoint():
    code, body = _get("/models")
    assert code == 200
    data = json.loads(body)
    assert set(["backend", "model", "vector_db"]).issubset(data.keys())


def test_rate_limit_chat(monkeypatch):
    # Force limit to 0 to deterministically trigger 429
    import api.app as appmod
    appmod.app.state.rate_limit_per_minute = 60  # normal limit, but override per request via header
    appmod.app.state.ip_windows.clear()

    code, body = _post("/chat", {"message": "should be limited"}, headers={"X-Test-Rate-Limit": "0"})
    assert code == 429
    data = json.loads(body)
    assert data.get("detail") == "rate limit exceeded"


def test_search_endpoint_smoke():
    code, body = _post("/search", {"query": "trash pickup", "limit": 1})
    assert code == 200
    data = json.loads(body)
    assert "count" in data and "results" in data


