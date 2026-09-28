#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if ! command -v docker >/dev/null 2>&1; then
  echo "Docker не найден. Установите Docker Desktop и повторите запуск."
  exit 1
fi
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Создан .env из .env.example. Для YouTube-поиска укажите YOUTUBE_API_KEY."
fi
docker compose up --build
