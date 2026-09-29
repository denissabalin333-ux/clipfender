# ClipFender — Render Free + Turso (без Persistent Disk)

Этот профиль развёртывания рассчитан на Render Free без локального Persistent Disk.

## Архитектура

- Render Free Web Service запускает FastAPI.
- Turso хранит постоянную SQLite-совместимую БД.
- generated character portraits хранятся как BLOB в таблице `character_portrait_assets` той же Turso БД.
- локальный SQLite остаётся доступным для разработки, если `TURSO_DATABASE_URL` не задан.

## Переменные Render

Обязательные секреты:

- `YOUTUBE_API_KEY`
- `TURSO_DATABASE_URL`
- `TURSO_AUTH_TOKEN`
- `ALLOWED_ORIGINS`
- `PUBLIC_BASE_URL`
- `ADMIN_EMAILS`
- `ADMIN_BOOTSTRAP_PASSWORD` — только до первого успешного bootstrap
- `OPENAI_API_KEY` — если нужна автоматическая генерация портретов

`CHARACTER_IMAGE_SEARCH_ENABLED` в production должен оставаться `0`.

## Создание Turso

Создайте бесплатную Turso database и token в Turso Dashboard/CLI. Текущий Free-план Turso заявлен как `$0/month`, без банковской карты, с 5 GB хранения. После создания database вставьте URL вида `libsql://...` и auth token в Render Environment Variables.

## Важно про Render Free

Render Free имеет эфемерную файловую систему: локальная SQLite БД и сгенерированные файлы теряются при restart/redeploy/spin-down. Поэтому production код при наличии `TURSO_DATABASE_URL` вообще не должен полагаться на `/var/lib/clipfender`.

Free web service может засыпать после периода без трафика. Поэтому первый запрос после idle может занять заметно дольше обычного.

## Первый запуск

1. Создайте Turso database.
2. Получите `TURSO_DATABASE_URL` и `TURSO_AUTH_TOKEN`.
3. Добавьте их в Render Environment Variables.
4. Добавьте YouTube/OpenAI/admin secrets.
5. Deploy Blueprint.
6. Проверьте `/health`.
7. Войдите под `ADMIN_EMAILS` + `ADMIN_BOOTSTRAP_PASSWORD`.
8. После успешного bootstrap удалите `ADMIN_BOOTSTRAP_PASSWORD` из Render.

## Локальный режим

Без `TURSO_DATABASE_URL` проект продолжает использовать обычный `clipfinder.db`.
