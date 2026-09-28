# CLIPFENDER — CHANGES_STAGE8

## Этап
Stage 8 — Idea for Edit, edit-suitability ranking, film/series filter, full-screen search.

## Главное решение по БД

Новая схема SQLite **не потребовалась**.

Текущие поля уже дают достаточно сигналов для честного v1:

- `edit_score`
- `is_action`
- `is_dynamic`
- `is_cinematic`
- `is_clip`
- `is_raw_footage`
- `is_clean`
- `is_hd`
- `is_4k`
- `duration`
- `has_dialogue`
- `has_voice`
- `is_no_music`
- `title`
- `description`
- `channel`

Это позволяет расширить ranking без миграции и без риска для существующего cache/database flow.

## Edit Suitability Score

Новая метрика:

`edit_suitability_score` — 0..100.

Версия:

`stage8-v1`.

### Состав

| Компонент | Вес / вклад |
|---|---:|
| Существующий `edit_score` | 45% |
| Материал для нарезки | до 20 |
| Качество / clean | до 15 |
| Длительность источника | до 10 |
| Релевантность query / film | до 10 |
| Audio / scene signals | до 5 |
| Явные anti-edit сигналы | штраф |

### Материал для нарезки

Положительные сигналы:

- raw footage;
- dynamic;
- action;
- clip;
- cinematic;
- clean.

### Качество

- 4K выше HD;
- HD выше отсутствия HD-сигнала;
- clean добавляет положительный сигнал.

### Длительность

Это **длительность исходного ролика**, а не длительность конкретной сцены.

Предпочтение получает короткий/средний источник:

- 5–60 сек;
- 61–180 сек;
- 181–300 сек;
- 301–600 сек;
- более длинные источники получают меньше бонуса.

### Релевантность

Проверяется по имеющимся:

- title;
- description;
- channel.

Для указанного фильма/сериала используется параметр `film` и тот же metadata filter.

### Что намеренно НЕ заявляется как точный сигнал

В текущей БД нет достоверных полей для:

- точного tempo анализа;
- watermark detection;
- subtitle detection;
- scene-level start/end timestamps.

Поэтому они не выдумываются.

`is_clean` используется как существующий общий clean-сигнал, но не переименовывается в «точно без водяного знака/субтитров».

## `score_estimated`

Новый API-поле:

`score_estimated: true | false`

Оно вычисляется по реально наблюдаемым сигналам.

SQLite default `0/false` сам по себе не считается доказательством того, что сигнал был рассчитан.

Старые записи с недостаточным количеством реальных сигналов получают:

```json
"score_estimated": true
```

Они не удаляются и не скрываются.

## Жёсткое правило сортировки

Backend теперь всегда применяет:

1. рассчитанный `edit_suitability_score`;
2. рассчитанные записи выше `score_estimated=true`;
3. пользовательская сортировка (`views`, `newest`, `oldest`, `score`) только внутри сопоставимого ranking tier.

То есть `sort=views` больше не может поднять массовую reaction/review-запись над явно лучшим материалом для монтажа.

Правило работает для:

- `/api/search`;
- cache path;
- YouTube path;
- `/archive`;
- нового `/search`;
- Idea mode.

## Примеры до / после

Текущая локальная `clipfinder.db` содержит 0 video records, поэтому ниже приведены **контролируемые тестовые примеры**, а не реальные production-видео из БД.

### Пример 1 — views

До Stage 8 при `sort=views`:

```text
«Jon Snow reaction review podcast» — 50 000 000 views
```
мог находиться перед:

```text
«Jon Snow 4K raw footage battle cinematic» — 1 200 views
```

После Stage 8 тестовый ranking дал:

```text
4K/raw/battle/cinematic → 92/100
reaction/review/podcast → 30/100
```

Поэтому первый материал становится выше второго, несмотря на огромную разницу в просмотрах.

### Пример 2 — вторичный sort

Для двух пригодных материалов `sort=views` продолжает работать, но только после основного suitability ranking.

То есть views остаются полезным вторичным критерием, а не главным критерием выбора материала для монтажа.

### Пример 3 — estimated

Старая запись только с title и без достаточных material/quality/duration signals получает:

```json
"score_estimated": true
```

