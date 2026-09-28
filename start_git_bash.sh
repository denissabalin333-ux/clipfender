#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

PYTHON_BIN="${PYTHON_BIN:-python}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python не найден. Установите Python 3.11+ и повторите запуск."
  exit 1
fi

if [ ! -d .venv ]; then
  "$PYTHON_BIN" -m venv .venv
fi

source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Создан .env из .env.example. Для реального YouTube-поиска укажите YOUTUBE_API_KEY."
fi

export APP_ENV="${APP_ENV:-development}"
export ALLOWED_ORIGINS="${ALLOWED_ORIGINS:-http://127.0.0.1:8080,http://localhost:8080}"
export PORT="${PORT:-8080}"

echo "ClipFender запущен: http://127.0.0.1:${PORT}/"
python -m uvicorn backend.main:app --host 127.0.0.1 --port "$PORT" --reload
