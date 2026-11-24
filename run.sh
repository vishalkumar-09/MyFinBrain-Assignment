#!/usr/bin/env bash
# Quick runner script that sets up PYTHONPATH and invokes Python 3.12 with all dependencies.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${SCRIPT_DIR}/.deps:${SCRIPT_DIR}:${PYTHONPATH}"

if [ -f "/snap/core24/1643/usr/bin/python3.12" ]; then
    PYTHON_BIN="/snap/core24/1643/usr/bin/python3.12"
elif command -v python3.12 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3.12)"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
else
    PYTHON_BIN="python"
fi

exec "${PYTHON_BIN}" "$@"
