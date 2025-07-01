from fastapi import FastAPI, HTTPException, Body
from typing import Optional
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
import re
from urllib.request import urlopen
import logging
import os
import queue
import threading
from .chat_engine import ChatEngine
from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

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

# Serve static files under /static and return index.html at the root
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


@app.get("/")
async def index() -> FileResponse:
    """Serve the front-end UI."""
    return FileResponse(WEB_DIR / "index.html")

logger.debug("Initializing ChatEngine and vector DB")
# Allow overriding the vector store location via the VECTOR_DB_DIR environment variable
db_env = os.getenv("VECTOR_DB_DIR")
DB_DIR = Path(db_env) if db_env else Path(__file__).parent.parent / "vector_db"
engine = ChatEngine()
vectordb = None
if DB_DIR.exists():
    try:
        try:
            embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        except Exception:
            model_dir = Path(__file__).parent.parent / "models" / "bge-small-en"
            name = str(model_dir) if model_dir.exists() else "BAAI/bge-small-en"
            embeddings = HuggingFaceEmbeddings(model_name=name)
        vectordb = Chroma(persist_directory=str(DB_DIR), embedding_function=embeddings)
        logger.info("Loaded vector DB from %s", DB_DIR)
    except Exception as exc:
        logger.warning("Vector DB unavailable: %s", exc)




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
        if vectordb:
            try:
                docs = vectordb.similarity_search(req.message, k=3)
                context = "\n\n".join(d.page_content for d in docs)
                prompt = f"Context:\n{context}\n\nUser: {req.message}\nAssistant:"
            except Exception:
                logger.exception("Vector search failed")
        # Run generation in a thread to avoid blocking the event loop
        reply = await asyncio.to_thread(engine.generate, prompt, timeout=30.0)
        logger.debug("POST /chat response: %s", reply)
        return {"response": reply}
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
                prompt = f"Context:\n{context}\n\nUser: {req.message}\nAssistant:"
            except Exception:
                logger.exception("Vector search failed")

        async def token_gen():
            q: queue.Queue[str | None] = queue.Queue()

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

    uvicorn.run(app, host="0.0.0.0", port=5000)
