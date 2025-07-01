from fastapi import FastAPI, HTTPException, Body, Request
from typing import Optional
from contextlib import asynccontextmanager
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
import re
from urllib.request import urlopen
from urllib.parse import urlparse
import logging
import queue
import threading
from .chat_engine import ChatEngine
from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from .config import settings

WEB_DIR = Path(__file__).parent.parent / "web"


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup and clean up on shutdown."""
    logger.debug("Initializing ChatEngine and vector DB")
    app.state.engine = ChatEngine(
        model=settings.openai_model,
        ollama_model=settings.ollama_model,
    )
    app.state.vectordb = load_vectordb(settings.vector_db_dir)
    yield


def create_app() -> FastAPI:
    """Return a fully configured FastAPI application."""
    app = FastAPI(lifespan=lifespan)
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
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
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


class ScrapeResponse(BaseModel):
    text: str


@app.get("/health")
async def health() -> dict[str, str]:
    """Simple health check."""
    logger.debug("GET /health called")
    return {"status": "ok"}


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape(
    url: Optional[str] = Body(default=None),
    file_content: Optional[str] = Body(default=None),
):
    """Fetch and return text from a URL or provided file content."""
    logger.debug("POST /scrape called")
    try:
        if not url and not file_content:
            raise HTTPException(status_code=400, detail="url or file_content required")
        text = ""
        if url:
            parts = urlparse(url)
            if parts.scheme not in {"http", "https"}:
                raise HTTPException(status_code=400, detail="invalid url scheme")
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
async def chat(req: ChatRequest, request: Request):
    """Return a response from the LLM with optional vector search context."""
    logger.debug("POST /chat called with: %s", req.message)
    try:
        prompt = req.message
        vectordb: Chroma | None = request.app.state.vectordb
        if vectordb:
            try:
                docs = vectordb.similarity_search(req.message, k=3)
                context = "\n\n".join(d.page_content for d in docs)
                prompt = f"Context:\n{context}\n\nUser: {req.message}\nAssistant:"
            except Exception:
                logger.exception("Vector search failed")
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
        prompt = req.message
        vectordb: Chroma | None = request.app.state.vectordb
        if vectordb:
            try:
                docs = vectordb.similarity_search(req.message, k=3)
                context = "\n\n".join(d.page_content for d in docs)
                prompt = f"Context:\n{context}\n\nUser: {req.message}\nAssistant:"
            except Exception:
                logger.exception("Vector search failed")

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
    """Trigger data ingestion to rebuild the vector database."""
    logger.debug("POST /ingest called")
    try:
        from data.ingest import main as ingest_main

        ingest_main(settings.data_dir, settings.vector_db_dir)
        request.app.state.vectordb = load_vectordb(settings.vector_db_dir)
        return {"status": "completed"}
    except Exception as exc:
        logger.exception("ingest failed: %s", exc)
        return {"status": "error", "detail": str(exc)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5000)
