from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    import ollama
except Exception:  # pragma: no cover - optional dependency
    ollama = None

try:
    import openai
except Exception:  # pragma: no cover - optional dependency
    openai = None
if openai:
    openai.api_key = os.getenv("OPENAI_API_KEY", "")

try:
    from langchain.vectorstores import Chroma
    from langchain.embeddings import OpenAIEmbeddings, HuggingFaceEmbeddings
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


class ChatEngine:
    async def generate(self, prompt: str) -> str:
        if ollama:
            try:
                result = ollama.generate(model="openhermes:latest", prompt=prompt)
                return result.get("response", "")
            except Exception:
                pass
        if openai:
            try:
                resp = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                )
                return resp.choices[0].message["content"].strip()
            except Exception:
                pass
        return "LLM response unavailable."


engine = ChatEngine()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


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
    reply = await engine.generate(prompt)
    return {"response": reply}


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
