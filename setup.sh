#!/usr/bin/env bash
set -e

# Allow installs to fail in offline environments


# Upgrade pip
python -m pip install --upgrade pip || true

# If a local wheels directory exists, install from there
if [ -d "wheels" ]; then
    python -m pip install --no-index --find-links wheels -r requirements.txt || true
else
    python -m pip install -r requirements.txt || true
fi
