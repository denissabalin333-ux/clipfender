# ClipFender — CHANGES_STAGE6

## Added
- Server-side user library API: favorites, collections, search history, saved filters, CSV/JSON/Markdown export.
- SQLite tables: `user_favorites`, `collections`, `collection_items`, `search_history`, `saved_filters`.
- `/library` page for authenticated users.
- Archive URL state (`q`, filters, sort, page) with Back/Forward restore.
- Server favorite synchronization on authenticated archive load.
- Save-search action and library navigation in archive tools.
- Collection-level CSV/JSON/Markdown export.
- `tests/test_library.py` and Stage 6 library client/API script.

## Changed
- `backend/main.py`: library router and `/library` route.
- `backend/database/database.py`: additive schema only.
- `frontend/components/header.html`: added Library navigation item.
- `frontend/css/app.css`: added library page stylesheet import.
- `frontend/js/stage6-library.js`: client-side URL state, server favorite sync, saved filters, library UI.

## Not changed
- Public search/video/quota endpoints and their response contracts.
- YouTube/scoring/edit-filter logic.
- `.env`.
- `clipfinder.db` (verified byte-for-byte unchanged against `_backup/stage6/clipfinder.db`).

## Not implemented in Stage 6
The optional S/C items from the project plan remain for later stages: timecode bookmarks/reference packs, similar-video recommendations, detailed Edit Score explanation, watermark/vertical/60fps/season filters, edit idea generator, character lore pages, PWA, localization, admin panel and reports.
