#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo "Run ./setup_and_run.sh first."
  exit 1
fi
.venv/bin/python run_app.py
