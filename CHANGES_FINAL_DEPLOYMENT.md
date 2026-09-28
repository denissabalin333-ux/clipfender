# ClipFender — final deployment hardening

## What was fixed

1. Dynamic character portraits no longer live under the source tree in production. `CHARACTER_STORAGE_DIR` is `/var/lib/clipfender/characters` on Render and `/app/data/characters` in Docker Compose. The `/media/characters/<slug>-hq.webp` route serves only validated portrait filenames from that persistent directory.
2. Legacy generated portraits already stored under the old source-tree directory are migrated to persistent storage on startup and the database URL is updated.
3. Production `.env` values are loaded before environment-sensitive backend modules import their module-level settings. This fixes local `.env` configuration for YouTube, database, search limits and automatic portraits.
4. Production health fails with HTTP 503 when required deployment configuration is missing: YouTube key, admin allowlist, HTTPS public URL/origins, persistent DB path, and OpenAI key when automatic generation is enabled.
5. Render Blueprint now declares the OpenAI secret, persistent portrait path, auto-generation settings, rate limits and proxy settings.
6. Legacy Bing Image Search integration is permanently disabled. It is kept only as historical code; it is not called by the active pipeline.
7. Character discovery endpoint is CSRF-protected as well as rate-limited.
8. Character discovery frontend obtains a CSRF cookie before invoking the endpoint when the cookie is missing.
9. Render/proxy-aware security helpers read `X-Forwarded-Proto` for secure cookies and `X-Forwarded-For` for per-client rate limiting when proxy trust is enabled.
10. A one-time startup admin bootstrap was added. If `ADMIN_EMAILS` has no corresponding account and `ADMIN_BOOTSTRAP_PASSWORD` is provided, the account is created with Argon2. Existing users are never overwritten. Remove the bootstrap secret after first successful admin login.
11. Dynamic sitemap generation now reads the current ready character catalog on every request, so newly discovered characters can appear without a service restart.
12. Dynamic portrait responses use a finite cache lifetime (`max-age=86400`) instead of `immutable`, so a regenerated portrait can replace a previous file without permanent browser caching.
13. Runtime dependency versions in `requirements.txt` are pinned to the tested production baseline.
14. `.gitignore` now excludes internal `_backup/`, `_archive/`, evidence, ZIP and checksum artifacts from accidental Git publication. These directories remain in the local release ZIP as required by the project workflow.

## Owner actions before public launch

Set in Render Environment Variables/Secrets:

```text
APP_ENV=production
YOUTUBE_API_KEY=...
OPENAI_API_KEY=...
ADMIN_EMAILS=you@example.com
ADMIN_BOOTSTRAP_PASSWORD=<strong one-time secret>
ALLOWED_ORIGINS=https://your-real-domain.example
PUBLIC_BASE_URL=https://your-real-domain.example
```

Keep:

```text
CHARACTER_IMAGE_SEARCH_ENABLED=0
CHARACTER_IMAGE_GENERATION_ENABLED=1
CHARACTER_STORAGE_DIR=/var/lib/clipfender/characters
CLIPFINDER_DB_PATH=/var/lib/clipfender/clipfinder.db
```

Deploy only after the Render Persistent Disk is attached at `/var/lib/clipfender`.

## Verification

- Python compile: PASS
- Frontend JS syntax check: PASS
- pytest: PASS
- production configuration/route smoke: PASS
- `.env` secret scan: PASS
- original production `clipfinder.db` restored before packaging
