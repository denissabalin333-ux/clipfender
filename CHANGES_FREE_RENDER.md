# ClipFender — Render Free без Persistent Disk

Дата: 2026-09-29

## Что изменено

1. `render.yaml` теперь использует `plan: free` и больше не содержит `disk:` или `CLIPFINDER_DB_PATH`.
2. Production datastore переключается на Turso при наличии `TURSO_DATABASE_URL` и `TURSO_AUTH_TOKEN`; локальный `clipfinder.db` остаётся fallback для разработки.
3. Добавлен sqlite3-совместимый remote adapter `backend/database/remote.py` для Turso serverless DB-API: qmark SQL, named/indexed rows, cursor lifecycle и `lastrowid`.
4. Добавлена таблица `character_portrait_assets`; в remote режиме generated portraits сохраняются как BLOB в Turso и отдаются через `/media/characters/{slug}.webp`.
5. `character_catalog.py` больше не пишет generated portraits на Render filesystem при remote DB mode.
6. `CHARACTER_IMAGE_SEARCH_ENABLED` в production установлен в `0`; AI generation остаётся доступной через `OPENAI_API_KEY`.
7. `.env.example`, Docker Compose и deployment docs обновлены под Turso.
8. Проверен rollback при ошибке записи remote profile/portrait.

## Почему так

Render Free имеет эфемерную файловую систему, поэтому SQLite-файл и новые generated images нельзя считать постоянными. Turso предоставляет удалённую SQLite-совместимую БД; текущий Free-план на сайте Turso указан как `$0/month`, без банковской карты, с 5 GB хранения.

## Ограничение проверки

В текущем sandbox нет установленного `turso_serverless`, поэтому реальный запрос к аккаунту Turso выполнить здесь невозможно. Remote adapter проверен unit-тестом на DB-API контракте; production connectivity нужно проверить после создания Turso database через `/health`.
