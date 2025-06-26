# Web

This directory contains a single-page chat interface.
The page now includes a clean layout with chat bubbles for a more polished experience.
Press the **Send** button or hit **Enter** to submit a message.

## Launching the UI

Any static file server can host the page. The simplest option is Python's built-in `http.server` module:

```bash
cd web
python3 -m http.server 8080  # or `python -m http.server`
```

Then open [http://localhost:8080](http://localhost:8080) in your browser and interact with the chat.

Messages are sent to the API server running on `http://localhost:8000/chat`, so
ensure the FastAPI server is active.
