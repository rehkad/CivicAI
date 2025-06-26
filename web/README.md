# Web

This directory contains a single-page chat interface.
The page now includes a clean layout with chat bubbles for a more polished experience.
Press the **Send** button or hit **Enter** to submit a message.

## Launching the UI

Once the API server is running, open [http://localhost:8000/](http://localhost:8000/) in your browser to chat.
Any static file server can host the page as well. The simplest option is Python's built-in `http.server` module:

```bash
cd web
python3 -m http.server 8080  # or `python -m http.server`
```

Then open [http://localhost:8080](http://localhost:8080) in your browser and interact with the chat.

Messages are sent to the `/chat` endpoint on the API server. When hosting the
front end separately, ensure the FastAPI server is reachable and adjust the
endpoint URL in `index.html` if needed.
