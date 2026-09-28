# ClipFender — CHANGES_STAGE13

## Итог Stage 13

Stage 13 выполнен на актуальном `ClipFender_PUBLIC_RELEASE_STAGE12_FINAL.zip`.

Ключевые изменения:

- `/guides` перевёрстан в широкую editorial/grid-раскладку;
- секция «Идея для эдита» стала отдельным full-width блоком с равномерной сеткой;
- `/guides → НАЙТИ СЦЕНЫ` подтверждён как рабочий переход в существующий `/archive?q=...`;
- причина огромного герба в «РЕЗУЛЬТАТЫ ПОИСКА» локализована в неконтролируемом размере `.cf4-signet img`; добавлено жёсткое ограничение размера;
- активных screenshot-background ссылок `reference/page-bg/*` в frontend после Stage 13 не осталось;
- default ranking сохранён на `sort=score` и усилен новым Stage 13 Edit Suitability scoring;
- scoring теперь сильнее учитывает релевантность запроса/фильма, монтажную длину, явные clean-сигналы и текстовые признаки мусорного контента;
- добавлены Stage 13 contract/regression tests.

## БАГ 1 — `/guides`

### Причина

`frontend/pages/guides.html` использовал `.cf-guides-layout` из трёх колонок, но `.cf-guide-idea` не занимал всю строку через `grid-column: 1 / -1`. Grid поэтому размещал секцию «Идея для эдита» только в первой колонке следующей строки и оставлял большую пустую область справа.

### Исправление

Добавлен `frontend/css/stage13-release.css` и отдельные Stage 13 overrides:

- desktop: `steps | scene | quick search`;
- `idea` занимает `grid-column: 1 / -1`;
- `.cf-guide-idea-grid` использует 4 равномерные колонки;
- блок `Важно` оформлен как широкая нижняя подсказка;
- при ширине до 1100px: 2 колонки, быстрый поиск и Idea-section на всю ширину;
- до 760px: одна колонка;
- до 480px: уменьшенные внутренние отступы и безопасная ширина controls.

### Responsive contract

CSS рассчитан на:

- 1440px+: 3-column primary layout + full-width idea row;
- 1024px/около того: 2-column primary layout + full-width search/idea;
- 768px: 1-column layout;
- 480px и ниже: 1-column layout без горизонтального overflow.

Полный автоматический browser E2E к localhost в данном sandbox невозможен: Chromium блокирует loopback navigation с `ERR_BLOCKED_BY_ADMINISTRATOR`. Поэтому responsive contract дополнительно закреплён в CSS tests, а сервер/DOM проверены отдельно.

## БАГ 2 — «РЕЗУЛЬТАТЫ ПОИСКА» / огромный герб

### Точный маршрут

В актуальном Stage 12 ZIP отдельного `/results` route нет.

Фактическая цепочка:

`/guides`
→ `final-v7.js`
→ `/archive?q=<query>`
→ `frontend/archive.html`
→ `/api/search`

Кнопка «НАЙТИ СЦЕНЫ» уже вела на корректный рабочий `/archive`; маршрут менять не требовалось.

### Точная причина

`frontend/archive.html` содержит декоративный:

```html
<div class="cf4-signet">
    <img src="/static/assets/reference/cf-crest.svg" ...>
</div>
```

SVG имеет intrinsic size 600×760.

В активном `final-v4.css` было старое ограничение `.cf4-signet`, но `final-v4.css` не импортируется через `app.css` и не влияет на активный archive page.

В активном каскаде не было достаточного ограничения для изображения внутри `.cf4-signet`, поэтому SVG мог отображаться в собственном большом размере.

### Исправление

В `frontend/css/stage13-release.css`:

- контейнер `.cf4-signet` ограничен `68×76px`;
- изображение ограничено `46×58px`;
- добавлены `max-width/max-height`, `object-fit: contain` и `overflow:hidden`;
- на <=680px decorative signet скрывается.

Дополнительно `cf4-results-shell` защищён от overflow.

### Screenshot-background audit

После Stage 13 grep по активным `.html/.css/.js`:

`reference/page-bg/*` — **0 активных ссылок**.

Следовательно старые UI screenshot'ы больше не используются как активные page backgrounds.

## БАГ 3 — default ranking / лучший материал для эдита

### Что было

Публичный API уже имел `sort="score"` по умолчанию, `/search` отправлял `sort=score`, `/archive` имел option `score`, а Idea Mode вызывал `sort_videos(..., "score", ...)`.

