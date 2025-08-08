from fastapi import FastAPI, HTTPException, Body
from typing import Optional
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from pathlib import Path
import os
import re
from urllib.request import urlopen
import logging
import threading
import time
from collections import defaultdict

WEB_DIR = Path(__file__).parent.parent / "web"

app = FastAPI()
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

from .chat_engine import ChatEngine
from .config import settings
from . import sources
from .cities import PRESETS, CityPreset

logger.debug("Initializing ChatEngine and attempting optional vector DB load")
vectordb = None  # Set below if a persisted DB exists and dependencies are available


def _maybe_load_vectordb():
    """Attempt to load a persisted Chroma DB if present. Returns the DB or None."""
    try:
        if not settings.enable_vector_db:
            logger.info("Vector DB disabled by configuration")
            return None

        db_dir = Path(settings.vector_db_dir)
        if not db_dir.exists():
            logger.info("Vector DB directory not found at %s - continuing without search", db_dir)
            return None

        # Import lazily to avoid hard dependency when running in demo mode
        try:
            from data.ingest import get_embeddings  # reuse embedding selection logic
            from langchain_community.vectorstores import Chroma
        except Exception as e:  # ImportError or other
            logger.warning("Vector DB dependencies unavailable (%s) - continuing without search", e)
            return None

        embeddings = get_embeddings()
        db = Chroma(persist_directory=str(db_dir), embedding_function=embeddings)
        # quick no-op to ensure it opens
        _ = db._collection if hasattr(db, "_collection") else None
        logger.info("Loaded vector DB from %s", db_dir)
        return db
    except Exception as exc:
        logger.warning("Failed to initialize vector DB: %s", exc)
        return None


vectordb = _maybe_load_vectordb()


engine = ChatEngine(model=settings.model_name, temperature=settings.model_temperature, ollama_model=settings.ollama_model)




class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    citations: list[dict] | None = None


class ScrapeResponse(BaseModel):
    text: str


# Simple per-IP rate limiter (fixed window per 60s)
app.state.rate_limit_per_minute = int(os.getenv("REQUESTS_PER_MINUTE", "60"))
app.state.ip_windows = {}


@app.middleware("http")
async def rate_limit_and_log(request, call_next):
    start = time.time()
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window_start = now - 60.0
    start_count = 0
    windows: dict = request.app.state.ip_windows
    window = windows.get(client_ip)
    # Per-request override for testing
    override_header = request.headers.get("X-Test-Rate-Limit")
    effective_limit = None
    if override_header is not None:
        try:
            effective_limit = int(override_header)
        except Exception:
            effective_limit = None

    # Deterministic block when limit is set to 0 or negative (useful for tests)
    if (effective_limit is not None and effective_limit <= 0) or request.app.state.rate_limit_per_minute <= 0:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=429, content={"detail": "rate limit exceeded"})
    if not window or window[0] < window_start:
        windows[client_ip] = (now, 0)
        start_count = 0
    else:
        start_count = window[1]

    limit = effective_limit if effective_limit is not None else request.app.state.rate_limit_per_minute
    if start_count >= limit:
        logger.warning("Rate limit exceeded for %s", client_ip)
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=429, content={"detail": "rate limit exceeded"})
    else:
        windows[client_ip] = (window[0] if window else now, start_count + 1)
    response = await call_next(request)
    elapsed_ms = int((time.time() - start) * 1000)
    logger.info("%s %s -> %s (%d ms)", request.method, request.url.path, response.status_code, elapsed_ms)
    return response


@app.get("/", response_class=FileResponse)
async def index():
    logger.debug("GET / called")
    try:
        return FileResponse(WEB_DIR / "index.html")
    except Exception as exc:
        logger.exception("Failed to serve index: %s", exc)
        raise

