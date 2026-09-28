# CHANGES_STAGE16 — автоматический рост каталога персонажей

Дата: 2026-09-28
База: ClipFender Stage 15 с обновлёнными 7 cinematic-портретами.

## Что добавлено

### 1. Автоматический character discovery pipeline

Добавлен `backend/services/character_catalog.py` и API `POST /api/characters/ensure`.

Поток:

1. Проверка существующего `CHARACTER_PROFILES`.
2. Проверка уже созданного динамического профиля в SQLite.
3. Атомарный `pending`-lock на slug, чтобы одновременные запросы не запустили две генерации.
4. Опциональный поиск изображения через Bing Image Search.
5. К скачиванию допускаются только хосты из `CHARACTER_IMAGE_SEARCH_ALLOWED_HOSTS`.
6. Кандидат проходит валидацию Pillow: тип изображения, минимальный размер, максимальный размер файла и базовый edge-detail quality check.
7. Если хороший web-image не найден, запускается OpenAI image generation.
8. Финальный WebP сохраняется локально в `frontend/assets/reference/generated/<slug>-hq.webp`.
9. Профиль сохраняется в SQLite (`character_catalog`).
10. Каталог `/characters` автоматически подхватывает ready dynamic profiles.
11. Detail route `/characters/{slug}` также умеет отдавать dynamic profile.
12. Sitemap автоматически включает ready dynamic profiles.

### 2. Защита от расходов/злоупотребления

- `CHARACTER_DISCOVERY_RATE_LIMIT` ограничивает число discovery-запросов на IP.
- `CHARACTER_GENERATION_DAILY_GUARD` ограничивает число AI-generation вызовов в UTC-день.
- cross-site `Sec-Fetch-Site: cross-site` отклоняется на discovery endpoint.
- concurrent requests на один slug коалесцируются через SQLite `pending` state.
- некачественный/невалидный asset не публикуется в каталоге.

### 3. Frontend интеграция

`frontend/js/stage16-character-autodiscovery.js` подключён на `/characters` и `/search`.

На `/characters` поиск неизвестного имени может автоматически инициировать добавление после debounce.

В Idea Mode на `/search` явное поле `Персонаж` инициирует discovery параллельно с поиском материалов. Ошибка получения портрета не ломает основной search flow.

### 4. Существующие 7 портретов не затронуты

Для известных персонажей внешний image-search/AI не вызывается:

- Jon Snow
- Jaime Lannister
- Daenerys Targaryen
- Tyrion Lannister
- Arya Stark
- Barristan Selmy
- Cersei Lannister

### 5. Конфигурация

Добавлены в `.env.example`:

- `CHARACTER_IMAGE_SEARCH_ENABLED`
- `BING_IMAGE_SEARCH_API_KEY`
- `BING_IMAGE_SEARCH_ENDPOINT`
- `CHARACTER_IMAGE_SEARCH_COUNT`
- `CHARACTER_IMAGE_SEARCH_ALLOWED_HOSTS`
- `CHARACTER_IMAGE_GENERATION_ENABLED`
- `OPENAI_API_KEY`
- `OPENAI_IMAGE_ENDPOINT`
- `OPENAI_IMAGE_MODEL`
- `OPENAI_IMAGE_SIZE`
- `CHARACTER_IMAGE_MIN_SHORT_SIDE`
- `CHARACTER_IMAGE_MAX_BYTES`
- `CHARACTER_IMAGE_MIN_EDGE_SCORE`
- `CHARACTER_DISCOVERY_RATE_LIMIT`
- `CHARACTER_DISCOVERY_RATE_WINDOW`
- `CHARACTER_GENERATION_DAILY_GUARD`

`Pillow` добавлен в `requirements.txt`, потому что pipeline реально проверяет и нормализует получаемые изображения.

## Реальная проверка

`pytest`: 79 тестов — PASS.

`compileall`: PASS.

`node --check`: PASS для всех frontend JS.

Отдельный dry-run с изолированной test DB:

`Санса Старк → ready → created=True → source=ai_generation → /static/assets/reference/generated/sansa-stark-hq.webp`.

Реальный production `clipfinder.db` тестами не изменялся.

## Важное поведение

Если в production не задан `OPENAI_API_KEY`, AI fallback не работает и новый персонаж не будет опубликован только ради заполнения каталога.

Если Bing используется, необходимо явно разрешить домены, которые владелец имеет право скачивать и хранить, через `CHARACTER_IMAGE_SEARCH_ALLOWED_HOSTS`.

Для автоматического роста каталога на хостинге с ephemeral filesystem нужны persistent storage для SQLite и каталога `frontend/assets/reference/generated/`, иначе накопленные записи/файлы могут исчезнуть после перезапуска или redeploy.
