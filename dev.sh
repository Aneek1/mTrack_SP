#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-8765}"

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]]; then
    kill "${BACKEND_PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

echo "Starting backend on :${PORT} ..."
python3 -m uvicorn backend.server:app --port "${PORT}" --reload &
BACKEND_PID="$!"

echo "Starting Electron UI ..."
(cd ui && npm run dev:electron)

