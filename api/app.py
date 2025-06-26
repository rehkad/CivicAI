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
    """Wrapper around whichever LLM is available."""

    fallback_message = (
        "The assistant is running in demo mode.\n"
        "Start Ollama with `ollama serve` or set `OPENAI_API_KEY` to enable "
        "real answers."
    )

    def _fallback_stream(self, prompt: str):
        """Simple echo-style fallback when no LLM is configured."""
        user_msg = prompt.split("User:")[-1].split("Assistant:")[0].strip()
        text = f"(demo) You said: {user_msg}" if user_msg else self.fallback_message
        for ch in text:
            yield ch

    def stream(self, prompt: str):
        """Yield tokens from the model if streaming is supported."""
        if ollama:
            try:
                for chunk in ollama.generate(
                    model="openhermes:latest", prompt=prompt, stream=True
                ):
                    if isinstance(chunk, dict):
                        yield chunk.get("response", "")
                    else:
                        yield str(chunk)
                return
            except Exception:
                pass
        if openai:
            try:
                resp = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    stream=True,
                )
                for part in resp:
                    delta = part["choices"][0]["delta"].get("content")
                    if delta:
                        yield delta
                return
            except Exception:
                pass
        # Fall back to a simple local response so the app still functions.
        yield from self._fallback_stream(prompt)

    def generate(self, prompt: str) -> str:
        """Return the full response from the model."""
        return "".join(list(self.stream(prompt)))


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
