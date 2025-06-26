#!/usr/bin/env bash
set -e

# Detect python3 or python
PY_CMD=$(command -v python3 || command -v python)
if [ -z "$PY_CMD" ]; then
    echo "Python 3 is required." >&2
    exit 1
fi

# Create a virtual environment automatically when none is active
if [ -z "$VIRTUAL_ENV" ]; then
    echo "No virtual environment detected. Using .venv for setup." >&2
    if [ ! -d ".venv" ]; then
        "$PY_CMD" -m venv .venv
    fi
    # shellcheck disable=SC1091
    source .venv/bin/activate
    PY_CMD=$(command -v python)
fi

# Upgrade pip
$PY_CMD -m ensurepip --upgrade
$PY_CMD -m pip install --upgrade pip

# If a local wheels directory exists, install from there
if [ -d "wheels" ]; then
    $PY_CMD -m pip install --no-index --find-links wheels -r requirements.txt
else
    $PY_CMD -m pip install -r requirements.txt
fi
