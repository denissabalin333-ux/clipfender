# ClipFender — публичный деплой и release checklist


## 0A. Final production character catalog storage

Dynamic character portraits are stored outside the source tree:

```text
CHARACTER_STORAGE_DIR=/var/lib/clipfender/characters
```

The Render persistent disk is mounted at `/var/lib/clipfender`, so both SQLite and generated portraits survive restarts/redeploys. Render documents that only data written under the disk mount path persists; a paid web service is required for a persistent disk.

The old Bing Image Search path is intentionally disabled because the Bing Search APIs were retired. Production uses the OpenAI image-generation fallback for new portraits when `OPENAI_API_KEY` is configured.

## 0B. Required Render secrets

Set these in the Render Dashboard as secret environment variables (never commit them):

```text
YOUTUBE_API_KEY=...
OPENAI_API_KEY=...
ADMIN_EMAILS=you@example.com
ALLOWED_ORIGINS=https://your-real-domain.example
PUBLIC_BASE_URL=https://your-real-domain.example
```

The application returns HTTP 503 from `/health` in production when any required value is missing or when the image-generation feature is enabled without `OPENAI_API_KEY`. This intentionally prevents a deployment from being considered healthy while a required production dependency is absent.

## 1. Canonical production configuration

Минимальный набор:

```text
YOUTUBE_API_KEY=...
APP_ENV=production
ALLOWED_ORIGINS=https://your-domain.example
PUBLIC_BASE_URL=https://your-domain.example
```

`ALLOWED_ORIGINS=*` в production запрещён приложением.

`PUBLIC_BASE_URL` нужен для canonical URL, Open Graph, sitemap и `security.txt`.

## 2. SQLite / Render

Текущий проект хранит search cache, quota state, пользователей, сессии, библиотеку, contact messages и rate-limit state в SQLite.

В текущем `render.yaml` Persistent Disk уже описан: `/var/lib/clipfender`, 1 GB, а приложение получает `CLIPFINDER_DB_PATH=/var/lib/clipfender/clipfinder.db`. Без постоянного диска Render использует эфемерную файловую систему, и SQLite может исчезнуть после redeploy/restart. Для нескольких инстансов вместо SQLite используйте PostgreSQL.

Для нескольких независимых инстансов/горизонтального масштабирования предпочтителен PostgreSQL. Публичные API при миграции должны остаться без изменений.

## 3. YouTube API compliance

ClipFender использует YouTube API Services. До production launch владелец проекта должен регулярно сверять актуальные документы YouTube:

- YouTube API Services Developer Policies: https://developers.google.com/youtube/terms/developer-policies
- YouTube API Services Terms of Service (EMEA): https://developers.google.com/youtube/terms/api-services-terms-of-service-emea
- Required Minimum Functionality: https://developers.google.com/youtube/terms/required-minimum-functionality
- Branding Guidelines: https://developers.google.com/youtube/terms/branding-guidelines
- YouTube Terms of Service: https://www.youtube.com/t/terms

По актуальной Developer Policy обычные неавторизованные API-данные могут временно храниться не дольше 30 календарных дней, после чего их нужно удалить или обновить; ClipFender чистит video cache и search_state примерно через 24 часа. Это должно периодически проверяться владельцем проекта на соответствие текущей политике. YouTube также требует показывать актуальные API Data и соблюдать требования embedded player. В проекте для player установлен `Referrer-Policy: strict-origin-when-cross-origin`, который YouTube рекомендует для идентификации API Client. 

Отдельное внимание: текущий `Edit Score` вычисляется из метаданных и статистики найденных видео. В 2026 году YouTube добавил дополнительную политику для derived metrics и отдельные условия хранения статистики для аудированных разработчиков. Перед коммерческим/широким релизом владелец должен проверить в Google Cloud / YouTube API Services Compliance, подпадает ли текущая формула score под эти правила и требуется ли отдельное разрешение. Не считать наличие этого локального score автоматически одобренным YouTube API.

## 4. Авторизация и приватность

