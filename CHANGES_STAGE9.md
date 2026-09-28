# CLIPFENDER — STAGE 9 FINAL RELEASE POLISH

## Цель
Финальная доводка public release без переписывания Stage 8 search/Idea Mode, Stage 11 admin/reports/i18n и Stage 12 security/Render слоя.

## 1. Устаревший `/character-search`

### Найденные пользовательские ссылки

- `frontend/components/header.html` — `НАЙТИ РОЛИК` → `/search`.
- `frontend/pages/edit-ideas.html` — `ОТКРЫТЬ ПОИСК` → `/search`.
- `frontend/pages/help.html` — `КАК ПОЛЬЗОВАТЬСЯ?` → `/search`.
- `frontend/pages/project.html` — `НАЧАТЬ ПОИСК` → `/search`.
- `frontend/js/final-v6.js` — fallback navigation → `/search`.

### Старый page route

- `frontend/pages/character-search.html` перенесён без удаления в `_archive/frontend/pages/character-search.html`.
- `backend/main.py` теперь отдаёт HTTP `301` с `/character-search` на `/search`.
- `/character-search` убран из `PUBLIC_SITEMAP_PATHS`.

Legacy SEO/CSS selector definitions остаются в проекте для rollback compatibility; active user flow их больше не использует.

## 2. Затемнение / blur / saturation — полный список фактически исправленных слоёв

### `frontend/css/final-v7.css`

1. `.home-stage3__scene`
   - было: `filter:saturate(.9) contrast(1.04) brightness(.78)`
   - стало: `filter:none`

2. `.home-stage3__scene::after`
   - было: stacked gradients с максимальным `rgba(0,0,0,.82)`
   - стало: один restrained vertical gradient с максимумом `rgba(0,0,0,.58)`

3. `.home-stage3__fog`
   - было: `opacity:.22`
   - стало: `opacity:.10`
   - `filter:none` сохранён.

4. `.home-stage3__veil`
   - было: gradient до `rgba(5,7,8,.95)`
   - стало: максимум `rgba(5,7,8,.46)` в legacy declaration, а Stage 9 release layer делает veil фактически инертным: `opacity:0; background:transparent`.

5. `.cf-v7-page::after`
   - было: gradient до `rgba(4,6,7,.96)`
   - стало: gradient до `rgba(4,6,7,.68)`.

6. `body:has(.cf-character-search-v7) .cf2-header` и остальные V7 header overrides
   - было: `position:absolute!important`
   - стало: `position:sticky!important`.
   - Это убирает риск визуального выброса контента под/над шапкой.

7. `.cf-search-page__scene`
   - было: dark gradient до `rgba(3,5,7,.96)`
   - стало: максимум `rgba(3,5,7,.68)`.
   - Для legacy page дополнительно зафиксирован `filter:none`.

8. `.cf-search-page__fog`
   - было: `opacity:.35`
   - стало: `opacity:.12`
   - `filter:none`.

### `frontend/css/site.css`

9. `.panel-art`
   - было: `filter:saturate(.7) contrast(1.05)`
   - стало: `filter:none`.

10. `.panel-art,.work-thumb-rich,.featured-visual,.project-map-art,.workshop-panel,.auth-art`
    - было: `filter:saturate(.84) contrast(1.05)`
    - стало: `filter:none`.

### `frontend/css/stage9-release-polish.css`

11. `.home-stage3__veil`
    - старый затемняющий veil отключён (`opacity:0`, `background:transparent`).

12. Контентные изображения
    - для character/video/search artwork принудительно оставлена чистая от blur/saturate подача.
    - декоративные слои остаются `pointer-events:none`.

## 3. Проверка страницы поиска

### `/search`

Изменять DOM-порядок не потребовалось: `#cf8SearchForm` уже расположен внутри первого `.cf8-hero` блока до `#cf8Results`.

Stage 9 добавил только stacking guarantees:

- `.cf8-hero` → content layer;
- `.cf8-form` → interactive layer;
- decor → non-interactive background layer.

Поэтому реальное поле поиска и кнопка находятся в первом экране вместе с Idea Mode и Film/Series controls.

### `/`

`#homeStage3Search` уже находится внутри центрального hero. Stage 9 усиливает его `z-index`, не перемещая форму из существующей cinematic композиции.

## 4. Header / section overlap

Прямой DOM leak чужой секции в header в текущем HTML не найден.

