from fastapi import FastAPI, HTTPException, Body
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from pathlib import Path
import os
import re
from urllib.request import urlopen

WEB_DIR = Path(__file__).parent.parent / "web"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

from .chat_engine import ChatEngine

vectordb = None


engine = ChatEngine()




class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


class ScrapeResponse(BaseModel):
    text: str


@app.get("/", response_class=FileResponse)
async def index():
    return FileResponse(WEB_DIR / "index.html")

@app.get("/health")
async def health() -> dict[str, str]:
    """Simple health check."""
    return {"status": "ok"}


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape(url: Optional[str] = Body(default=None), file_content: Optional[str] = Body(default=None)):
    """Fetch and return text from a URL or provided file content."""
    if not url and not file_content:
        raise HTTPException(status_code=400, detail="url or file_content required")
    text = ""
    if url:
        try:
            with urlopen(url) as resp:
                html = resp.read().decode()
            text = re.sub("<[^>]+>", " ", html)
            text = " ".join(text.split())
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    elif file_content:
        text = file_content
    return {"text": text[:1000]}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Return a response from the LLM with optional vector search context."""
    prompt = req.message
    if vectordb:
        try:
            docs = vectordb.similarity_search(req.message, k=3)
            context = "\n\n".join(d.page_content for d in docs)
            prompt = f"Context:\n{context}\n\nUser: {req.message}\nAssistant:"
        except Exception:
            pass
    reply = engine.generate(prompt)
    return {"response": reply}


@app.post("/chat_stream")
async def chat_stream(req: ChatRequest):
    """Stream the LLM response token by token."""
    prompt = req.message
    if vectordb:
        try:
            docs = vectordb.similarity_search(req.message, k=3)
            context = "\n\n".join(d.page_content for d in docs)
            prompt = f"Context:\n{context}\n\nUser: {req.message}\nAssistant:"
        except Exception:
            pass

    def token_gen():
        for token in engine.stream(prompt):
            yield token

    return StreamingResponse(token_gen(), media_type="text/plain; charset=utf-8")


@app.post("/ingest")
async def ingest_endpoint() -> dict[str, str]:
    """Trigger data ingestion to rebuild the vector database."""
    try:
        from data.ingest import main as ingest_main

        ingest_main()
        return {"status": "completed"}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
