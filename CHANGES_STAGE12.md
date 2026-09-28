# CLIPFENDER — STAGE 12 FINAL PRE-RELEASE AUDIT

Дата: 2026-09-26

## 0. Исходная точка и расхождения с заданием

Работа выполнена по актуальному `ClipFender_PUBLIC_RELEASE_STAGE11_FINAL.zip`.

В актуальном ZIP описание бага с персонажами уже частично отличалось от старой версии: активный `frontend/pages/characters.html` содержал не 3 fake-карточки, а 6 жёстко зашитых карточек с существующими `*-hq.webp`. Архитектура всё равно оставалась неверной: каталог не строился из `CHARACTER_PROFILES`, отсутствовал Барристан Селми и не было фильтров каталога.

Для фильтров `/filters` как отдельного рабочего маршрута в актуальном backend не существует. Реальный блок фильтров находится внутри `/archive` в `#filters`; в Stage 12 проверен и исправлен именно этот активный путь.

---

## 1. БАГ 1 — реальные персонажи вместо hardcode

### Причина

`frontend/pages/characters.html` был standalone-шаблоном с вручную перечисленными карточками. `backend/main.py` передавал страницу без каталога `CHARACTER_PROFILES`.

### Что исправлено

- `backend/character_profiles.py`: добавлен профиль `barristan-selmy`.
- Использован существующий реальный asset:
  `/static/assets/reference/final/barristan-hq.webp`.
- `backend/main.py`: добавлен каталог `_available_character_catalog()`, который отдаёт только профили с реально существующим static portrait.
- `/characters` теперь передаёт в Jinja:
  - `characters`
  - `character_houses`
  - `character_edit_profiles`
- Старый standalone `characters.html` сохранён в `_archive/frontend/pages/characters.html` и исходная версия также сохранена в `_backup/stage12/`.
- Новый `frontend/pages/characters.html` использует общий header/footer и `app.css`, без старого inline-CSS островка.
- Карточки используют реальные `character.image`, `name`, `house`, `summary`, `slug`, `query`, `edit_profile`.
- Добавлены фильтры:
  - поиск по имени;
  - дом/принадлежность;
  - `edit_profile`.
- Значения профилей строятся из реальных данных каталога.
- Sitemap персонажей теперь формируется из `CHARACTER_PROFILES` только для реально существующих portrait assets.

### Browser DOM check

Результат из Chromium DOM harness:

- карточек: **7**;
- Barristan: найден **1**;
- initial visible: **7/7**;
- фильтр Ланнистер: Джейми, Тирион, Серсея;
- профиль `action`: Джон, Джейми, Дейенерис, Арья, Барристан;
- поиск `Барристан`: **1** карточка.

Кнопка сохранения персонажа в изолированном `set_content` harness не использовалась как production verdict: browser sandbox не предоставляет normal origin/localStorage, поэтому состояние `localStorage` там нельзя считать проверкой production-origin. Сам production JS использует `localStorage` на обычном сайте.

---

## 2. БАГ 2 — фильтры архива

### Причина №1: противоречивый CSS

В `frontend/css/final-v7.css` одновременно существовали:

- `body.cf4-active .filters-wrap { display:none!important }`
- ниже `body.cf4-active .filters-wrap { display:block!important; ... }`

Это было устранено. В активном `final-v7.css` оставлено **одно** правило:

`body.cf4-active .filters-wrap { display:block!important; width:100%!important; margin-top:18px!important }`

### `final-v4.css`

`frontend/css/app.css` не импортирует `final-v4.css`, активные страницы также не подключают его для archive. `final-v4.css` не используется текущим `/archive`.

Отдельное упоминание `final-v4.css` осталось только внутри `frontend/components/component-kit.html`; этот legacy/component-kit файл не подключается как stylesheet источником активного archive flow.

### Причина №2: фильтры не запускали новый поиск

`archive.html` умел собирать параметры в `buildSearchUrl()`, но изменения select/input не запускали повторный `searchVideos()`.

Добавлен:

`frontend/js/stage12-archive-filters.js`

Он:

- слушает `change` для select/input;
- debounce-ит текстовые/числовые input;
- повторно вызывает существующий `searchVideos()`;
- не отправляет запрос до первого поискового запроса;
- не меняет контракт `/api/search`.

