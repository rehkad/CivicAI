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

logger.debug("Initializing ChatEngine and vector DB stubs")
vectordb = None  # Vector store disabled for debugging


engine = ChatEngine()




class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


class ScrapeResponse(BaseModel):
    text: str


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
            tokens = await asyncio.to_thread(lambda: list(engine.stream(prompt, timeout=30.0)))
            for token in tokens:
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

    uvicorn.run(app, host="0.0.0.0", port=8000)
