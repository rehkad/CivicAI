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
6. Start the API server:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```
7. Visit `http://localhost:8000/health` to confirm the server is running. The front-end UI is served automatically at `http://localhost:8000`.

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

### Using Ollama with OpenHermes
1. Install [Ollama](https://ollama.ai) with:
   ```bash
   curl https://ollama.ai/install.sh | sh
   ```
2. Start the local model server and download the model:
   ```bash
   ollama serve &
   ollama pull openhermes
   ```
3. With `ollama` running, the API will query the `openhermes` model whenever
   `OPENAI_API_KEY` is not set.

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
server. When the API is running, open `http://localhost:8000/` to use the chat
UI. Responses stream back to the browser so you see the answer as it is
generated.

### API Endpoints

- `GET /health` – simple health check returning `{"status": "ok"}`.
- `POST /chat` – send a message and receive an LLM response.
- `POST /chat_stream` – same as `/chat` but streams tokens as they are generated.
- `POST /ingest` – rebuild the local vector database from documents.

Set the `OPENAI_API_KEY` environment variable if you want to use the OpenAI
API. Leaving this variable unset makes the app rely solely on the local
`openhermes` model via `ollama`. Without either model the server returns
"LLM response unavailable.". This open source model is downloaded with
`ollama pull openhermes` and used by default.

### Running tests

Install the additional development packages before running the tests:

```bash
pip install -r requirements-dev.txt
```

Then execute the suite with `pytest`.

### Running on Replit

This repository includes a simple `replit.nix` file so that a Python
interpreter is available by default when opened on Replit. The Nix
configuration installs `python3` and `pip`, letting you run the
application without manual setup. After the environment loads, execute
`./setup.sh` to install all Python dependencies. When the `wheels/`
directory contains wheel files the script installs from those prebuilt wheels,
so a network connection is unnecessary.

