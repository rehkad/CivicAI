from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from pathlib import Path
import os

WEB_DIR = Path(__file__).parent.parent / "web"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

from .chat_engine import ChatEngine

try:
    from langchain_community.vectorstores import Chroma
    from langchain_openai import OpenAIEmbeddings
    from langchain_community.embeddings import HuggingFaceEmbeddings
except Exception:  # pragma: no cover - optional dependency
    Chroma = None
    OpenAIEmbeddings = None
    HuggingFaceEmbeddings = None

embeddings = None
vectordb = None
if OpenAIEmbeddings or HuggingFaceEmbeddings:
    try:
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    except Exception:
        try:
            model_dir = Path(__file__).parent.parent / "models" / "bge-small-en"
            if model_dir.exists():
                embeddings = HuggingFaceEmbeddings(model_name=str(model_dir))
            else:
                embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en")
        except Exception:
            embeddings = None

if embeddings and Chroma:
    try:
        vectordb = Chroma(persist_directory="vector_db", embedding_function=embeddings)
    except Exception:
        vectordb = None


engine = ChatEngine()




class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


@app.get("/", response_class=FileResponse)
async def index():
    return FileResponse(WEB_DIR / "index.html")

@app.get("/health")
async def health() -> dict[str, str]:
    """Simple health check."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Return a response from the LLM with optional vector search context."""
    context = ""
    if vectordb:
        try:
            docs = vectordb.similarity_search(req.message, k=3)
            context = "\n\n".join(d.page_content for d in docs)
        except Exception:
            context = ""
    prompt = f"Context:\n{context}\n\nUser: {req.message}\nAssistant:"
    reply = engine.generate(prompt)
    return {"response": reply}


@app.post("/chat_stream")
async def chat_stream(req: ChatRequest):
    """Stream the LLM response token by token."""
    context = ""
    if vectordb:
        try:
            docs = vectordb.similarity_search(req.message, k=3)
            context = "\n\n".join(d.page_content for d in docs)
        except Exception:
            context = ""
    prompt = f"Context:\n{context}\n\nUser: {req.message}\nAssistant:"

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
