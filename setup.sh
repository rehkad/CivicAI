#!/usr/bin/env bash
set -e

# Upgrade pip
python3 -m ensurepip --upgrade
python3 -m pip install --upgrade pip

# If a local wheels directory exists, install from there
if [ -d "wheels" ]; then
    python3 -m pip install --no-index --find-links wheels -r requirements.txt
else
    python3 -m pip install -r requirements.txt
fi
