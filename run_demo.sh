#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mode="${1:-mock}"
if [[ "$mode" != "mock" && "$mode" != "live" ]]; then
  echo "Usage: ./run_demo.sh [mock|live]" >&2
  exit 2
fi
if [[ ! -x .venv/bin/python ]]; then
  python_bin=""
  for candidate in python3.13 python3.12 python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys;raise SystemExit(0 if sys.version_info >= (3,11) else 1)' 2>/dev/null; then python_bin="$candidate"; break; fi
  done
  [[ -n "$python_bin" ]] || { echo "Python 3.11+ is required." >&2; exit 2; }
  "$python_bin" -m venv .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate
  python -m pip install -r requirements-demo.txt
else
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi
if ! python -c 'import fastapi,uvicorn,httpx,yaml,pydantic_settings,multipart,dotenv,pytest' >/dev/null 2>&1; then
  echo "Installing the pinned demo dependencies..."
  python -m pip install -r requirements-demo.txt
fi
exec python scripts/demo.py "$mode"