### Реальный HTTP before/after

На изолированном тестовом наборе из 4 материалов:

**До:**
`Stage12FilterTest` → **4 результата**.

**После выбора `action=true`:**
→ **2 результата** (`stage12-0`, `stage12-2`).

**После `duration_max=30`:**
→ **2 результата** (`stage12-0`, `stage12-2`).

Проверено, что параметры реально присутствуют в URL `/api/search` и backend применяет их к выдаче.

`edit_min_score=90` намеренно не использован как пример before/after: backend рассчитывает edit score самостоятельно, поэтому такой искусственный тестовый набор закономерно не давал результата. Для отчёта использованы реальные рабочие фильтры `action` и `duration`.

### Responsive

Статический DOM/layout smoke охватывал целевые desktop/mobile widths. Полный Playwright resize-run был прерван EPIPE внутри Playwright driver после нескольких context resize, поэтому это **не выдаётся за полноценный end-to-end browser verdict**. Реальная серверная фильтрация и видимость активного `#filters` проверены отдельно.

---

## 3. БАГ 3 — безопасность и публичный релиз

### Аутентификация

**Безопасно:**

- пароли хэшируются через Argon2 (`argon2-cffi` / `PasswordHasher`);
- session cookie в production: `HttpOnly`, `Secure`, `SameSite=Lax`;
- CSRF cookie отделён от HttpOnly session cookie.

### Brute force / login rate limit

**Безопасно:** после последовательных неверных логинов лимитер реально возвращал `429` после установленного порога.

### CSRF

**Безопасно:** POST без корректного CSRF токена даёт `403` для чувствительных форм/API; проверены auth/contact/reports/library flows.

### SQL injection

**Безопасно:** активные SQL-запросы используют параметризованные значения `?`; пользовательский ввод не конкатенируется в SQL.

### XSS

**В основном безопасно:** динамический HTML в JS использует `escapeHtml`/`esc`, Jinja templates autoescape. `script-src` текущего CSP содержит `unsafe-inline`, поэтому CSP остаётся точкой для будущего hardening; удаление этого флага потребовало бы переноса legacy inline scripts в nonce/hash/external flow.

### `/admin`

**Исправлено и безопасно:** раньше page-route `/admin` был доступен без прав; теперь:

- без session → `401`;
- обычный user → `403`;
- allowlisted admin → `200`.

API `/api/admin/*` сохраняет собственную `require_admin()` защиту.

### Защита admin allowlist

Дополнительно исправлена privilege-escalation возможность: публичная регистрация теперь не принимает адрес, уже находящийся в `ADMIN_EMAILS`. Владелец должен создать обычный account и затем добавить его email в production `ADMIN_EMAILS` либо provision-ить admin напрямую.

### `.env` / secrets

**Безопасно:**

- `.env` отсутствует в release ZIP;
- `.env.example` содержит пустые secret fields;
- `.gitignore` исключает `.env` и `.env.*`, но оставляет `.env.example`;
- `.dockerignore` также исключает `.env`/`.env.*` и оставляет `.env.example`.

### Security headers

**Активны:**

- `Content-Security-Policy`;
- `X-Frame-Options: SAMEORIGIN`;
- `Referrer-Policy: strict-origin-when-cross-origin`;
- `Permissions-Policy`;
- `Strict-Transport-Security` на HTTPS.

### User data isolation

**Безопасно:** Library/history/favorites/collections/saved filters/related data запрашиваются с `user_id` текущей session; admin API отдельно защищён.

### Account deletion

**Безопасно:** удаляются связанные collections/items/favorites/history/saved filters/bookmarks/reports/sessions и сама user record в отдельном тестовом database fixture.

---

## 4. Полный маршрутный аудит

На живом локальном FastAPI instance проверены `200`:

- `/`
- `/search`
- `/archive`
- `/characters`
- `/characters/jon-snow`
- `/characters/jaime-lannister`
- `/characters/daenerys-targaryen`
- `/characters/tyrion-lannister`
- `/characters/arya-stark`
- `/characters/cersei-lannister`
- `/characters/barristan-selmy`
- `/edit-ideas`
- `/guides`
- `/help`
- `/faq`
- `/library`
- `/login`
- `/project`
- `/contacts`
- `/privacy`
- `/terms`
- `/copyright`
- `/video`

