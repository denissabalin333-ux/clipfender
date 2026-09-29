# ClipFender — публичный деплой и release checklist

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

## 2. Production datastore / Render Free

Текущий production-профиль Render Free не использует Persistent Disk и не зависит от локального SQLite-файла. Render Free имеет эфемерную файловую систему, поэтому `clipfinder.db` и пользовательские generated files нельзя считать постоянными.

При заданных `TURSO_DATABASE_URL` и `TURSO_AUTH_TOKEN` приложение переключается на Turso через SQLite-совместимый remote DB-API. Динамические character portraits сохраняются как BLOB в `character_portrait_assets`, поэтому они также переживают restart/redeploy.

Локальный `clipfinder.db` остаётся рабочим fallback для разработки. Публичные API-контракты не меняются.

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
4. `TURSO_DATABASE_URL` и `TURSO_AUTH_TOKEN` заданы для production; Render Persistent Disk для Render Free не используется.
5. `/health` возвращает `200`.
6. `/sitemap.xml`, `/robots.txt`, `/privacy`, `/terms`, `/copyright` доступны.
7. Registration/login/logout работают.
8. Account deletion работает и требует текущий пароль.
9. Search, load-more и video работают.
10. YouTube source attribution виден рядом с API content.
11. Embedded player открывается через официальный YouTube player без overlay над player controls.
12. CI зелёный.
13. Подтверждена compliance-проверка YouTube API Services перед публичным запуском.
