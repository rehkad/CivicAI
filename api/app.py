"""FastAPI application exposing chat and scraping endpoints."""

from fastapi import FastAPI, HTTPException, Request
from typing import Optional
from contextlib import asynccontextmanager
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, ValidationError, model_validator, HttpUrl
from pathlib import Path
import re
import httpx
import logging

from .logging_utils import setup_logging
import queue
import threading
from .chat_engine import ChatEngine
from .utils import is_public_url
from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from .config import settings

setup_logging(settings.log_level)
logger = logging.getLogger(__name__)

WEB_DIR = Path(__file__).parent.parent / "web"

__all__ = [
    "app",
    "create_app",
    "ChatRequest",
    "ChatResponse",
    "ScrapeRequest",
    "ScrapeResponse",
]


def load_vectordb(db_dir: Path) -> Chroma | None:
    """Load a Chroma database from ``db_dir`` if present."""
    if not db_dir.exists():
        return None
    try:
        try:
            embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        except Exception:
            model_dir = Path(__file__).parent.parent / "models" / "bge-small-en"
            name = str(model_dir) if model_dir.exists() else "BAAI/bge-small-en"
            embeddings = HuggingFaceEmbeddings(model_name=name)
        db = Chroma(persist_directory=str(db_dir), embedding_function=embeddings)
        logger.info("Loaded vector DB from %s", db_dir)
        return db
    except Exception as exc:
        logger.warning("Vector DB unavailable: %s", exc)
        return None


def build_prompt(message: str, vectordb: Chroma | None) -> str:
    """Return a prompt with optional vector search context."""
    prompt = message
    if vectordb:
        try:
            docs = vectordb.similarity_search(message, k=3)
            context = "\n\n".join(d.page_content for d in docs)
            prompt = f"Context:\n{context}\n\nUser: {message}\nAssistant:"
        except Exception:
            logger.exception("Vector search failed")
    return prompt


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup and clean up on shutdown."""
    logger.debug("Initializing ChatEngine and vector DB")
    app.state.engine = ChatEngine(
        model=settings.openai_model,
        ollama_model=settings.ollama_model,
        fallback_message=settings.fallback_message,
    )
    app.state.vectordb = load_vectordb(settings.vector_db_dir)
    try:
        yield
    finally:
        try:
            await asyncio.to_thread(app.state.engine.close)
        except Exception:
            logger.warning("Engine cleanup failed", exc_info=True)


def create_app() -> FastAPI:
    """Return a fully configured FastAPI application."""
    app = FastAPI(lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Serve static files under /static and return index.html at the root
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

    @app.get("/")
    async def index() -> FileResponse:
        """Serve the front-end UI."""
        return FileResponse(WEB_DIR / "index.html")

    return app


app = create_app()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


class ScrapeRequest(BaseModel):
    """Input data for the ``/scrape`` endpoint."""

    url: Optional[HttpUrl] = None
    file_content: Optional[str] = None

    @model_validator(mode="after")
    def _validate_data(cls, values: "ScrapeRequest") -> "ScrapeRequest":
        """Ensure at least one field is provided."""
        if not (values.url or values.file_content):
            raise ValueError("url or file_content required")
        return values

    @property
    def has_data(self) -> bool:
        return bool(self.url or self.file_content)


class ScrapeResponse(BaseModel):
    text: str


@app.get("/health")
async def health() -> dict[str, str]:
    """Simple health check."""
    logger.debug("GET /health called")
    return {"status": "ok"}


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape(payload: ScrapeRequest):
    """Fetch and return text from a URL or provided file content."""
    logger.debug("POST /scrape called")
    try:
        text = ""
        limit = settings.scrape_max_bytes
        if payload.url:
            if not is_public_url(str(payload.url)):
                raise HTTPException(status_code=400, detail="invalid url")
            async with httpx.AsyncClient(timeout=settings.scrape_timeout) as client:
                async with client.stream("GET", str(payload.url)) as resp:
                    resp.raise_for_status()
                    parts = []
                    size = 0
                    async for chunk in resp.aiter_text():
                        parts.append(chunk)
                        size += len(chunk)
                        if size >= limit:
                            break
                    html = "".join(parts)[:limit]
            text = re.sub("<[^>]+>", " ", html)
            text = " ".join(text.split())
        elif payload.file_content:
            text = payload.file_content.strip()
        return {"text": text[:limit]}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Scrape failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request):
    """Return a response from the LLM with optional vector search context."""
    logger.debug("POST /chat called with: %s", req.message)
    try:
        vectordb: Chroma | None = request.app.state.vectordb
        prompt = build_prompt(req.message, vectordb)
        # Run generation in a thread to avoid blocking the event loop
        engine: ChatEngine = request.app.state.engine
        reply = await asyncio.to_thread(engine.generate, prompt, timeout=30.0)
        logger.debug("POST /chat response: %s", reply)
        return {"response": reply}
    except Exception as exc:
        logger.exception("Chat endpoint failed: %s", exc)
        raise HTTPException(status_code=500, detail="chat failed")


@app.post("/chat_stream")
async def chat_stream(req: ChatRequest, request: Request):
    """Stream the LLM response token by token."""
    logger.debug("POST /chat_stream called with: %s", req.message)
    try:
        vectordb: Chroma | None = request.app.state.vectordb
        prompt = build_prompt(req.message, vectordb)

        async def token_gen():
            q: queue.Queue[str | None] = queue.Queue()

            engine: ChatEngine = request.app.state.engine

            def worker() -> None:
                try:
                    for tok in engine.stream(prompt, timeout=30.0):
                        q.put(tok)
                finally:
                    q.put(None)

            thread = threading.Thread(target=worker, daemon=True)
            thread.start()
            while True:
                token = await asyncio.to_thread(q.get)
                if token is None:
                    break
                logger.debug("stream token: %s", token)
                yield token

        return StreamingResponse(token_gen(), media_type="text/plain; charset=utf-8")
    except Exception as exc:
        logger.exception("chat_stream failed: %s", exc)
        raise HTTPException(status_code=500, detail="chat_stream failed")


@app.post("/ingest")
async def ingest_endpoint(request: Request) -> dict[str, str]:
    """Trigger data ingestion without blocking the event loop."""
    logger.debug("POST /ingest called")
    try:
        from data.ingest import main as ingest_main

        await asyncio.to_thread(
            ingest_main, settings.data_dir, settings.vector_db_dir
        )
        request.app.state.vectordb = load_vectordb(settings.vector_db_dir)
        return {"status": "completed"}
    except Exception as exc:
        logger.exception("ingest failed: %s", exc)
        return {"status": "error", "detail": str(exc)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5000)