Найденным источником риска были legacy absolute-header rules. Они переведены в sticky-поведение; Stage 9 также закрепляет:

`header z-index: 500`

и фоновые/контентные слои ниже.

Main/page containers сохраняют `overflow:clip`, поэтому section content не должен визуально выходить за границу shell.

## 5. A — favicon

Добавлены:

- `frontend/favicon.svg` — адаптированный существующий `cf-crest.svg`;
- `frontend/favicon.ico` — 16/32/48 PNG frames;
- `frontend/assets/meta/favicon-32x32.png`;
- `frontend/assets/meta/apple-touch-icon.png` (180x180);
- `frontend/assets/meta/icon-192.png`;
- `frontend/assets/meta/icon-512.png`.

`frontend/components/seo.html` теперь содержит:

- SVG favicon;
- ICO fallback;
- 32x32 PNG;
- `apple-touch-icon`.

`manifest.webmanifest` содержит SVG + 192x192 PNG + 512x512 PNG.

Добавлены root endpoints для icon files.

## 6. B — Open Graph

`og_image` уже существовал как общий context variable; Stage 9 сделал его корректно динамическим в `frontend/page_shell.py`:

- default → `/static/assets/meta/clipfender-og-1200x630.jpg`;
- character profile → изображение персонажа;
- `/video?id=<valid 11-char id>` → `https://i.ytimg.com/vi/<id>/hqdefault.jpg`.

Created default share image:

`frontend/assets/meta/clipfender-og-1200x630.jpg`.

Character profile `ProfilePage` JSON-LD тоже получает image.

## 7. C — robots / sitemap

Оба endpoint уже существовали; Stage 9 привёл их в соответствие public release:

### `/robots.txt`

Закрыты:

- `/api/`
- `/_archive/`
- `/admin`
- `/login`
- `/library`

### `/sitemap.xml`

Убраны:

- `/character-search`
- `/login`
- `/library`

Оставлены public pages, legal pages и character profiles.

## 8. D — alt / accessibility

Контентные изображения получили осмысленные alt; decorative crest images с пустым alt теперь явно имеют `aria-hidden="true"`.

Проверены active `frontend/**/*.html`:

- отсутствующих `alt` — 0;
- decorative empty-alt без `aria-hidden` — 0.

Background-image character cards не требуют `<img alt>` и остаются presentation layers.

## 9. Что изменено

- `backend/main.py`
- `frontend/page_shell.py`
- `frontend/components/header.html`
- `frontend/components/footer.html`
- `frontend/components/seo.html`
- `frontend/archive.html`
- `frontend/pages/edit-ideas.html`
- `frontend/pages/help.html`
- `frontend/pages/project.html`
- `frontend/pages/library.html`
- `frontend/css/final-v7.css`
- `frontend/css/site.css`
- `frontend/css/app.css`
- `frontend/js/final-v6.js`
- `frontend/manifest.webmanifest`
- `START_HERE.md`
- `frontend/sw.js`
- `tests/test_stage9_release.py`

## 10. Создано

- `frontend/favicon.svg`
- `frontend/favicon.ico`
- `frontend/assets/meta/favicon-32x32.png`
- `frontend/assets/meta/apple-touch-icon.png`
- `frontend/assets/meta/icon-192.png`
- `frontend/assets/meta/icon-512.png`
- `frontend/assets/meta/clipfender-og-1200x630.jpg`
- `frontend/css/stage9-release-polish.css`
- `tests/test_stage9_release.py`
- `CHANGES_STAGE9.md`

## 11. Перемещено

- `frontend/pages/character-search.html`
  → `_archive/frontend/pages/character-search.html`

Ничего не удалено.

## 12. Backup

Перед изменениями сделаны копии изменяемых файлов в:

`_backup/stage9/`

## 13. Regression

```text
pytest                     45 passed
python -m py_compile      PASS
node --check              PASS
CSS imports               0 missing
active /character-search  links: 0
legacy character page     archived
favicon routes             PASS
manifest icons             PASS
OG context                 PASS
robots                     PASS
sitemap                    PASS
alt audit                  PASS
```

`clipfinder.db` не изменялся в Stage 9.

Полный runtime smoke с настоящим YouTube client в этой sandbox-среде не запускался из-за отсутствующей локальной `googleapiclient`; проектный pytest использует изолированный stub для проверки приложения без обращения к реальному YouTube API.
