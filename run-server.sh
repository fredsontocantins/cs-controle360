#!/usr/bin/env bash
set -euo pipefail
CS_API_KEY=${CS_API_KEY:-cs-secret}
CS_ALLOW_UNSECURED_ADMIN=${CS_ALLOW_UNSECURED_ADMIN:-1}
export CS_API_KEY
export CS_ALLOW_UNSECURED_ADMIN
PYTHON_BIN=".venv/bin/python"
if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="$(command -v python3)"
fi
"$PYTHON_BIN" -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
