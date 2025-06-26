# API

The FastAPI server exposes endpoints for chatting and managing the vector
database. Before running the server, ingest city documents so the vector
database can provide context:

```bash
python3 ../data/ingest.py
uvicorn main:app --host 0.0.0.0 --port 8000
```

Available endpoints:

- `GET /health` – verify the server is running.
- `POST /chat` – interact with the language model.
- `POST /ingest` – rebuild the vector database.
