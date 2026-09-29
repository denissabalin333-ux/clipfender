# CHANGES_STAGE17.md

## Production hotfix: archive/results + registration

Дата: 2026-09-29
Источник изменений: последний доступный production-пакет ClipFender (`ClipFender_PUBLIC_RELEASE_FINAL_DEPLOY.zip`), который соответствовал версии, отправленной в GitHub перед текущим hotfix.

### 1. БАГ страницы «Результаты поиска» /archive

Причина, подтверждённая в runtime Chromium на текущем коде:

- Активный шаблон: `frontend/archive.html`.
- Поле поиска содержит inline SVG `.cf4-search-icon`.
- На живой проблемной версии браузер рассчитывал этот SVG некорректно/возвращал старое состояние без актуального Stage 15 CSS, из-за чего круг отображался как залитая чёрная точка.
- В текущем source `stage15-release.css` существовал исправляющий контракт, но cache/versioning и явная связь страницы с этим CSS были недостаточно надёжными.
- Дополнительно старый заголовок `.content-shell > .section-title` мог оставаться видимым, поскольку более старое правило ожидало класс `.archive-page`, которого нет на фактическом `<body class="cf4-active">`.

Исправлено:

- `frontend/archive.html` теперь явно подключает `stage15-release.css?v=1510` и новый `stage17-production-hotfix.css?v=1710`.
- `app.css` cache-bust повышен до `v=73.0` на archive.
- SVG получил прямые HTML-атрибуты `width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.7" ...`, чтобы корректный вид не зависел только от внешнего CSS.
- Добавлен `frontend/css/stage17-production-hotfix.css`.
- Добавлено правило `body.cf4-active .content-shell > .section-title { display:none!important; }`.
- Добавлена защита от overflow/неожиданного большого SVG.

Runtime verification after fix:

- Chromium computed width: `18px`
- Chromium computed height: `18px`
- computed fill: `none`
- computed stroke: `rgb(185, 150, 88)`
- legacy result-section title count in the production archive shell: `0`
- browser console errors in the isolated runtime probe: `0`

Evidence: `stage17_archive_after_browser.png`.

### 2. Регистрация / повторный email / отсутствие сессии после регистрации

Фактический backend ранее уже делал duplicate check, но регистрация пользователя и создание initial session выполнялись в отдельных DB transactions/connections. Это оставляло окно, в котором пользователь мог получить успешный response от registration, а session могла не быть доступна на следующем page request.

Исправлено:

- `backend/api/auth.py`: user insert + initial `auth_sessions` insert теперь выполняются в одной транзакции с `BEGIN IMMEDIATE`.
- Duplicate email check теперь использует `lower(trim(email))` и остаётся дополнительно защищённым DB trigger.
- Ошибки уникальности/duplicate trigger преобразуются в `409` вместо внутреннего DB error.
- Response registration содержит `authenticated: true`.
- `backend/security.py`: `create_session()` принимает существующее соединение и может работать внутри внешней транзакции.
- `backend/database/database.py`: добавлены legacy-safe triggers `trg_users_email_unique_insert` и `trg_users_email_unique_update`; существующие записи они не удаляют.
- `frontend/js/site.js`: после регистрации выполняется `/api/auth/me`. При успешной сессии пользователь отправляется в `/archive`. Если runtime не подтвердил сессию, email сохраняется и пользователь отправляется на `/login?email=...&registered=1`.
- Email последнего аккаунта хранится только как UX fallback в `localStorage`, пароль/токен туда не записывается.
- `frontend/pages/login.html`: cache-bust `app.css` поднят до `v=73.0`, `site.js` до `v=7.6`.

Real runtime integration result on the production-equivalent FastAPI app:

```text
POST /api/auth/register       -> 200
response.authenticated        -> true
GET  /api/auth/me             -> authenticated: true
repeat same email             -> 409
```

Это подтверждено отдельным TestClient runtime script после изменений.

### 3. «Найти ролик»

В текущем проекте `/search` является отдельной современной страницей (`frontend/pages/search.html`) и не является тем же route, что `/archive`. На имеющемся пользовательском скриншоте показан именно `archive/results` route, поэтому без отдельного скриншота актуального `/search` не вносилась необоснованная визуальная перестройка этой страницы.

### 4. Сохранение старых файлов

Все затронутые исходные файлы сохранены в `_backup/stage17/` и `_archive/stage17/`.

### 5. Tests

- `python -m compileall -q backend frontend tests` — PASS
- `node --check` для всех frontend JS — PASS
- `pytest -q` — PASS
- Runtime auth integration — PASS
- Chromium layout probe for archive search icon — PASS

Примечание: прямой navigation Chromium к live Render loopback/network в sandbox ограничен средой; для визуальной проверки использовался локальный runtime harness с тем же актуальным HTML/CSS. Это ограничение не выдаётся за полный live browser E2E.
