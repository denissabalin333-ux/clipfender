# CLIPFENDER — FINAL PUBLIC RELEASE

> Канонический способ локального запуска — `start_git_bash.sh` или `start_windows.bat`. Эти скрипты создают `.venv` и ставят все зависимости из `requirements.txt`, включая `argon2-cffi`.

Это единая рабочая папка проекта. Промежуточные ZIP этапов собирать вместе не требуется.

## Запуск

### Git Bash / Windows

```bash
./start_git_bash.sh
```

или Windows:

```text
start_windows.bat
```

### Docker

```bash
./start_docker.sh
```

или Windows:

```text
start_docker.bat
```

## После запуска

Открой:

```text
http://127.0.0.1:8080/
```

Проверка:

```text
http://127.0.0.1:8080/health
```

## Что нужно настроить

Сначала создаётся `.env` из `.env.example`.

Для реального поиска:

```text
YOUTUBE_API_KEY=...
```

Для production:

```text
APP_ENV=production
ALLOWED_ORIGINS=https://ваш-домен
PUBLIC_BASE_URL=https://ваш-домен
```

Не публикуй `.env` и секретные ключи.

## Структура

```text
backend/       FastAPI + API
frontend/      HTML/CSS/JS
frontend/pages страницы
frontend/components общий shell
_database/     — нет: SQLite лежит в корне
clipfinder.db  исходная локальная БД
_archive/      сохранённый старый код и этапы
_backup/       резервные копии изменённых файлов
tests/         pytest
Dockerfile
 docker-compose.yml
render.yaml
requirements.txt
.env.example
```

## Что проверено перед упаковкой

- pytest: 18 passed
- Python compile: PASS
- JavaScript syntax: PASS
- статические ссылки: PASS
- реальный Uvicorn smoke с временной YouTube-заглушкой: PASS
- все публичные страницы и SEO endpoints: 200
- `clipfinder.db` сохранён побайтно исходным
- `.env` в релизный пакет не включён
- промежуточных ZIP внутри проекта нет


## Stage 16 production hardening

The final deployment package stores auto-generated character portraits on the same persistent Render disk as SQLite. The retired Bing Image Search integration is disabled. Environment loading occurs before environment-sensitive backend modules import their configuration. Production `/health` reports 503 until required deployment secrets/configuration are present.

## Final deployment hardening

- `.env` stays outside Git/Docker build context.
- Internal `_archive/` and `_backup/` snapshots are ignored by Git and Docker but remain in the local release ZIP.
- Dynamic portraits use the Render persistent disk at `/var/lib/clipfender/characters`.
- Production health fails closed until required secrets/configuration are present.
- Bootstrap admin can be created once from `ADMIN_BOOTSTRAP_PASSWORD`; remove that secret after the first successful login.
