# Web

This directory contains a simple single-page chat interface.

## Launching the UI

Any static file server can host the page. The simplest option is Python's built-in `http.server` module:

```bash
cd web
python3 -m http.server 8080
```

Then open [http://localhost:8080](http://localhost:8080) in your browser and interact with the chat.
