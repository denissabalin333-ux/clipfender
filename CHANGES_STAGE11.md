# CHANGES_STAGE11 — ClipFender

Дата: 2026-09-26
Исходный архив: `ClipFender_PUBLIC_RELEASE_STAGE10_FINAL.zip`

## Итог Stage 11

Stage 11 направлен на устранение визуальных заглушек/наложений, восстановление рабочих страниц и проверку публичной навигации. Исходный код перед правками сохранён в `_backup/stage11/`, а старые активные версии файлов — в `_archive/stage11/` с сохранением исходного назначения.

Ключевая системная причина нескольких визуальных багов: файлы `frontend/assets/reference/page-bg/*.webp` в актуальном Stage 10 были не чистыми сценами, а сохранёнными скриншотами самих страниц. Они использовались как CSS-background, поэтому пользователь видел «второй интерфейс»: повторные заголовки, аккордеоны, карточки и другие элементы поверх настоящего DOM.

## БАГ 1 — «Библиотека» показывала огромный герб

### Причина

Активная страница:

- `frontend/pages/library.html`
- `frontend/css/pages/library.css`
- backend: `backend/api/library.py`
- маршрут: `/library`

`library.html` не подключал общий `/static/css/app.css`, хотя стили `.cf-library-*` находятся в `frontend/css/pages/library.css`, который подключается через `app.css`.

При отсутствии общего CSS декоративный SVG-герб не имел нужного ограничения размеров и мог занимать чрезмерную область страницы.

### Исправление

- В `frontend/pages/library.html` добавлено подключение `/static/css/app.css?v=72.0`.
- В `frontend/css/pages/library.css` добавлена отдельная реальная cinematic-сцена из существующих assets.
- Для герба добавлены жёсткие размеры `width:78px; height:96px; object-fit:contain; overflow:hidden`, чтобы SVG не мог разрастись даже при проблеме с загрузкой.
- Библиотека не скрывалась из навигации: backend и страница имеют реальную функциональность (избранное, коллекции, история поиска, сохранённые фильтры, экспорт).

### Состояние после

В focused browser/DOM-проверке `.cf-library-crest` имел размер около `92x112`, а SVG — `78x96`. Признаков полноэкранного герба нет.

## БАГ 2 — «О проекте»: чёрный фон и слишком короткий контент

### Фактический маршрут

Пункт меню «О ПРОЕКТЕ» ведёт на `/project`:

- `frontend/pages/project.html`
- `frontend/css/pages/project.css`

`/about` существует отдельно, но текущим header/footer для «О проекте» не используется.

### Причина

`frontend/css/final-v7.css` использовал `frontend/assets/reference/page-bg/about.webp` как фон. Этот `.webp` является скриншотом интерфейса страницы, а не чистой фоновой сценой.

В старом `project.html` также были неподтверждённые числовые блоки `100K+`, `200K+`, `24/7`, для которых в актуальном backend не найден достоверный источник статистики.

### Исправление

`frontend/pages/project.html` заменён на полную рабочую версию с общими header/footer и следующими секциями:

1. зачем нужен ClipFender;
2. история задачи — от поиска конкретного момента до пригодного материала;
3. четыре основных направления сервиса;
4. процесс от запроса до раскадровки;
5. принципы проекта;
6. CTA в обычный поиск и Idea Mode.

Вместо screenshot-background используется существующий asset:

`/static/assets/reference/final-real/world-castle-real.webp`

Числа `100K+`, `200K+`, `24/7` удалены как неподтверждённая статистика.

### Состояние после

Focused DOM-проверка подтвердила один основной H1 `ЗАЧЕМ НУЖЕН CLIPFENDER`, четыре основные контентные секции, отсутствие фиктивных статистических блоков и наличие реального cinematic-background asset.

## БАГ 3 — «Помощь»: сломанный фон и переход на FAQ

### Причина

Активная страница:

- `frontend/pages/help.html`
- `frontend/css/pages/help.css`
- маршрут: `/help`

`final-v7.css` использовал `frontend/assets/reference/page-bg/help.webp`, который является screenshot-like page asset, а не чистой сценой. Дополнительный `reference-hotfix/help-scene.webp` также не является подходящим чистым production-background.

Ссылка `ЧАСТЫЕ ВОПРОСЫ` уже имела корректный target `/faq`; проблема была на целевой странице FAQ, а не в URL ссылки.

### Исправление

- Все активные ссылки на screenshot-background для Help переведены на существующий cinematic asset `world-castle-real.webp`.
- Оригинальные активные версии сохранены в `_archive/stage11/` и `_backup/stage11/`.
- Существующие рабочие карточки Help сохранены.

### Состояние после

Focused DOM-проверка подтвердила наличие одной рабочей ссылки `href="/faq"`.

## БАГ 4 — FAQ: задвоение заголовка, фото поверх аккордеона

### Причина

Активный `frontend/pages/faq.html` фактически содержал только один настоящий H1 и один настоящий accordion. Второй визуальный «FAQ» возникал из-за фонового файла `frontend/assets/reference/page-bg/faq.webp`, который сам содержал снимок интерфейса FAQ.

То есть дубликат был не вторым HTML-компонентом, а изображением, использованным как background.

### Исправление

- `frontend/css/final-v4.css` и `frontend/css/final-v7.css` больше не используют `reference/page-bg/faq.webp`.
- FAQ layout и aside переведены на реальную существующую cinematic-сцену.
- Лишние screenshot-like background layers убраны из active CSS.
- Реальный accordion не переписывался без необходимости: используется существующий JS `faqToggle`.

### Состояние после

Focused browser/DOM проверка:

- H1 `ЧАСТЫЕ ВОПРОСЫ`: `1`;
- элементов FAQ: `6`;
- посторонних `<img>` внутри `.faq-layout`: `0`;
- открытие второго вопроса изменяло его класс с `faq-item-rich` на `faq-item-rich open`.

## БАГ 5 — «Фильтры»: узкая колонка, герб, чёрная заглушка

### Фактическое расхождение с описанием

В актуальном Stage 10 ZIP отдельного рабочего маршрута `/filters` нет. Реальные фильтры находятся внутри:

`frontend/archive.html`

в блоке:

`section.filters-wrap#filters`

### Причина

В `frontend/css/final-v7.css` фильтры скрывались правилом:

`body.cf4-active .filters-wrap { display:none !important; }`

При этом кнопка `#cf4FilterOpen` не открывала отдельную реализованную modal — она только пыталась прокрутить страницу к уже скрытому блоку. В результате пользователь видел неполную/нерабочую область фильтров.

### Исправление

- `frontend/archive.html` сохранён перед правкой и помещён в `_backup/stage11/` и `_archive/stage11/`.
- Кнопка `ФИЛЬТРЫ` теперь оставляет `aria-expanded="true"` и переводит фокус/прокрутку к реальному рабочему блоку.
- В `final-v7.css` реальный `.filters-wrap` снова становится видимым.
- Desktop: полноценная 4-колоночная сетка.
- 1050px и ниже: 3 колонки.
- 760px и ниже: 2 колонки.
- 520px и ниже: 1 колонка.

### Состояние после

Focused DOM/layout проверка на ширине 1440px подтвердила:

- `#filters`: `display:block`;
- ширина около `1178px`;
- блок видим;
- кнопка имеет `aria-expanded=true` до и после клика.

Отдельную `/filters` страницу не добавлял и ссылку на неё не создавал, поскольку такого активного маршрута в актуальном backend нет.

## Дополнительные найденные и исправленные проблемы

### 1. Screenshot-backgrounds по всему сайту

Проверен active frontend на ссылки вида:

- `reference/page-bg/*.webp`;
- `reference-hotfix/*scene`.

После Stage 11 таких active CSS/HTML references не осталось. Существующие реальные production scenes используются повторно:

- `reference/final-real/world-castle-real.webp`;
- `reference/final-real/siege-castle-real.webp`;
- `reference/final-real/home-cinematic-real.webp`.

Старые screenshot assets физически не удалялись.

### 2. Edit Ideas

`frontend/pages/edit-ideas.html` содержал явное использование `page-bg/ideas.webp` как background. Оно заменено на существующую реальную cinematic-сцену `siege-castle-real.webp`.

### 3. Characters fallback

`frontend/js/stage10-characters.js` имел fallback thumbnail на `page-bg/ideas.webp`. Он заменён на существующую реальную сцену `world-castle-real.webp`.

Оригинальная версия JS отдельно сохранена в `_backup/stage11/` и `_archive/stage11/`.

### 4. Неподтверждённые цифры Project

Удалены вместо попытки «угадать» статистику.

## Аудит header/footer меню

Проверены актуальные маршруты из header/footer и корневой главной страницы:

- `/`
- `/archive`
- `/characters`
- `/contacts`
- `/copyright`
- `/edit-ideas`
- `/guides`
- `/help`
- `/library`
- `/login`
- `/privacy`
- `/project`
- `/search`
- `/terms`

Каждый из этих маршрутов при локальном FastAPI smoke-test вернул HTTP `200`.

Отдельно проверена цепочка:

`/help → /faq`

Она использует корректный `/faq` target.

## Проверки

### Python

`python -m compileall -q backend frontend` — PASS.

### JavaScript

`node --check` для всех active frontend JS — PASS.

### Tests

Полный текущий тестовый набор: **49 passed**.

### Browser / DOM

Проведены focused проверки:

- Library — crest dimensions нормальные;
- Archive — фильтры видимы на desktop, responsive grid активен;
- FAQ — один H1, шесть FAQ items, никаких посторонних изображений в layout, accordion открывается;
- Help — ссылка на FAQ корректна;
- Project — один основной H1, новый контент, fake stats отсутствуют, реальный background asset подключён.

Прямой полноценный визуальный screenshot через browser sandbox ограничен окружением: sandbox блокировал загрузку локальных loopback/file:// ресурсов. Поэтому в отчёте не заявляется полноценная pixel-perfect визуальная проверка через такой sandbox; DOM/layout и route checks выполнены фактически.

## База данных

После тестового запуска FastAPI исходный `clipfinder.db` был восстановлен из Stage 10 ZIP.

SHA-256 до/после восстановления совпадает:

`20376bbf27b2be422052d962b71f7f27acce061a43bc16677f15bf1352adc4f3`

Это означает, что в release ZIP база не содержит служебных изменений, вызванных локальным smoke-test.

## Изменённые файлы относительно Stage 10

Активные содержательные изменения:

- `frontend/archive.html`
- `frontend/css/final-v4.css`
- `frontend/css/final-v7.css`
- `frontend/css/pages/library.css`
- `frontend/css/pages/project.css`
- `frontend/js/stage10-characters.js`
- `frontend/pages/edit-ideas.html`
- `frontend/pages/library.html`
- `frontend/pages/project.html`

Дополнительно добавлены Stage 11 snapshots в `_backup/stage11/` и `_archive/stage11/`.

## Правило сохранения старого

Ни один исходный активный файл Stage 10 не удалён. Перед заменой активные версии были сохранены в `_backup/stage11/`, а архивные копии — в `_archive/stage11/`.
