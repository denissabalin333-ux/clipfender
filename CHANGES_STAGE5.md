# ClipFender — Stage 5

## Цель

Довести визуальный слой до живого cinematic archive-интерфейса, не переписывая существующую backend-логику и не удаляя существующие функции/ID/classes.

## Изменено

- `frontend/css/app.css` — подключён новый additive visual layer.
- `frontend/css/design-tokens.css` — добавлен token `--z-tooltip`.
- `frontend/js/site.js` — добавлен loader Stage 5.
- `frontend/pages/character-search.html` — подключён Stage 5 JS.
- `frontend/pages/video.html` — подключён Stage 5 JS.

## Создано

- `frontend/css/stage5-atmosphere.css`
- `frontend/js/stage5-atmosphere.js`

## Stage 5 features

- лёгкие частицы/пепел через canvas;
- grain/noise слой;
- мягкий pointer + scroll parallax;
- scroll reveal для секций и карточек;
- `prefers-reduced-motion` fallback;
- animated counters на hero;
- live suggestions для главного поиска;
- кнопка «СЛУЧАЙНЫЙ РОЛИК ДЛЯ ЭДИТА»;
- блок «ПОПУЛЯРНОЕ СЕГОДНЯ»;
- skeleton-загрузка результатов архива;
- improved empty/error states;
- glow/depth hover для карточек;
- копирование ссылки на ролик;
- официальный YouTube-плеер создаётся только после явного клика;
- единый tooltip layer;
- светлая/тёмная тема с сохранением выбора в localStorage;
- улучшенный toast/modal motion.

## Что намеренно не менялось

- публичные backend API;
- поиск, scoring, edit_filter, YouTube quota/cache;
- database schema;
- `clipfinder.db`;
- существующие demo auth/contact functions;
- legacy CSS/JS — не удалялись и не переносились на этом этапе.

## Backup

Перед изменениями Stage 5 сохранены рабочие версии изменяемых файлов в `_backup/stage5/`.

## Archive

`__pycache__`, созданные только проверками Python, перемещены в `_archive/generated-stage5/`.

## Проверки

- `pytest -q`: 12 passed
- `python -m py_compile`: PASS
- `node --check`: PASS для всех JS
- CSS parse (`tinycss2`): PASS
- Stage 5 CSS `!important`: 0
- HTTP smoke-test: все основные страницы 200
- Stage 5 CSS/JS assets: 200
- `clipfinder.db`: SHA-256 `20376bbf27b2be422052d962b71f7f27acce061a43bc16677f15bf1352adc4f3`

Браузерный screenshot-прогон в текущем sandbox невозможен: Chromium блокирует локальную HTTP-навигацию с `ERR_BLOCKED_BY_ADMINISTRATOR`, несмотря на работающий HTTP smoke-test.
