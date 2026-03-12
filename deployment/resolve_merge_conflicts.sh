#!/usr/bin/env bash
set -euo pipefail

BASE_BRANCH="${1:-main}"
CURRENT_BRANCH="$(git branch --show-current)"

if [ -z "${CURRENT_BRANCH}" ]; then
  echo "[merge] No se detectó rama actual"
  exit 1
fi

if ! git remote get-url origin >/dev/null 2>&1; then
  echo "[merge] Falta remoto origin. Configúralo antes de continuar."
  exit 1
fi

echo "[merge] Fetch origin..."
git fetch origin

echo "[merge] Rebase ${CURRENT_BRANCH} sobre origin/${BASE_BRANCH}"
set +e
git rebase "origin/${BASE_BRANCH}"
status=$?
set -e

if [ $status -ne 0 ]; then
  echo "[merge] Hay conflictos. Resuélvelos manualmente y luego ejecuta:"
  echo "        git add <archivos>"
  echo "        git rebase --continue"
  echo "[merge] Si quieres abortar: git rebase --abort"
  exit $status
fi

echo "[merge] Rebase completado. Sube la rama con:"
echo "        git push --force-with-lease origin ${CURRENT_BRANCH}"
