# ClipFender — CHANGES_STAGE15

## Stage 15: runtime-confirmed archive result fix + portrait root-cause audit

Дата: 2026-09-27
Исходный релиз: `ClipFender_PUBLIC_RELEASE_STAGE14_FINAL.zip`

> Этот отчёт отделяет подтверждённые runtime-факты от того, что нельзя честно исправить без новых исходных изображений.

## 1. БАГ 1 — «РЕЗУЛЬТАТЫ ПОИСКА»: чёрный круг

### Реальный путь воспроизведения

`Помощь → поиск/фильтры → /archive?q=minecraft%20survival`.

Фактический route:

`frontend/archive.html`

В HTML до Stage 15 проблемный элемент находился в строках 640–641:

```html
<div class="cf4-search-field">
  <svg viewBox="0 0 24 24" aria-hidden="true"><circle ...></circle><path ...></path></svg>
```

### Что реально было видно в Chromium ДО исправления

Проблемный DOM-элемент:

`body.cf4-active .cf4-search-field > svg`

Computed Style / geometry:

- `width: 1136px`
- `height: 1136px`
- `fill: rgb(0, 0, 0)`
- `stroke: none`
- вложенный `circle`: примерно `615.33 × 615.33px`

Это объясняет скриншот с большим чёрным кругом.

Причина была не в гербе, не в loader и не в API fallback: у `.cf4-search-field` не было активного layout/style-контракта для SVG, а старый размерочный код находился в неиспользуемом `final-v4.css`.

### Дополнительная проверка API

При пустом `YOUTUBE_API_KEY` в локальном окружении реальный запрос:

`GET /api/search?query=minecraft%20survival&min_views=0&sort=score&limit=20&page=1`

вернул:

`503`

```json
{"detail":"Не удалось получить данные YouTube. Повтори попытку позже."}
```

Чтобы проверить именно отображение результатов без YouTube API, был создан только тестовый cache fixture. Тот же запрос с fixture вернул `200` и 1 результат. Полный ответ сохранён в:

`evidence/stage15/api-search-minecraft-survival.mock.json`

### Что изменено

`frontend/archive.html:641`

SVG теперь явно имеет:

```html
class="cf4-search-icon"
width="18"
height="18"
viewBox="0 0 24 24"
```

Новый активный слой:

`frontend/css/stage15-release.css`

Добавляет:

- `.cf4-search-field` как flex-контейнер высотой 48px;
- SVG `18×18px`;
- `fill:none`;
- `stroke:currentColor`;
- `overflow:visible`;
- корректные размеры `circle/path`;
- нормальную desktop/tablet/mobile grid-раскладку querybar.

`frontend/css/app.css:47` подключает Stage 15 слой.

`frontend/archive.html:614` получает новый cache-bust `app.css?v=72.0`.

### Реальный browser AFTER

Chromium после исправления увидел:

- SVG rect: `18 × 18px`;
- computed `width: 18px`;
- computed `height: 18px`;
- `fill: none`;
- `stroke: rgb(185, 150, 88)`;
- circle rect: `9.75 × 9.75px`;
- `#videos` содержит 1 реальную тестовую `video-card`;
- browser errors: `0`.

Скриншот после:

`evidence/stage15/after-archive-fixed-browser.png`

Предыдущий runtime-снимок:

`evidence/stage15/before-archive-black-circle.png`

### Вывод

Первопричина подтверждена и исправлена в самом источнике layout-проблемы, а не маскированием круга.

---

## 2. БАГ 2 — мутные портреты персонажей

### Реальная проверка в Chromium

Для `jon-hq.webp`:

- URL: `/static/assets/reference/final/jon-hq.webp?v=1510`
- HTTP: `200 image/webp`
- размер файла: `48 100 bytes` по runtime Network test
- `naturalWidth: 1440`
- `naturalHeight: 1260`
- display size в browser probe: `620 × 350px`
- `filter: none`
- `opacity: 1`
- `transform: none`
- `object-fit: cover`
- `complete: true`

Физический размер файла значительно больше отображаемого, поэтому upscale-проблемы нет.

