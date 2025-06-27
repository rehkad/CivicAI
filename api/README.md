# API

The FastAPI server exposes endpoints for chatting and managing the vector
database. Before running the server, ingest city documents so the vector
database can provide context:

```bash
python3 ../data/ingest.py  # or `python ../data/ingest.py`
uvicorn main:app --host 0.0.0.0 --port 5000
```

Available endpoints:

- `GET /health` – verify the server is running.
- `POST /chat` – interact with the language model.
- `POST /chat_stream` – send `{"message": "<text>"}` and receive a plain-text stream of tokens. Unlike `/chat`, which returns a JSON object after generation finishes, this endpoint yields tokens as they are produced.
- `POST /ingest` – rebuild the vector database.
