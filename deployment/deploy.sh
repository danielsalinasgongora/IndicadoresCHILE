#!/usr/bin/env bash
set -euo pipefail

ensure_prereqs() {
  command -v docker >/dev/null 2>&1 || { echo "[deploy] docker no está instalado"; exit 1; }
  docker compose version >/dev/null 2>&1 || { echo "[deploy] docker compose plugin no disponible"; exit 1; }
  command -v curl >/dev/null 2>&1 || { echo "[deploy] curl no está instalado"; exit 1; }
}

generate_secure_key() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -base64 48 | tr -d '\n' | tr '/+' '_-'
  else
    # Fallback portable sin dependencias adicionales
    python - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
  fi
}

read_env_value() {
  local key="$1"
  local default_value="$2"
  local file=".env"

  if [ ! -f "$file" ]; then
    echo "$default_value"
    return
  fi

  local value
  value="$(grep -E "^${key}=" "$file" | tail -n1 | cut -d '=' -f2- || true)"
  if [ -z "$value" ]; then
    echo "$default_value"
  else
    echo "$value"
  fi
}

generate_admin_key_if_needed() {
  local current_key
  current_key="$(read_env_value "ADMIN_API_KEY" "")"

  if [ -z "$current_key" ] || [ "$current_key" = "change-this-in-production" ]; then
    local new_key
    new_key="$(generate_secure_key)"
    if grep -q '^ADMIN_API_KEY=' .env; then
      sed -i "s#^ADMIN_API_KEY=.*#ADMIN_API_KEY=${new_key}#" .env
    else
      printf '\nADMIN_API_KEY=%s\n' "$new_key" >> .env
    fi
    echo "[deploy] ADMIN_API_KEY generada automáticamente en .env"
  fi
}

ensure_prereqs

if [ ! -f .env ]; then
  echo "[deploy] .env no existe. Copiando desde .env.example..."
  cp .env.example .env
fi

generate_admin_key_if_needed

APP_PORT="$(read_env_value "APP_PORT" "8000")"

echo "[deploy] Building and starting containers..."
docker compose up -d --build

echo "[deploy] Waiting for service health..."
for i in {1..45}; do
  if curl -fsS "http://127.0.0.1:${APP_PORT}/api/health" >/dev/null; then
    local_ip="$(hostname -I | awk '{print $1}' || true)"
    if [ -z "${local_ip}" ]; then
      local_ip="localhost"
    fi
    echo "[deploy] Service is up: http://127.0.0.1:${APP_PORT}"
    echo "[deploy] Dashboard URL (LAN): http://${local_ip}:${APP_PORT}"
    exit 0
  fi
  sleep 2
done

echo "[deploy] Service did not become healthy in time"
exit 1
