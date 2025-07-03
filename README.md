# CivicAI
CivicAI is a self-hosted AI chatbot that answers local government questions\u2014like trash pickup, permits, or municipal codes\u2014using public city data. Easily customizable for any U.S. city with local or cloud LLMs, vector search, and a simple web UI.

## Setup
1. Ensure Python 3.8 or newer is installed.
   Your system may use the `python` command instead of `python3`; adjust the commands below accordingly.
2. Clone this repository and change into its directory.
3. **(Optional) create and activate a virtual environment** before installing dependencies:
   `python3 -m venv .venv && source .venv/bin/activate` (use `python -m venv` if `python3` isn't available).
   If no environment is active, `./setup.sh` automatically creates `.venv` and installs packages there.
4. Install dependencies using `./setup.sh`. When the `wheels/` directory contains wheel files the script installs from them; otherwise it falls back to downloading packages. This script also installs `pip` when it's missing and activates `.venv` when necessary.
5. If you see `ModuleNotFoundError` errors (e.g., for FastAPI) or `pip` isn't found, rerun `./setup.sh` to ensure all dependencies are installed.
6. Start the API server (customize the host and port with `HOST` and `PORT`):
   ```bash
   HOST=0.0.0.0 PORT=5000 uvicorn main:app --host "$HOST" --port "$PORT"
   ```
7. Visit `http://<host>:<port>/health` to confirm the server is running. The front-end UI is served automatically at `http://<host>:<port>`.

Alternatively, execute `./start.sh` to perform steps 3–7 automatically.

**Workflow:** run `./setup.sh`, then `python3 data/ingest.py` (or `python data/ingest.py`), and finally `python3 api/app.py` (or `python api/app.py`).

### Why pin versions?
The `requirements.txt` file lists exact dependency versions so the
project installs the same packages every time. This keeps the
environment reproducible and avoids unexpected changes when working
offline or rebuilding later.

### Populating `wheels/` for offline setup
When you do have an internet connection, predownload the project dependencies so
they're available later without network access:

```bash
pip download -r requirements.txt -d wheels
```

This creates wheel files under the `wheels/` directory. When offline, the
`./setup.sh` script installs from these wheels if they are available;
otherwise it will attempt to download packages from PyPI.

If you run `./setup.sh` and see a message like `Missing wheel files for packages: fastapi ...`,
it's because the required wheels aren't present in the `wheels/` folder. Run the
`pip download` command above while online to populate the directory and then
rerun `./setup.sh`.

### Configuring the LLM
CivicAI now relies on [LangChain](https://python.langchain.com) to talk to a
language model. The server will prefer the OpenAI API when the
`OPENAI_API_KEY` environment variable is set. Without a key it will try to use
a locally running [Ollama](https://ollama.ai) model (such as `llama2`).  If
neither backend is available the app runs in a lightweight demo mode that
simply echoes your input.

You can override the default model names using environment variables:

- `OPENAI_MODEL` – OpenAI chat model used when `OPENAI_API_KEY` is set.
- `OLLAMA_MODEL` – local model name for the Ollama backend.

### Ingesting city data (optional)
Sample Santa Barbara documents are provided in `data/santa_barbara/`. Run
`python3 data/ingest.py` to create a local vector store which the chat endpoint
uses for extra context if available. This step is optional and requires an
internet connection the first time to download embeddings.

### Configuration
Two environment variables control where data is stored:

- `VECTOR_DB_DIR` – location of the Chroma vector store (default `vector_db/`).
- `DATA_DIR` – directory of text files to ingest (default `data/santa_barbara/`).

Both the ingestion script and the API server honor these variables so you can
customize paths without editing the code.

-Additional optional variables:

- `LOG_LEVEL` – Python logging level (default `INFO`). The server
  configures logging automatically using this level.
- `CORS_ORIGINS` – comma-separated list of allowed CORS origins (default `*`).
- `HOST` – address the server binds to (default `0.0.0.0`).
- `PORT` – port number for the API server (default `5000`).
- `SCRAPE_TIMEOUT` – seconds to wait when fetching URLs (default `10`).
- `SCRAPE_MAX_BYTES` – maximum characters returned by `/scrape` (default `100000`).
- `FALLBACK_MESSAGE` – text returned when no language model is available.

## Folder overview
- **`api/`** \u2013 backend API server written in Python.
- **`web/`** \u2013 front-end web application placeholder.
- **`data/`** \u2013 example datasets and loading scripts.

## Development
Edit `api/app.py` to add endpoints or change logic. The server automatically reloads when you restart the command above. Front-end and data-related code live under `web/` and `data/` respectively.

The included web interface (`web/index.html`) sends messages to the FastAPI
server. When the API is running, open `http://localhost:5000/` to use the chat
UI. Responses stream back to the browser so you see the answer as it is
generated.

### API Endpoints

- `GET /health` – simple health check returning `{"status": "ok"}`.
- `POST /chat` – send a message and receive an LLM response.
- `POST /chat_stream` – same as `/chat` but streams tokens as they are generated.
- `POST /ingest` – rebuild the local vector database from documents (optional).
- `POST /scrape` – return text from a URL or uploaded file.

Set `OPENAI_API_KEY` to send requests to OpenAI's hosted models. When the
variable is unset the server looks for an Ollama instance instead. If neither is
available you will only see a short demo response.

### Running tests

Before running `pytest`, **you must install the development requirements**:

```bash
pip install -r requirements-dev.txt
```

After the dependencies are installed, run the suite with:

```bash
python -m pytest
```

### Running on Replit

This repository includes a simple `replit.nix` file so that a Python
interpreter is available by default when opened on Replit. The Nix
configuration installs `python3` and `pip`, letting you run the
application without manual setup. After the environment loads, execute
`./setup.sh` to install all Python dependencies. When the `wheels/`
directory contains wheel files the script installs from those prebuilt wheels,
so a network connection is unnecessary.

