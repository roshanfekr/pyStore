#!/usr/bin/env sh
set -e
cd "$(dirname "$0")/.."

if [ -f .venv/Scripts/python.exe ]; then
    PY=.venv/Scripts/python.exe
else
    PY=.venv/bin/python
fi

"$PY" -m pytest "$@"
