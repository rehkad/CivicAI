# API

The FastAPI server exposes a `/chat` endpoint that generates answers using a
local or remote LLM. Before running the server, ingest city documents so the
vector database can provide context:

```bash
python3 ../data/ingest.py
uvicorn main:app --host 0.0.0.0 --port 8000
```
