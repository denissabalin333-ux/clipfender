# ClipFender — ЭТАП 7

Дата: 22 сентября 2026

## Изменено

### Legal / privacy
- Добавлены `/privacy`, `/terms`, `/copyright`.
- В footer добавлены ссылки на документы.
- Добавлено удаление аккаунта через `DELETE /api/auth/me` с повторным вводом пароля и CSRF.
- При удалении удаляются сессии, избранное, коллекции, история поиска и сохранённые фильтры.

### SEO / sharing
- Добавлен общий Jinja SEO component.
- Уникальные title/description/robots/canonical/OG/Twitter metadata.
- JSON-LD `WebPage` + `WebSite`.
- `/sitemap.xml`.
- `/robots.txt`.
- `favicon.svg`.
- `manifest.webmanifest`.
- `security.txt`.

### YouTube compliance layer
- Рядом с карточками поиска показано `Источник: YouTube` с переходом к source URL.
- На странице video добавлена явная атрибуция YouTube.
- CSP/Referrer-Policy сохраняют поддержку официального embedded player.
- Deployment documentation содержит текущие ссылки на YouTube API Terms, Developer Policies, Required Minimum Functionality и Branding Guidelines.
- В документации отдельно отмечен release-review для текущего Edit Score как возможного derived metric.

### Privacy-friendly analytics
- Добавлена опциональная Plausible integration.
- По умолчанию отключена.
- При включении сначала показывается consent banner.
- Analytics script загружается только после согласия.

### PWA / offline
- Добавлен `manifest.webmanifest`.
- Добавлен `sw.js`.
- API `/api/*` не кэшируется service worker.
- Добавлен offline fallback.

### CI / deployment
- Добавлен GitHub Actions workflow: Ruff + compileall + pytest.
- Добавлен `pyproject.toml` с Ruff configuration.
- Docker теперь запускается non-root user.
- Добавлен Docker healthcheck.
- Render configuration дополнена `PUBLIC_BASE_URL` и optional Plausible settings.
- `DEPLOY_PUBLIC.md` полностью обновлён под public release.

### Tests
- Добавлены Stage 7 tests для public documents, SEO routes и account deletion.
- Итоговый pytest: 18 passed.

## Создано

- `frontend/components/seo.html`
- `frontend/pages/privacy.html`
- `frontend/pages/terms.html`
- `frontend/pages/copyright.html`
- `frontend/css/stage7-publish.css`
- `frontend/js/stage7-privacy.js`
- `frontend/js/stage7-account.js`
- `frontend/manifest.webmanifest`
- `frontend/sw.js`
- `frontend/offline.html`
- `tests/test_stage7_public.py`
- `.github/workflows/ci.yml`
- `pyproject.toml`
- `CHANGES_STAGE7.md`

## Изменено существующих

- `backend/main.py`
- `backend/api/auth.py`
- `frontend/page_shell.py`
- `frontend/components/footer.html`
- `frontend/archive.html`
- `frontend/pages/library.html`
- `frontend/pages/video.html`
- `frontend/css/app.css`
- `.env.example`
- `render.yaml`
- `requirements-dev.txt`
- `Dockerfile`
- `DEPLOY_PUBLIC.md`
- `README_PUBLIC_SITE.txt`
- public HTML pages received the shared SEO component.

## Перенесено

Только служебные `__pycache__`, созданные проверками, в:

`_archive/generated-stage7/`

Код проекта и старые файлы не удалялись.

## Внешние policy references checked on 22 September 2026

- YouTube API Services Developer Policies
- YouTube API Services Terms of Service (EMEA)
- YouTube API Services Required Minimum Functionality
- YouTube API Services Branding Guidelines
- Google Privacy Policy

Официальные страницы и конкретные release caveats дополнительно зафиксированы в `DEPLOY_PUBLIC.md`.

## Ограничение перед юридическим production launch

На сайте намеренно не выдуманы юридическое имя/адрес оператора. Перед публикацией необходимо заполнить фактические юридические данные владельца сервиса и проверить текст документов с юристом для применимой юрисдикции.

## Verification note

- `pytest -q`: 18 passed.
- `node --check` for active Stage 7 JS: PASS.
- `python -m compileall`: PASS before final cleanup.
- CSS `@import` resolution: 0 missing imports.
- Local HTML asset references: 0 missing.
- Public route smoke executed through the test harness: PASS.
- Ruff is configured in CI, but could not be executed in this sandbox because the `ruff` package is not installed and outbound package installation is unavailable.

The production `clipfinder.db` was restored from the Stage 6 archive after testing and its SHA-256 remains:

`20376bbf27b2be422052d962b71f7f27acce061a43bc16677f15bf1352adc4f3`
