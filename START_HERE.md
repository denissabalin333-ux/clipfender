# CLIPFENDER — единая финальная папка

Это основной готовый проект. Не нужно собирать файлы из семи этапов вручную.

> Для локального запуска используйте `start_git_bash.sh` или `start_windows.bat`. Не запускайте `python -m uvicorn ...` из глобального Python: сначала требуется окружение `.venv` и установка `requirements.txt`, иначе появятся ошибки вида `ModuleNotFoundError`.

## 1. Что должно лежать в этой папке

В корне должны быть:

```text
backend/
frontend/
tests/
_archive/
_backup/
clipfinder.db
.env.example
requirements.txt
Dockerfile
docker-compose.yml
start_git_bash.sh
start_windows.bat
render.yaml
```

Папки `_archive/` и `_backup/` нужны для сохранения старого кода и истории изменений. Их не надо удалять.

## 2. Windows / Git Bash

Открой Git Bash в этой папке и выполни:

```bash
./start_git_bash.sh
```

После этого открой:

```text
http://127.0.0.1:8080/
```

Скрипт сам:

1. создаст `.venv`;
2. установит `requirements.txt`;
3. создаст `.env` из `.env.example`, если его ещё нет;
4. запустит FastAPI/Uvicorn.

Для настоящего поиска через YouTube API добавь в `.env`:

```text
YOUTUBE_API_KEY=твой_ключ
```

## 3. Windows без Git Bash

Двойной клик по:

```text
start_windows.bat
```

Либо из CMD:

```bat
start_windows.bat
```

## 4. Docker

Самый простой запуск:

```bash
./start_docker.sh
```

Windows:

```bat
start_docker.bat
```

Или вручную:

```bash
docker compose up --build
```

Сайт будет:

```text
http://127.0.0.1:8080/
```

SQLite для Docker хранится в:

```text
data/clipfinder.db
```

Это отдельная persistent-копия. Она не перезаписывает исходный `clipfinder.db` в корне проекта.

Остановка:

```bash
docker compose down
```

## 5. Render

Используй существующий `render.yaml`.

Обязательные переменные:

```text
YOUTUBE_API_KEY
ALLOWED_ORIGINS
PUBLIC_BASE_URL
```

Для production `ALLOWED_ORIGINS` должен содержать реальный домен, а не `*`.

## 6. Быстрая проверка

После запуска:

```bash
curl http://127.0.0.1:8080/health
```

Ожидается JSON со статусом `ok`.

Затем проверь:

```text
/
/archive
/search
/characters
/guides
/edit-ideas
/video
/library
/login
/contacts
/health
```

## 7. Важно

Не коммить и не публикуй:

```text
.env
YOUTUBE_API_KEY
другие секреты
```

`.env.example` публиковать можно.

Корневой `clipfinder.db` сохранён из проекта. Для production на Render этот Blueprint уже предусматривает Persistent Disk 1 GB и `CLIPFINDER_DB_PATH=/var/lib/clipfender/clipfinder.db`. Для нескольких инстансов используйте PostgreSQL согласно `DEPLOY_PUBLIC.md`. Администратор задаётся через `ADMIN_EMAILS` в Render Environment.


## Production launch

For a public Render deployment, use `render.yaml` from the repository root. Set `YOUTUBE_API_KEY`, `OPENAI_API_KEY`, `ADMIN_EMAILS`, `ALLOWED_ORIGINS`, and `PUBLIC_BASE_URL` as Render environment variables. Keep `APP_ENV=production`. The persistent disk is used for `/var/lib/clipfender`, including SQLite and automatically generated character portraits.

Do not upload `.env` to GitHub or Render source control. Put secrets only in Render Environment Variables/Secrets.
