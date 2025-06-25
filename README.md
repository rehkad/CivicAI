# CivicAI
CivicAI is a self-hosted AI chatbot that answers local government questions—like trash pickup, permits, or municipal codes—using public city data. Easily customizable for any U.S. city with local or cloud LLMs, vector search, and a simple web UI.

## Components

### API
The `api/` directory contains the backend API server. Start developing by editing `api/app.py` and extending the endpoints as needed.

### Web
The `web/` directory is intended for the front-end web application.

### Data
The `data/` directory holds sample datasets or data-loading scripts.

## Running Tests

Run `pytest` from the repository root to execute the test suite:

```bash
pytest
```

This will start a temporary API server and verify that the `/chat` endpoint
responds with JSON.
