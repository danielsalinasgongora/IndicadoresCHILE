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
    return
  fi

  if [ -r /dev/urandom ] && command -v base64 >/dev/null 2>&1; then
    head -c 48 /dev/urandom | base64 | tr -d '\n' | tr '/+' '_-'
    return
  fi

  echo "[deploy] No se pudo generar ADMIN_API_KEY automáticamente (faltan openssl/base64)."
  echo "[deploy] Define ADMIN_API_KEY manualmente en .env"
  exit 1
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

set_env_value() {
  local key="$1"
  local value="$2"
  if grep -q "^${key}=" .env; then
    sed -i "s#^${key}=.*#${key}=${value}#" .env
  else
    printf '\n%s=%s\n' "$key" "$value" >> .env
  fi
}

is_port_in_use() {
  local port="$1"

  if command -v ss >/dev/null 2>&1; then
    ss -ltn | awk '{print $4}' | grep -Eq "(^|:)${port}$"
    return
  fi

  if command -v lsof >/dev/null 2>&1; then
    lsof -iTCP -sTCP:LISTEN -P -n | awk '{print $9}' | grep -Eq "(^|:)${port}$"
    return
  fi

  if command -v netstat >/dev/null 2>&1; then
    netstat -ltn 2>/dev/null | awk '{print $4}' | grep -Eq "(^|:)${port}$"
    return
  fi

  # fallback: if no checker available, assume free
  return 1
}

choose_available_port() {
  local current_port="$1"

  if ! is_port_in_use "$current_port"; then
    echo "$current_port"
    return
  fi

  echo "[deploy] El puerto ${current_port} ya está en uso en el host."

  if [ -t 0 ]; then
    while true; do
      read -r -p "[deploy] Ingresa otro puerto (ej: 8080): " new_port
      if ! echo "$new_port" | grep -Eq '^[0-9]{2,5}$'; then
        echo "[deploy] Puerto inválido."
        continue
      fi
      if [ "$new_port" -lt 1 ] || [ "$new_port" -gt 65535 ]; then
        echo "[deploy] Puerto fuera de rango (1-65535)."
        continue
      fi
      if is_port_in_use "$new_port"; then
        echo "[deploy] El puerto ${new_port} también está ocupado."
        continue
      fi
      echo "$new_port"
      return
    done
  fi

  echo "[deploy] Entorno no interactivo y puerto ocupado."
  echo "[deploy] Define APP_PORT manualmente en .env y reintenta."
  exit 1
}

generate_admin_key_if_needed() {
  local current_key
  current_key="$(read_env_value "ADMIN_API_KEY" "")"

  if [ -z "$current_key" ] || [ "$current_key" = "change-this-in-production" ]; then
    local new_key
    new_key="$(generate_secure_key)"
    set_env_value "ADMIN_API_KEY" "$new_key"
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
APP_PORT="$(choose_available_port "$APP_PORT")"
set_env_value "APP_PORT" "$APP_PORT"

echo "[deploy] Usando APP_PORT=${APP_PORT}"

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
