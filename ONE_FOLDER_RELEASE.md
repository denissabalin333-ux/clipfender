# ClipFender — One Folder Release

Это единая собранная версия проекта. Для запуска не нужно объединять никакие Stage ZIP вручную.

## Внутри
- backend/
- frontend/
- tests/
- _backup/ — сохранённые исходные версии по этапам
- _archive/ — старые/неактивные файлы, которые не удалялись
- clipfinder.db
- requirements.txt
- .env.example
- Docker/Render конфигурация
- start_git_bash.sh
- start_windows.bat
- start_docker.sh
- start_docker.bat

## Запуск
Git Bash:

    ./start_git_bash.sh

Windows CMD/PowerShell:

    start_windows.bat

Docker:

    start_docker.bat

или

    ./start_docker.sh

После запуска:

    http://127.0.0.1:8080/

Health:

    http://127.0.0.1:8080/health

## Важно
Не запускайте `python -m uvicorn ...` из глобального Python до установки `requirements.txt`. Start-скрипты сами создают `.venv` и ставят зависимости, включая argon2-cffi.
