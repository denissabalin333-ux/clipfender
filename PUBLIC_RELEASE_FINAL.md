# ClipFender — Final Public Release

Этот пакет подготовлен для публичного запуска на Render.

## 1. Что уже настроено в коде

- FastAPI запускается через `render.yaml`.
- SQLite и автоматически создаваемые portraits используют Persistent Disk.
- Production `/health` не становится зелёным, пока обязательная конфигурация отсутствует.
- `YOUTUBE_API_KEY` используется для реального поиска.
- `OPENAI_API_KEY` используется для автоматической генерации новых character portraits.
- Legacy Bing Image Search путь выключен.
- Новые portraits хранятся под `CHARACTER_STORAGE_DIR` и отдаются через `/media/characters/...`.
- Bootstrap admin создаётся на старте при наличии `ADMIN_EMAILS` + `ADMIN_BOOTSTRAP_PASSWORD`.
- После первого входа `ADMIN_BOOTSTRAP_PASSWORD` рекомендуется удалить из Render.

## 2. Что сделать владельцу

### GitHub

1. Создать приватный или публичный GitHub repository.
2. Загрузить содержимое этого проекта в корень repository.
3. Убедиться, что `.env`, `clipfinder.db`, `.venv`, ZIP-файлы и `_backup/` не публикуются в Git. `.gitignore` уже настроен.

### Render

1. Создать Blueprint из repository и `render.yaml`.
2. Подключить Persistent Disk с mount path `/var/lib/clipfender`.
3. Заполнить Environment Variables:

```text
YOUTUBE_API_KEY=ВАШ_YOUTUBE_KEY
OPENAI_API_KEY=ВАШ_OPENAI_KEY
ADMIN_EMAILS=ВАШ_EMAIL
ADMIN_BOOTSTRAP_PASSWORD=СИЛЬНЫЙ_ОДНОРАЗОВЫЙ_ПАРОЛЬ
ALLOWED_ORIGINS=https://ВАШ_ДОМЕН
PUBLIC_BASE_URL=https://ВАШ_ДОМЕН
APP_ENV=production
CHARACTER_IMAGE_SEARCH_ENABLED=0
CHARACTER_IMAGE_GENERATION_ENABLED=1
CHARACTER_STORAGE_DIR=/var/lib/clipfender/characters
```

4. Дождаться deploy.
5. Проверить `/health` — должен быть HTTP 200 и `{"status":"ok"}`.
6. Войти с `ADMIN_EMAILS` и `ADMIN_BOOTSTRAP_PASSWORD`.
7. После успешного первого входа удалить `ADMIN_BOOTSTRAP_PASSWORD` из Render.

## 3. Домен

После успешного deploy добавить custom domain в Render и установить DNS-записи, которые покажет Render.

После подключения домена обновить:

```text
PUBLIC_BASE_URL=https://реальный-домен
ALLOWED_ORIGINS=https://реальный-домен
```

Если используется `www`, можно указать обе origin через запятую.

## 4. Первый production smoke-test

Проверить:

```text
/health
/
/search
/archive
/characters
/characters/jon-snow
/characters/barristan-selmy
/guides
/help
/faq
/project
/library
/login
/contacts
/privacy
/terms
/copyright
/sitemap.xml
/robots.txt
```

Затем:

- зарегистрировать обычного пользователя;
- войти/выйти;
- выполнить реальный YouTube search;
- применить фильтр;
- открыть YouTube source;
- открыть archive;
- открыть Idea Mode;
- ввести нового персонажа и дождаться portrait discovery;
- открыть новую карточку персонажа;
- перезапустить/redeploy service и проверить, что portrait сохранился.

## 5. Важные ограничения

- Persistent Disk на Render нужен для сохранения SQLite и динамически созданных portraits.
- Для нескольких экземпляров web service SQLite + disk не подходят; используйте PostgreSQL и отдельное хранилище.
- Генерация новых portraits расходует OpenAI API budget; `CHARACTER_GENERATION_DAILY_GUARD` и per-IP discovery rate limit ограничивают расходы.
- Старый Bing Image Search provider не используется.
