# Финальная проверка запуска

- [ ] Python 3.11+ установлен
- [ ] `start_git_bash.sh` или `start_windows.bat` запускается
- [ ] `.env` создан из `.env.example`
- [ ] `YOUTUBE_API_KEY` задан для реального YouTube-поиска
- [ ] `/health` возвращает `status=ok`
- [ ] `/` открывается без 500
- [ ] `/archive` выполняет поиск/фильтры
- [ ] `/login` открывается
- [ ] `/library` требует авторизацию для приватных данных
- [ ] `/contacts` принимает сообщение
- [ ] Docker запускается через `docker compose up --build`
- [ ] production `ALLOWED_ORIGINS` не равен `*`
- [ ] `.env` не попал в git/ZIP


## Public release — final production checks

- [ ] Render Persistent Disk is attached and mounted at `/var/lib/clipfender`
- [ ] `YOUTUBE_API_KEY` is configured in Render Secrets
- [ ] `OPENAI_API_KEY` is configured if automatic portrait discovery is enabled
- [ ] `ADMIN_EMAILS` contains the exact owner/admin email(s)
- [ ] `PUBLIC_BASE_URL` is the real HTTPS domain
- [ ] `ALLOWED_ORIGINS` contains only the real HTTPS origin(s)
- [ ] `CHARACTER_IMAGE_SEARCH_ENABLED=0` (legacy Bing path disabled)
- [ ] `CHARACTER_STORAGE_DIR=/var/lib/clipfender/characters`
- [ ] `/health` returns `{"status":"ok"}`
- [ ] Create one test account and verify login/logout
- [ ] Run a real YouTube search and verify cards + YouTube links
- [ ] Enter a new character name and verify the generated portrait remains after redeploy/restart
- [ ] Verify `/admin` is 401 for anonymous and 403 for non-admin
- [ ] Verify `/sitemap.xml`, `/robots.txt`, `/privacy`, `/terms`, `/copyright`
- [ ] Run `pytest -q` and CI before switching DNS to production
