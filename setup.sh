#!/usr/bin/env bash
set -e

# Ensure Python 3 is installed
if ! command -v python3 >/dev/null && ! command -v python >/dev/null; then
    echo "Error: Python 3 is required but was not found." >&2
    exit 1
fi

# Upgrade pip
python3 -m ensurepip --upgrade
python3 -m pip install --upgrade pip

# If a local wheels directory exists, install from there
if [ -d "wheels" ]; then
    python3 -m pip install --no-index --find-links wheels -r requirements.txt
else
    python3 -m pip install -r requirements.txt
fi
