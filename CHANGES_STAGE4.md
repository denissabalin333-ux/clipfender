# ClipFender — Stage 4 backend hardening

## Added
- FastAPI `lifespan` startup/shutdown flow.
- Explicit production CORS configuration via `ALLOWED_ORIGINS`.
- SQLite-backed shared search rate limiting for multi-worker deployments.
- Security headers and a CSP compatible with local fonts and the official YouTube iframe.
- Database-aware `/health` check while preserving the existing JSON shape on success.
- Unified API handling for validation and unhandled server errors (`detail` remains the top-level error field).
- Safer query and YouTube video ID validation.
- Sanitized YouTube/backend error messages with server-side logging.
- pytest coverage for search, scoring, edit filter, video endpoint, health and CORS.
- `requirements-dev.txt` and `pytest.ini`.

## Preserved
- `/api/search`, `/api/load-more`, `/api/quota`, `/api/video/{id}`, `/health` routes.
- Existing successful response structures.
- YouTube cache, quota guard, scoring and edit-filter logic.
- `clipfinder.db` contents.
