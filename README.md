# CivicAI
CivicAI is a self-hosted AI chatbot that answers local government questions\u2014like trash pickup, permits, or municipal codes\u2014using public city data. Easily customizable for any U.S. city with local or cloud LLMs, vector search, and a simple web UI.

## Setup
1. Ensure Python 3.8 or newer is installed.
   Your system may use the `python` command instead of `python3`; adjust the commands below accordingly.
2. Clone this repository and change into its directory.
3. (Optional) Create a virtual environment: `python3 -m venv .venv && source .venv/bin/activate` (use `python -m venv` if `python3` isn't available).
4. Install dependencies using `./setup.sh`. When no internet connection is available the script installs from a prepopulated `wheels/` directory.
5. Start the API server:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```
6. Visit `http://localhost:8000` to verify the server is running.

**Workflow:** run `./setup.sh`, then `python3 data/ingest.py` (or `python data/ingest.py`), and finally `python3 api/app.py` (or `python api/app.py`).

### Ingesting city data
Sample Santa Barbara documents are provided in `data/santa_barbara/`. The
ingestion script requires the `BAAI/bge-small-en` embeddings model. Download
the model from [Hugging Face](https://huggingface.co/BAAI/bge-small-en) and
place the files under `models/bge-small-en/` so they are available offline.
Then run the ingestion script to create a local Chroma database before starting
the API:

```bash
python3 data/ingest.py  # or `python data/ingest.py`
```

## Folder overview
- **`api/`** \u2013 backend API server written in Python.
- **`web/`** \u2013 front-end web application placeholder.
- **`data/`** \u2013 example datasets and loading scripts.

## Development
Edit `api/app.py` to add endpoints or change logic. The server automatically reloads when you restart the command above. Front-end and data-related code live under `web/` and `data/` respectively.

The included web interface (`web/index.html`) sends messages to the FastAPI
server at `http://localhost:8000/chat`.

### API Endpoints

- `GET /health` – simple health check returning `{"status": "ok"}`.
- `POST /chat` – send a message and receive an LLM response.
- `POST /ingest` – rebuild the local vector database from documents.

Set the `OPENAI_API_KEY` environment variable if you want to use the OpenAI
API. Without it, the server falls back to local models when available or returns
"LLM response unavailable.".

### Running tests

Run `pytest` to execute the small test suite.

