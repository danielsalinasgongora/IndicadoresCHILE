#!/usr/bin/env sh
set -eu

if [ "${RUN_UPDATE_ON_STARTUP:-1}" = "1" ]; then
  echo "[entrypoint] Running initial data update..."
  python scripts/update_data.py || echo "[entrypoint] Warning: initial update failed, API will still start."
fi

echo "[entrypoint] Starting API on port ${PORT:-8000}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
