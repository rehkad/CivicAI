# Data

This directory contains example documents for Santa Barbara along with an
`ingest.py` script that loads them into a local Chroma database.

Run `python3 ingest.py` (or `python ingest.py`) to create the vector store used by the API.

## Preloading the embedding model

`ingest.py` falls back to the `BAAI/bge-small-en` model when OpenAI
embeddings are unavailable. Download the model files from
[Hugging Face](https://huggingface.co/BAAI/bge-small-en) and place them in
`models/bge-small-en/` at the repository root if you want to avoid network
downloads during ingestion or API startup.