Stage 13 не ломает этот контракт, а усиливает саму метрику `edit_suitability_score`.

### Новая scoring версия

`EDIT_SUITABILITY_VERSION = "stage13-v2"`.

Score теперь использует только существующие данные модели:

- `edit_score`;
- `is_raw_footage`;
- `is_dynamic`;
- `is_action`;
- `is_clip`;
- `is_cinematic`;
- `is_clean`;
- `is_hd` / `is_4k`;
- длительность;
- query/film relevance;
- audio flags;
- title/description/channel text.

Усилены:

1. релевантность query и film;
2. полезная монтажная длительность;
3. явные clean-сигналы (`no subtitles`, `no watermark`, `no commentary` и т.п.);
4. отрицательные текстовые признаки (`reaction`, `review`, `podcast`, `stream`, `fan edit`, `subtitles`, `watermark` и т.п.).

Не добавлялась выдуманная scene-level detection: реальный tempo, точные таймкоды, визуальное распознавание субтитров/водяных знаков по кадру и т.п. по-прежнему не притворяются доступными, если их нет в metadata.

### Concrete before/after

Использован детерминированный набор из реальных полей текущей модели, чтобы показать эффект новой логики без выдуманных YouTube данных.

Запрос: `Jon Snow`, фильм: `Game of Thrones`.

| Материал | Stage 12 | Stage 13 |
|---|---:|---:|
| `CLEAN001 — Jon Snow battle scene raw footage` | 84 | **82** |
| `DIRTY001 — Jon Snow 4K cinematic subtitles watermark` | **88** | 70 |

До Stage 13 первым стоял материал с explicit `subtitles/watermark` сигналами, потому что старая модель их не наказывала.

После Stage 13 первым стал clean raw/action источник.

Это показывает именно изменение ranking поведения, а не искусственную подмену результата.

### Текущий database snapshot

Production `clipfinder.db` в Stage 12 ZIP не содержит video rows (`videos = 0`), поэтому реальный live YouTube before/after из snapshot честно построить нельзя.

## Дополнительные изменения

### Idea Mode

В `frontend/pages/search.html` в datalist персонажей добавлен существующий реальный персонаж:

- Барристан Селми.

### Tests

Добавлен:

`tests/test_stage13.py`

Он покрывает:

- Stage 13 ranking regression;
- clean metadata signals;
- wide/full-width guides layout contract;
- bounded archive crest;
- default `sort=score` contract для search/archive/Idea Mode.

## Файлы Stage 13

Изменены:

- `frontend/pages/guides.html`
- `frontend/css/app.css`
- `frontend/css/stage13-release.css` (новый)
- `frontend/archive.html`
- `frontend/pages/search.html`
- `backend/services/scoring.py`
- `tests/test_stage8.py`
- `tests/test_stage9.py`
- `tests/test_stage13.py` (новый)

Не изменялись, но перепроверены:

- `frontend/js/stage12-archive-filters.js`
- `frontend/js/stage8-idea.js`
- `frontend/css/final-v7.css`

В актуальном Stage 12 `final-v7.css` уже имел одно активное правило `body.cf4-active .filters-wrap`; Stage 13 повторно подтвердил отсутствие конфликта и не создавал лишнее правило.

## Backup / Archive

Перед изменением активные файлы сохранены в:

`_backup/stage13/`

Старые активные версии также сохранены с исходными путями в:

`_archive/stage13/`

## Проверки

- `python -m compileall -q backend` — PASS
- `node --check` — 16/16 PASS
- `pytest -q` — **61 passed**
- публичные маршруты: **21/21 HTTP 200**
- `/characters/barristan-selmy`: HTTP 200
- активные `reference/page-bg/*` frontend refs: **0**
- production `clipfinder.db` восстановлена побайтно из Stage 12 ZIP
- final DB SHA-256: `20376bbf27b2be422052d962b71f7f27acce061a43bc16677f15bf1352adc4f3`

## Browser test limitation

Внутренний Chromium присутствует, но sandbox запрещает navigation к `127.0.0.1:*` и локальному test server (`ERR_BLOCKED_BY_ADMINISTRATOR`). Поэтому Stage 13 не заявляет полноценный live browser E2E по localhost как пройденный.

Серверные route/API tests, CSS/HTML contract checks и scoring regression выполнены полностью.
