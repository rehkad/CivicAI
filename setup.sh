#!/usr/bin/env bash
set -e

# Upgrade pip
python -m pip install --upgrade pip

# If a local wheels directory exists, install from there
if [ -d "wheels" ]; then
    python -m pip install --no-index --find-links wheels -r requirements.txt
else
    python -m pip install -r requirements.txt
fi
