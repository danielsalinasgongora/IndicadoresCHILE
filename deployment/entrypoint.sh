#!/usr/bin/env sh
set -eu

if [ "${RUN_UPDATE_ON_STARTUP:-1}" = "1" ]; then
  echo "[entrypoint] Running initial data update..."
  python scripts/update_data.py || echo "[entrypoint] Warning: initial update failed, API will still start."
fi

PORT="${PORT:-8000}"
FORWARDED_ALLOW_IPS="${FORWARDED_ALLOW_IPS:-*}"
PROXY_HEADERS="${PROXY_HEADERS:-1}"

echo "[entrypoint] Starting API on port ${PORT}"

if [ "$PROXY_HEADERS" = "1" ]; then
  exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --proxy-headers \
    --forwarded-allow-ips "$FORWARDED_ALLOW_IPS"
else
  exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "$PORT"
fi