### Проверка CSS

`frontend/css/app.css:71`:

```css
.cf12-character-portrait img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    filter: none !important;
}
```

`frontend/css/stage14-portraits.css` также явно задаёт:

- `filter: none !important`
- `backdrop-filter: none !important`
- `opacity: 1`
- `image-rendering: auto`

В computed style Chromium итоговый `filter` действительно `none`.

### Проверенные 7 файлов

| Портрет | Natural size | Размер файла |
|---|---:|---:|
| `jon-hq.webp` | 1440×1260 | 48 KB |
| `jaime-hq.webp` | 1420×1380 | 68 KB |
| `daenerys-hq.webp` | 1440×1260 | 76 KB |
| `tyrion-hq.webp` | 1440×1260 | 52 KB |
| `arya-hq.webp` | 1440×1260 | 56 KB |
| `barristan-hq.webp` | 1440×1260 | 64 KB |
| `cersei-hq.webp` | 1440×1440 | 72 KB |

### Реальная причина

Портреты визуально мягкие уже в исходных `*-hq.webp`. Они не становятся резкими после загрузки в браузер, потому что исходный raster уже содержит мягкий/низкодетальный материал.

Это подтверждается одновременно тремя независимыми фактами:

1. `naturalWidth/naturalHeight` намного больше display size;
2. computed `filter` на `<img>` = `none`;
3. при непосредственном просмотре самих файлов soft-detail уже присутствует.

То есть текущий код не создаёт blur, который можно убрать ещё одним CSS-override.

### Что изменено в Stage 15

Не было сделано ложного «лечения» через CSS blur/sharpen.

Обновлён cache-busting портретов:

`frontend/pages/characters.html:75`
`frontend/pages/character.html:24`

`?v=1510`

и:

`frontend/js/stage14-portraits.js:5`

`CACHE_VERSION = '1510'`

Это гарантирует, что браузер не продолжит использовать прежнюю закэшированную версию изображения.

Но это **не добавляет отсутствующие детали в исходный raster**.

### Browser AFTER

Chromium после cache-bust загрузил реальный файл:

- `naturalWidth=1440`
- `naturalHeight=1260`
- `complete=true`
- `filter=none`
- `opacity=1`
- `object-fit=cover`
- display `620×350px` в отдельном runtime probe

Скриншот:

`evidence/stage15/after-character-portrait-browser.png`

### Что физически нужно заменить

Для действительно резких портретов нужны новые исходники этих 7 персонажей — желательно реальные постеры/кадры без сильного ресайза и с заметно большим исходным detail level. Только увеличение WebP или CSS sharpen не восстановит потерянные детали.

Stage 15 намеренно НЕ подменяет их случайными картинками или сгенерированными лицами.

Это единственный пункт Stage 15, который нельзя честно считать визуально «исправленным» без новых исходных изображений.

---

## 3. Backup/archive

Перед Stage 15 изменения были сохранены в:

`_backup/stage15/`

Старые версии изменённых существующих файлов сохранены также в:

`_archive/stage15/`

---

## 4. Проверки

- `python -m compileall backend` — PASS
- `node --check` для всех frontend JS — PASS
- `pytest` — PASS, 72 tests
- HTTP `/archive?q=minecraft survival` — `200`
- Mock `/api/search` — `200`, `filtered_total=1`
- Chromium runtime AFTER для search SVG — PASS
- Chromium runtime AFTER для portrait — PASS
- Browser errors в isolated runtime probes — `0`
- production `clipfinder.db` восстановлена из исходного Stage 14 ZIP; SHA-256:
  `20376bbf27b2be422052d962b71f7f27acce061a43bc16677f15bf1352adc4f3`

---

## 5. Основной итог

БАГ 1 полностью локализован до конкретного inline SVG и исправлен на уровне реального DOM/CSS-контракта.

БАГ 2 полностью локализован до качества самих исходных `*-hq.webp`: browser render pipeline не добавляет blur и не увеличивает изображение сверх native resolution. Для настоящей резкости нужны новые качественные исходники.