Для `/admin` правильный публичный результат теперь `401`, а не `200`.

---

## 5. Интерактивные элементы — итоговый smoke report

### `/characters`
- Фильтр по дому — **работает**; проверен результат Ланнистер = 3 карточки.
- Фильтр `edit_profile=action` — **работает**; Барристан входит в выборку.
- Поиск персонажа — **работает**; Барристан находится отдельно.
- Reset — **работает** в DOM harness.
- Ссылки карточек — строятся на `/characters/{slug}`; все 7 route targets отвечают `200`.

### `/archive`
- Search → `/api/search` — **работает**.
- `action` — **работает**, 4 → 2.
- `duration` — **работает**, 4 → 2 на тестовом наборе.
- Остальные фильтры имеют серверные параметры через существующий `buildSearchUrl`; auto-rerun теперь подключён общим listener.
- Фильтр block — **видим**; конфликтующее CSS правило устранено.

### `/faq`
- Заголовок — **1**, не задвоен.
- FAQ items — **6**.
- Accordion — DOM check выполнен.

### Остальные публичные страницы

Route target smoke: все перечисленные выше публичные страницы возвращают ожидаемый `200`; отсутствующие страницы/сломанные menu targets в активной навигации не обнаружены.

Ограничение: sandbox блокирует direct loopback navigation для Playwright (`ERR_BLOCKED_BY_ADMINISTRATOR`) и в отдельном run был EPIPE Playwright driver, поэтому нельзя честно заявлять, что каждый клик всех страниц был выполнен в настоящем сетевом Chromium-сеансе. Серверные route/API проверки и изолированный DOM smoke выполнены.

---

## 6. Files changed

### Backend

- `backend/main.py`
- `backend/character_profiles.py`
- `backend/api/auth.py`

### Frontend

- `frontend/pages/characters.html`
- `frontend/archive.html`
- `frontend/css/app.css`
- `frontend/css/final-v7.css`
- `frontend/js/stage12-characters.js`
- `frontend/js/stage12-archive-filters.js`

### Tests

- `tests/test_stage10.py`
- `tests/test_stage11.py`
- `tests/test_stage12.py`

### Release/deployment files already present from the Stage 12 pre-existing state

- `render.yaml`
- `docker-compose.yml`
- `START_HERE.md`
- `DEPLOY_PUBLIC.md`
- `backend/api/search.py`

These existing Stage 12 release changes were preserved and verified; they were not removed during the character/filter/security work.

---

## 7. Backup / archive policy

All changed pre-existing files were copied to `_backup/stage12/` before modification.

The old hardcoded active `frontend/pages/characters.html` was moved to `_archive/frontend/pages/characters.html`, preserving its original relative path.

The pre-existing `CHANGES_STAGE12.md` was preserved in:
`_archive/stage12/CHANGES_STAGE12.md`
and `_backup/stage12/CHANGES_STAGE12.md`.

---

## 8. Verification

- `pytest -q`: **56 passed**
- `python -m compileall -q backend frontend`: **PASS**
- `node --check` on active JS files: **16 files / 0 failures**
- live route audit: **all public routes 200; `/admin` 401 unauthenticated**
- character DOM harness: **7 cards / Barristan / house / profile / search verified**
- archive HTTP filter check: **parameters sent + results changed**
- security checks: Argon2 / session flags / login rate limit / CSRF / admin guard / env-ignore / security headers verified
- `clipfinder.db`: restored to the exact Stage 11 source copy before final packaging

---

## 9. Remaining pre-production actions

1. Set a real `YOUTUBE_API_KEY` in the production environment — never commit it to the repository.
2. Set `PUBLIC_BASE_URL` and exact production `ALLOWED_ORIGINS`.
3. Set `ADMIN_EMAILS` for the real admin account.
4. Keep Render SQLite on the configured Persistent Disk / `CLIPFINDER_DB_PATH` and deploy as a single instance unless moving to PostgreSQL.
5. Perform one real production smoke with a real YouTube key and HTTPS domain.
6. Consider a follow-up CSP hardening pass removing `unsafe-inline` after legacy inline scripts are migrated to nonce/hash/external scripts.
