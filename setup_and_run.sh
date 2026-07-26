#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3.11 or newer is required."
  exit 1
fi

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt

if [ ! -f frontend/dist/index.html ]; then
  if ! command -v npm >/dev/null 2>&1; then
    echo "The prebuilt frontend is missing and Node.js is not installed. Install Node.js 22+, then run this script again."
    exit 1
  fi
  (cd frontend && npm install && npm run build)
fi

[ -f .env ] || cp .env.example .env
python run_app.py
