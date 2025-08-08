#!/usr/bin/env bash
set -euo pipefail

# Ensure virtual environment and dependencies
if [ -z "${VIRTUAL_ENV:-}" ]; then
  if [ ! -d ".venv" ]; then
    echo "Creating virtual environment (.venv)"
    python3 -m venv .venv || python -m venv .venv
  fi
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

if ! python -c "import fastapi" >/dev/null 2>&1; then
  echo "Installing dependencies..."
  pip install -r requirements.txt
fi

# Kill any existing processes on port 8000
if lsof -ti:8000 >/dev/null 2>&1; then
  echo "Killing processes on port 8000"
  lsof -ti:8000 | xargs kill -9 2>/dev/null || true
fi

echo "Starting CivicAI server on http://localhost:8000"
exec uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload --log-level info
