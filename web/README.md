# Web

This directory contains a single-page chat interface.
The UI now features a sidebar, theme toggle, and persistent conversations stored in your browser.
Press the **Send** button or hit **Enter** to submit a message. Use the **New Chat** button to clear the history.

## Launching the UI

Once the API server is running, open [http://localhost:5000/](http://localhost:5000/) in your browser to chat.
Any static file server can host the page as well. The simplest option is Python's built-in `http.server` module:

```bash
cd web
python3 -m http.server 8080  # or `python -m http.server`
```

Then open [http://localhost:8080](http://localhost:8080) in your browser and interact with the chat.

Messages are sent to the `/chat` endpoint on the API server. When hosting the
front end separately, ensure the FastAPI server is reachable. You can set a
global `API_BASE` variable before loading `index.html` to prefix the endpoint
URLs. For example, if the API is served under `/api`, define
`window.API_BASE = '/api'` and the page will request `${API_BASE}/chat` and
`${API_BASE}/chat_stream` automatically.