и всегда помещается ниже нормально рассчитанных записей.

## Фильм / сериал

Добавлен необязательный API-параметр:

```text
film=Game of Thrones
```

Старое поведение без `film` не меняется.

Фильтр работает по реально имеющимся metadata:

- title;
- description;
- channel.

Специальная franchise table не добавлялась, чтобы не угадывать принадлежность ролика к конкретному сериалу без достоверного источника.

## Idea for Edit API

Добавлен:

```text
GET /api/edit-idea
```

Поддерживает:

- `query` — персонаж/идея;
- `film` — фильм/сериал;
- `mood`;
- `tempo`;
- `limit_per_stage`.

### Mood

- action
- dark
- drama
- romance
- emotional
- epic
- tension
- melancholy

### Tempo

- fast
- medium
- slow

Tempo в Stage 8 — **heuristic**, основанный только на доступных metadata и flags.

### Структура сценария

```text
INTRO
↓
BUILD-UP
↓
CLIMAX
↓
OUTRO
```

Каждая секция использует только реальные записи из локальной БД за последние 24 часа.

### Таймкоды

Поскольку scene-level timestamps сейчас отсутствуют, API не придумывает `00:37–00:49`.

Вместо этого возвращается полный диапазон исходного видео и:

```json
"timecode_exact": false
```

Это намеренно сделано консервативно.

## Full-screen Search

Добавлена страница:

```text
/search
```

На ней есть переключатель:

```text
ОБЫЧНЫЙ ПОИСК
ИДЕЯ ДЛЯ ЭДИТА
АРХИВ
```

Главная страница теперь направляет основной поиск в `/search`, а не напрямую в `/archive`.

Кнопки-подсказки на hero также открывают новый search interface.

## Archive

Существующий `/archive` сохранён.

Добавлены:

- Film / series filter;
- ссылка-переключатель в Idea mode.

Существующий search/cache/quota pipeline не переписан.

## Guides

`pages/guides.html` дополнена:

- описание Idea mode;
- mood tags;
- tempo tags;
- 4-stage scenario;
- правило backend sorting;
- `score_estimated`;
- ограничение точных scene timestamps.

## Изменённые файлы

```text
backend/main.py
backend/api/search.py
backend/services/scoring.py
frontend/page_shell.py
frontend/index.html
frontend/archive.html
frontend/pages/guides.html
frontend/js/final-v6.js
frontend/js/stage5-atmosphere.js
frontend/css/app.css
```

## Созданные файлы

```text
backend/api/edit_idea.py
frontend/pages/search.html
frontend/css/stage8-idea.css
frontend/js/stage8-idea.js
tests/test_stage8.py
CHANGES_STAGE8.md
```

## Backup

Перед изменением сохранено в:

```text
_backup/stage8/
```

включая оригинальные версии затронутых backend/frontend файлов и `clipfinder.db`.

## База данных

Схема **не изменялась**.

`clipfinder.db` побайтно совпадает с оригиналом:

```text
20376bbf27b2be422052d962b71f7f27acce061a43bc16677f15bf1352adc4f3
```

## Проверки

```text
pytest                         24 passed
python -m py_compile           PASS
node --check                   PASS
public /search route           PASS
/api/edit-idea                 PASS
/sitemap.xml contains /search  PASS
Stage 7 project files missing  0
```

## Что проверить руками

1. Обычный поиск с `sort=views` и `sort=newest`: сильный edit material должен оставаться выше слабого.
2. Результат со слабыми старыми metadata должен показывать `estimated`/неполный score.
3. `/archive?film=Game%20of%20Thrones` должен фильтровать существующие материалы.
4. `/search?mode=idea&q=Jon%20Snow` должен собрать сценарий из реальных записей БД; на пустой БД должен честно показать `no_material`.
5. На главной hero submit и подсказки должны открывать `/search`, а не `/archive`.
6. В Idea mode проверить все mood/tempo варианты и `film`.
7. Не должно появляться выдуманных scene-level таймкодов.
8. На 360/768/1024/1440/1920 проверить новый `/search` интерфейс и archive filter.
9. На production перед публикацией добавить реальные юридические реквизиты владельца сервиса, если они ещё не внесены в legal pages.
