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

### Configuring the LLM
This version of CivicAI uses the OpenAI API by default. Set the
`OPENAI_API_KEY` environment variable before starting the server so requests are
sent to OpenAI's hosted models. When no API key is provided the app falls back
to a simple demo mode that echoes your input.

### Ingesting city data (optional)
Sample Santa Barbara documents are provided in `data/santa_barbara/`. Run
`python3 data/ingest.py` to create a local vector store which the chat endpoint
uses for extra context if available. This step is optional and requires an
internet connection the first time to download embeddings.

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
- `POST /ingest` – rebuild the local vector database from documents (optional).
- `POST /scrape` – return text from a URL or uploaded file.

Set the `OPENAI_API_KEY` environment variable so the chat endpoints use the
OpenAI API. Without an API key the app runs in a limited demo mode that simply
echoes your input.

### Running tests

Before running `pytest`, **you must install the development requirements**:

```bash
pip install -r requirements-dev.txt
```

After the dependencies are installed, run the suite with:

```bash
pytest
```

### Running on Replit

This repository includes a simple `replit.nix` file so that a Python
interpreter is available by default when opened on Replit. The Nix
configuration installs `python3` and `pip`, letting you run the
application without manual setup. After the environment loads, execute
`./setup.sh` to install all Python dependencies. When the `wheels/`
directory contains wheel files the script installs from those prebuilt wheels,
so a network connection is unnecessary.

