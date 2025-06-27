#!/usr/bin/env bash
set -e

PY_CMD=$(command -v python3 || command -v python)
if [ -z "$PY_CMD" ]; then
    echo "Python 3 is required." >&2
    exit 1
fi

if [ ! -d ".venv" ]; then
    "$PY_CMD" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

./setup.sh

.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload --log-level debug
