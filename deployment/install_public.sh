#!/usr/bin/env bash
set -euo pipefail

echo "[install] IndicadoresCHILE instalación pública"

if ! command -v docker >/dev/null 2>&1; then
  echo "[install] Docker no está instalado."
  echo "[install] Instálalo desde: https://docs.docker.com/engine/install/"
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "[install] Falta Docker Compose plugin."
  echo "[install] Instálalo desde: https://docs.docker.com/compose/install/linux/"
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "[install] curl no está instalado. Instálalo antes de continuar."
  exit 1
fi

if [ ! -f .env ]; then
  cp .env.example .env
  echo "[install] .env creado desde .env.example"
fi

default_origins='ALLOWED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000'
if grep -q "^${default_origins}$" .env; then
  public_ip="$(curl -sS --max-time 5 ifconfig.me || true)"
  if [ -n "$public_ip" ]; then
    sed -i "s#^ALLOWED_ORIGINS=.*#ALLOWED_ORIGINS=http://${public_ip}:8000,http://localhost:8000,http://127.0.0.1:8000#" .env
    echo "[install] ALLOWED_ORIGINS actualizado con IP pública: ${public_ip}"
  else
    echo "[install] No fue posible detectar IP pública automáticamente; se mantiene ALLOWED_ORIGINS por defecto."
  fi
fi

./deployment/deploy.sh

echo "[install] Listo. Comandos útiles:"
echo "  docker compose ps"
echo "  docker compose logs -f dashboard"
