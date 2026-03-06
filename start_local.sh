#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_HOST="${BIZON_HOST:-127.0.0.1}"
BACKEND_PORT="${BIZON_BACKEND_PORT:-8000}"
FRONTEND_PORT="${BIZON_FRONTEND_PORT:-3000}"

export PYTHONPATH="${ROOT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
export npm_config_cache="${npm_config_cache:-${ROOT_DIR}/.npm-cache}"

if [[ ! -d "${ROOT_DIR}/gui-web/node_modules" ]]; then
  echo "Missing gui-web/node_modules. Run: cd gui-web && npm install" >&2
  exit 1
fi

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]]; then
    kill "${BACKEND_PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

echo "Starting backend on http://${APP_HOST}:${BACKEND_PORT}"
(cd "${ROOT_DIR}" && python3 -m uvicorn backend.main:app --host "${APP_HOST}" --port "${BACKEND_PORT}") &
BACKEND_PID=$!

echo "Starting frontend on http://${APP_HOST}:${FRONTEND_PORT}"
cd "${ROOT_DIR}/gui-web"
npm run dev -- --host "${APP_HOST}" --port "${FRONTEND_PORT}"