@app.get("/health")
async def health() -> dict[str, str]:
    """Simple health check."""
    logger.debug("GET /health called")
    return {"status": "ok"}


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape(url: Optional[str] = Body(default=None), file_content: Optional[str] = Body(default=None)):
    """Fetch and return text from a URL or provided file content."""
    logger.debug("POST /scrape called")
    try:
        if not url and not file_content:
            raise HTTPException(status_code=400, detail="url or file_content required")
        text = ""
        if url:
            with urlopen(url) as resp:
                html = resp.read().decode()
            text = re.sub("<[^>]+>", " ", html)
            text = " ".join(text.split())
        elif file_content:
            text = file_content
        return {"text": text[:1000]}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Scrape failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Return a response from the LLM with optional vector search context."""
    logger.debug("POST /chat called with: %s", req.message)
    try:
        prompt = req.message
        citations: list[dict] | None = None
        if vectordb:
            try:
                docs = vectordb.similarity_search(req.message, k=3)
                context = "\n\n".join(d.page_content for d in docs)
                citations = [
                    {
                        "source": getattr(d, "metadata", {}).get("source", "vector_db"),
                        "score": getattr(d, "score", None),
                    }
                    for d in docs
                ]
                # RAG-enabled prompt template
                prompt = (
                    "You are CivicAI, a helpful city services assistant. Use the provided context to answer the user's question concisely.\n\n"
                    f"Context:\n{context}\n\n"
                    f"User: {req.message}\nAssistant:"
                )
            except Exception:
                logger.exception("Vector search failed")
        # Run generation in a thread to avoid blocking the event loop
        reply = await asyncio.to_thread(engine.generate, prompt, timeout=settings.chat_timeout_seconds)
        logger.debug("POST /chat response: %s", reply)
        return {"response": reply, "citations": citations}
    except Exception as exc:
        logger.exception("Chat endpoint failed: %s", exc)
        raise HTTPException(status_code=500, detail="chat failed")


@app.post("/chat_stream")
async def chat_stream(req: ChatRequest):
    """Stream the LLM response token by token."""
    logger.debug("POST /chat_stream called with: %s", req.message)
    try:
        prompt = req.message
        if vectordb:
            try:
                docs = vectordb.similarity_search(req.message, k=3)
                context = "\n\n".join(d.page_content for d in docs)
                prompt = (
                    "You are CivicAI, a helpful city services assistant. Use the provided context to answer the user's question concisely.\n\n"
                    f"Context:\n{context}\n\n"
                    f"User: {req.message}\nAssistant:"
                )
            except Exception:
                logger.exception("Vector search failed")

        # Bridge the synchronous token generator to an async StreamingResponse
        async def token_gen():
            loop = asyncio.get_running_loop()
            queue: asyncio.Queue[str | None] = asyncio.Queue()

            def produce_tokens():
                try:
                    for token in engine.stream(prompt, timeout=settings.chat_timeout_seconds):
                        asyncio.run_coroutine_threadsafe(queue.put(token), loop)
                finally:
                    asyncio.run_coroutine_threadsafe(queue.put(None), loop)

            threading.Thread(target=produce_tokens, daemon=True).start()

            while True:
                token = await queue.get()
                if token is None:
                    break
                logger.debug("stream token: %s", token)
                yield token

        return StreamingResponse(token_gen(), media_type="text/plain; charset=utf-8")
    except Exception as exc:
        logger.exception("chat_stream failed: %s", exc)
        raise HTTPException(status_code=500, detail="chat_stream failed")


@app.get("/models")
async def models_info():
    """Expose backend/model configuration and vector DB status."""
    try:
        info = engine.get_info()
        return {
            **info,
            "vector_db": bool(vectordb),
            "vector_db_dir": str(Path(settings.vector_db_dir)),
        }
    except Exception as exc:
        logger.exception("/models failed: %s", exc)
        raise HTTPException(status_code=500, detail="models info failed")


class SearchRequest(BaseModel):
    query: str
    limit: int = 5
    city: str | None = None


from functools import lru_cache


@lru_cache(maxsize=256)
def _search_cache_key(query: str, limit: int, city: str | None) -> tuple:
    return (query.strip().lower(), int(limit), (city or '').strip().lower())


@app.post("/search")
async def aggregated_search(req: SearchRequest):
    """Aggregate results from federal and local open-data APIs."""
    try:
        limit = max(1, min(10, req.limit))
        results = []
        # Simple cache
        key = _search_cache_key(req.query, limit, req.city)
        # Not caching async payload easily; reuse lru key to gate execution
        # If we wanted full cache, we'd store results in app.state; keep simple for now.

        # Federal
        results.extend(await sources.search_federal_register(req.query, limit))
        results.extend(await sources.search_govinfo(req.query, limit))
        results.extend(await sources.search_regulations_gov(req.query, limit))
        results.extend(await sources.search_datagov(req.query, limit))
        try:
            results.extend(await sources.usaspending_search(req.query, limit))
        except Exception:
            logger.exception("USAspending search failed")

        # Local (examples): Socrata and ArcGIS, driven by env for demo
        preset: CityPreset | None = PRESETS.get((req.city or "").strip().lower()) if req.city else None
        soc_domain = (preset.socrata_domain if preset else None) or os.getenv("SOCRATA_DOMAIN")
        soc_dataset = (preset.socrata_dataset if preset else None) or os.getenv("SOCRATA_DATASET")
        if soc_domain and soc_dataset:
            try:
                results.extend(await sources.socrata_search(soc_domain, soc_dataset, limit=limit))
            except Exception:
                logger.exception("Socrata search failed")
        arcgis_url = (preset.arcgis_service_url if preset else None) or os.getenv("ARCGIS_SERVICE_URL")
        if arcgis_url:
            try:
                results.extend(await sources.arcgis_query(arcgis_url, limit=limit))
            except Exception:
                logger.exception("ArcGIS query failed")

        # Cap output
        return {"count": len(results), "results": results[: 3 * limit]}
    except Exception as exc:
        logger.exception("aggregated search failed: %s", exc)
        raise HTTPException(status_code=500, detail="search failed")


@app.post("/ingest")
async def ingest_endpoint() -> dict[str, str]:
    """Trigger data ingestion to rebuild the vector database."""
    logger.debug("POST /ingest called")
    try:
        from data.ingest import main as ingest_main

        ingest_main()
        return {"status": "completed"}
    except Exception as exc:
        logger.exception("ingest failed: %s", exc)
        return {"status": "error", "detail": str(exc)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.app:app", host=settings.host, port=settings.port, reload=True)
