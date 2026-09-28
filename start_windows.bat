@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
  set "PY=py -3"
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo Python 3.11+ не найден. Установите Python и повторите запуск.
    exit /b 1
  )
  set "PY=python"
)

if not exist .venv (
  %PY% -m venv .venv
  if errorlevel 1 exit /b 1
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if not exist .env (
  copy /Y .env.example .env >nul
  echo Создан .env из .env.example. Для реального YouTube-поиска укажите YOUTUBE_API_KEY.
)

if "%PORT%"=="" set PORT=8080
if "%ALLOWED_ORIGINS%"=="" set ALLOWED_ORIGINS=http://127.0.0.1:%PORT%,http://localhost:%PORT%
if "%APP_ENV%"=="" set APP_ENV=development

echo ClipFender запущен: http://127.0.0.1:%PORT%/
python -m uvicorn backend.main:app --host 127.0.0.1 --port %PORT% --reload