- Пароли хранятся как Argon2 hashes.
- Session cookie — `HttpOnly`.
- CSRF token проверяется сервером.
- Аккаунт можно удалить в разделе «Моя библиотека».
- При удалении удаляются account data, sessions, favorites, collections, search history и saved filters.

Privacy page:

```text
/privacy
```

Terms:

```text
/terms
```

Copyright / complaints:

```text
/copyright
```

## 5. Analytics

По умолчанию аналитика выключена.

Для Plausible:

```text
PLAUSIBLE_DOMAIN=your-domain.example
PLAUSIBLE_SCRIPT_URL=https://plausible.io/js/script.js
```

При включённой аналитике пользователь сначала видит consent banner. Только после согласия загружается analytics script.

## 6. SEO

Доступны:

```text
/sitemap.xml
/robots.txt
/manifest.webmanifest
/favicon.svg
/.well-known/security.txt
```

`PUBLIC_BASE_URL` должен указывать на канонический публичный origin.

SEO shell добавляет:

- unique title;
- meta description;
- canonical;
- Open Graph;
- Twitter card;
- JSON-LD WebPage/WebSite;
- robots policy.

Страницы входа, библиотеки и 404 отмечены `noindex`.

## 7. PWA

Service worker:

```text
/sw.js
```

Он не перехватывает `/api/*`, поэтому API не получает устаревший cache. Статические ресурсы кешируются с fallback на `/offline.html`.

## 8. Docker

```bash
docker build -t clipfender .

docker run --rm -p 8080:8080 \
  -e YOUTUBE_API_KEY="..." \
  -e APP_ENV=production \
  -e ALLOWED_ORIGINS="https://your-domain.example" \
  -e PUBLIC_BASE_URL="https://your-domain.example" \
  clipfender
```

Docker запускает приложение не от root и содержит `/health` healthcheck.

## 9. CI

GitHub Actions выполняет:

```bash
ruff check backend tests frontend
python -m compileall -q backend frontend
pytest -q
```

Workflow:

```text
.github/workflows/ci.yml
```

## 10. Финальный manual checklist

Перед publication проверить:

1. `PUBLIC_BASE_URL` совпадает с реальным HTTPS доменом.
2. `ALLOWED_ORIGINS` не содержит `*`.
3. YouTube API key находится только в secret/environment.
4. Render Persistent Disk включён для SQLite или выполнена миграция на PostgreSQL.
5. `/health` возвращает `200`.
6. `/sitemap.xml`, `/robots.txt`, `/privacy`, `/terms`, `/copyright` доступны.
7. Registration/login/logout работают.
8. Account deletion работает и требует текущий пароль.
9. Search, load-more и video работают.
10. YouTube source attribution виден рядом с API content.
11. Embedded player открывается через официальный YouTube player без overlay над player controls.
12. CI зелёный.
13. Подтверждена compliance-проверка YouTube API Services перед публичным запуском.


## 11. First production deployment — exact order

1. Push the repository to GitHub without `.env` or database files.
2. In Render create a Blueprint from `render.yaml`.
3. Make sure the web service has the Persistent Disk mounted at `/var/lib/clipfender`. A Render persistent disk preserves only files written under that mount path and requires a paid service.
4. Set `YOUTUBE_API_KEY`, `OPENAI_API_KEY`, `ADMIN_EMAILS`, `ADMIN_BOOTSTRAP_PASSWORD`, `ALLOWED_ORIGINS`, and `PUBLIC_BASE_URL` in Render Environment Variables. Never put real secrets in `render.yaml` or Git.
5. Keep `CHARACTER_IMAGE_SEARCH_ENABLED=0`; the legacy Bing Image Search integration is disabled.
6. Deploy and open `/health`. It must return HTTP 200 with `status=ok`.
7. Log in using the allowlisted admin email and the bootstrap password. Once the account exists, remove `ADMIN_BOOTSTRAP_PASSWORD` from Render.
8. Run one real YouTube search and one new-character discovery. Confirm the portrait URL is under `/media/characters/` and remains available after a restart.
9. Only after these checks point the domain DNS at the Render service.
