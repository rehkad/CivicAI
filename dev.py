#!/usr/bin/env python3
"""Development server with hot reloading enabled."""

import uvicorn
from api.app import app

if __name__ == "__main__":
    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["api", "data"],
        log_level="debug"
    ) 