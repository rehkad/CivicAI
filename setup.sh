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
    # Verify that every requirement has a corresponding wheel file
    missing=()
    shopt -s nocaseglob
    while read -r req; do
        req=$(echo "$req" | sed 's/#.*//' | xargs)
        [ -z "$req" ] && continue
        pkg=$(echo "$req" | cut -d'[' -f1 | cut -d'<' -f1 | cut -d'>' -f1 \
            | cut -d'=' -f1 | cut -d' ' -f1 | cut -d';' -f1)
        wheel_pkg=$(echo "$pkg" | tr '[:upper:]' '[:lower:]' | tr '_' '-')
        if ! compgen -G "wheels/${wheel_pkg}-*.whl" > /dev/null; then
            missing+=("$pkg")
        fi
    done < requirements.txt
    shopt -u nocaseglob
    if [ ${#missing[@]} -ne 0 ]; then
        echo "Missing wheel files for packages: ${missing[*]}" >&2
        echo "Run: pip download -r requirements.txt -d wheels while online." >&2
        exit 1
    fi
    $PY_CMD -m pip install --no-index --find-links wheels -r requirements.txt
else
    $PY_CMD -m pip install -r requirements.txt
fi
