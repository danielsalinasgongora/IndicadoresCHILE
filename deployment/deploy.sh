#!/usr/bin/env bash
set -euo pipefail

ensure_prereqs() {
  command -v docker >/dev/null 2>&1 || { echo "[deploy] docker no está instalado"; exit 1; }
  docker compose version >/dev/null 2>&1 || { echo "[deploy] docker compose plugin no disponible"; exit 1; }
  command -v curl >/dev/null 2>&1 || { echo "[deploy] curl no está instalado"; exit 1; }
}

generate_admin_key_if_needed() {
  current_key="$(grep -E '^ADMIN_API_KEY=' .env | cut -d '=' -f2- || true)"
  if [ -z "$current_key" ] || [ "$current_key" = "change-this-in-production" ]; then
    new_key="$(python - <<'PY'
import secrets
print(secrets.token_urlsafe(32))
PY
)"
    if grep -q '^ADMIN_API_KEY=' .env; then
      sed -i "s#^ADMIN_API_KEY=.*#ADMIN_API_KEY=${new_key}#" .env
    else
      printf '\nADMIN_API_KEY=%s\n' "$new_key" >> .env
    fi
    echo "[deploy] ADMIN_API_KEY generado automáticamente en .env"
  fi
}

ensure_prereqs

if [ ! -f .env ]; then
  echo "[deploy] .env no existe. Copiando desde .env.example..."
  cp .env.example .env
fi

generate_admin_key_if_needed

set -a
source .env
set +a

echo "[deploy] Building and starting containers..."
docker compose up -d --build

echo "[deploy] Waiting for service health..."
for i in {1..45}; do
  if curl -fsS "http://127.0.0.1:${APP_PORT:-8000}/api/health" >/dev/null; then
    echo "[deploy] Service is up: http://127.0.0.1:${APP_PORT:-8000}"
    echo "[deploy] Dashboard URL: http://$(hostname -I | awk '{print $1}'):${APP_PORT:-8000}"
    exit 0
  fi
  sleep 2
done

echo "[deploy] Service did not become healthy in time"
exit 1
