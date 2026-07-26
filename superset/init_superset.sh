#!/usr/bin/env bash
set -euo pipefail

superset db upgrade
superset fab create-admin \
  --username "${SUPERSET_ADMIN_USERNAME:-admin}" \
  --firstname LedgerFlow \
  --lastname Admin \
  --email "${SUPERSET_ADMIN_EMAIL:-admin@ledgerflow.local}" \
  --password "${SUPERSET_ADMIN_PASSWORD:-admin}" || true
superset init
python /app/pythonpath/bootstrap_ledgerflow.py || true

gunicorn \
  --bind 0.0.0.0:8088 \
  --workers 2 \
  --worker-class gthread \
  --threads 20 \
  --timeout 120 \
  "superset.app:create_app()" &
SERVER_PID=$!
python /app/pythonpath/bootstrap_assets.py || true
wait "$SERVER_PID"
