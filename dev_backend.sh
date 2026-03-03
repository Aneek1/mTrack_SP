#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-8765}"
python3 -m uvicorn backend.server:app --port "${PORT}" --reload

