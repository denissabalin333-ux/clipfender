@echo off
setlocal
cd /d "%~dp0"
where docker >nul 2>nul
if errorlevel 1 (
  echo Docker не найден. Установите Docker Desktop и повторите запуск.
  exit /b 1
)
if not exist .env (
  copy /Y .env.example .env >nul
  echo Создан .env из .env.example. Для YouTube-поиска укажите YOUTUBE_API_KEY.
)
docker compose up --build
