"""Server-side user library: favorites, collections, search history and saved filters."""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from backend.database.database import get_connection
from backend.security import get_current_user, require_csrf

router = APIRouter(prefix="/library", tags=["library"])

VIDEO_FIELDS = (
    "id", "title", "channel", "thumbnail", "url", "views", "published_at", "duration",
    "is_short", "is_4k", "is_hd", "is_clean", "is_action", "is_clip", "is_cinematic",
    "is_gameplay", "is_dynamic", "has_music", "has_voice", "has_dialogue", "is_raw_footage",
    "is_no_music", "score", "edit_score", "description", "music_confidence", "voice_confidence",
    "dialogue_confidence", "music_source", "voice_source", "dialogue_source", "query",
)


class FavoritePayload(BaseModel):
    video_id: str
    video: dict[str, Any] = Field(default_factory=dict)


class CollectionPayload(BaseModel):
    name: str
    description: str = ""


class CollectionItemPayload(BaseModel):
    video_id: str
    video: dict[str, Any] = Field(default_factory=dict)


class HistoryPayload(BaseModel):
    query: str
    params: dict[str, Any] = Field(default_factory=dict)


class SavedFilterPayload(BaseModel):
    name: str
    query: str = ""
    filters: dict[str, Any] = Field(default_factory=dict)


class BookmarkPayload(BaseModel):
    video_id: str
    start_seconds: float = Field(ge=0, le=86400)
    end_seconds: float = Field(gt=0, le=86400)
    note: str = Field(default="", max_length=500)
    video: dict[str, Any] = Field(default_factory=dict)


def _user_id(request: Request) -> int:
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Войди в ClipFender, чтобы использовать библиотеку.")
    return int(user["id"])


def _clean_text(value: Any, limit: int) -> str:
    return " ".join(str(value or "").strip().split())[:limit]


def _snapshot(video_id: str, video: dict[str, Any]) -> str:
    clean: dict[str, Any] = {}
    for key in VIDEO_FIELDS:
        if key in video:
            value = video[key]
            if isinstance(value, (str, int, float, bool)) or value is None:
                clean[key] = value
    clean["id"] = str(video_id)[:128]
    return json.dumps(clean, ensure_ascii=False, separators=(",", ":"))[:24000]


def _decode_snapshot(row) -> dict[str, Any]:
    try:
        value = json.loads(row["video_json"] or "{}")
        return value if isinstance(value, dict) else {"id": row["video_id"]}
    except (TypeError, ValueError):
        return {"id": row["video_id"]}


def _collection_owned(connection, user_id: int, collection_id: int):
    row = connection.execute(
        "SELECT id, name, description, created_at, updated_at FROM collections WHERE id = ? AND user_id = ?",
        (collection_id, user_id),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Коллекция не найдена")
    return row


@router.get("/favorites")
def favorites(request: Request):
    user_id = _user_id(request)
    connection = get_connection()
    try:
        rows = connection.execute(
            "SELECT video_id, video_json, created_at, updated_at FROM user_favorites WHERE user_id = ? ORDER BY updated_at DESC, created_at DESC",
            (user_id,),
        ).fetchall()
        return {"items": [dict(video=_decode_snapshot(row), video_id=row["video_id"], created_at=row["created_at"], updated_at=row["updated_at"]) for row in rows]}
    finally:
        connection.close()


@router.post("/favorites")
def add_favorite(payload: FavoritePayload, request: Request):
    user_id = _user_id(request)
    require_csrf(request)
    video_id = _clean_text(payload.video_id, 128)
    if not video_id:
        raise HTTPException(status_code=422, detail="video_id обязателен")
    video_json = _snapshot(video_id, payload.video)
    connection = get_connection()
    try:
        connection.execute(
            """
            INSERT INTO user_favorites (user_id, video_id, video_json)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, video_id) DO UPDATE SET
                video_json=excluded.video_json,
                updated_at=CURRENT_TIMESTAMP
            """,
            (user_id, video_id, video_json),
        )
        connection.commit()
        return {"ok": True, "video_id": video_id}
    finally:
        connection.close()


@router.delete("/favorites/{video_id}")
def delete_favorite(video_id: str, request: Request):
    user_id = _user_id(request)
    require_csrf(request)
    connection = get_connection()
    try:
        connection.execute("DELETE FROM user_favorites WHERE user_id = ? AND video_id = ?", (user_id, video_id))
        connection.commit()
        return {"ok": True, "video_id": video_id}
    finally:
        connection.close()


@router.get("/collections")
def collections(request: Request):
    user_id = _user_id(request)
    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT c.id, c.name, c.description, c.created_at, c.updated_at,
                   COUNT(ci.video_id) AS item_count
            FROM collections c
            LEFT JOIN collection_items ci ON ci.collection_id = c.id
            WHERE c.user_id = ?
            GROUP BY c.id
            ORDER BY c.updated_at DESC, c.created_at DESC
            """,
            (user_id,),
        ).fetchall()
        return {"items": [dict(row) for row in rows]}
    finally:
        connection.close()


@router.post("/collections")
def create_collection(payload: CollectionPayload, request: Request):
    user_id = _user_id(request)
    require_csrf(request)
    name = _clean_text(payload.name, 80)
    description = _clean_text(payload.description, 500)
    if len(name) < 2:
        raise HTTPException(status_code=422, detail="Название коллекции слишком короткое")
    connection = get_connection()
    try:
        count = connection.execute("SELECT COUNT(*) AS c FROM collections WHERE user_id = ?", (user_id,)).fetchone()["c"]
        if int(count) >= 50:
            raise HTTPException(status_code=409, detail="Можно создать не более 50 коллекций")
        cursor = connection.execute("INSERT INTO collections (user_id, name, description) VALUES (?, ?, ?)", (user_id, name, description))
        connection.commit()
        return {"ok": True, "id": int(cursor.lastrowid), "name": name, "description": description, "item_count": 0}
    finally:
        connection.close()


@router.delete("/collections/{collection_id}")
def delete_collection(collection_id: int, request: Request):
    user_id = _user_id(request)
    require_csrf(request)
    connection = get_connection()
    try:
        _collection_owned(connection, user_id, collection_id)
        connection.execute("DELETE FROM collection_items WHERE collection_id = ?", (collection_id,))
        connection.execute("DELETE FROM collections WHERE id = ? AND user_id = ?", (collection_id, user_id))
        connection.commit()
        return {"ok": True, "id": collection_id}
    finally:
        connection.close()


@router.get("/collections/{collection_id}")
def collection_detail(collection_id: int, request: Request):
    user_id = _user_id(request)
    connection = get_connection()
    try:
        collection = _collection_owned(connection, user_id, collection_id)
        rows = connection.execute(
            "SELECT video_id, video_json, created_at FROM collection_items WHERE collection_id = ? ORDER BY created_at DESC",
            (collection_id,),
        ).fetchall()
        return {
            "collection": dict(collection),
            "items": [dict(video_id=row["video_id"], video=_decode_snapshot(row), created_at=row["created_at"]) for row in rows],
        }
    finally:
        connection.close()


@router.post("/collections/{collection_id}/items")
def add_collection_item(collection_id: int, payload: CollectionItemPayload, request: Request):
    user_id = _user_id(request)
    require_csrf(request)
    connection = get_connection()
    try:
        _collection_owned(connection, user_id, collection_id)
        video_id = _clean_text(payload.video_id, 128)
        connection.execute(
            "INSERT INTO collection_items (collection_id, video_id, video_json) VALUES (?, ?, ?) ON CONFLICT(collection_id, video_id) DO UPDATE SET video_json=excluded.video_json",
            (collection_id, video_id, _snapshot(video_id, payload.video)),
        )
        connection.execute("UPDATE collections SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (collection_id,))
        connection.commit()
        return {"ok": True, "collection_id": collection_id, "video_id": video_id}
    finally:
        connection.close()


@router.delete("/collections/{collection_id}/items/{video_id}")
def delete_collection_item(collection_id: int, video_id: str, request: Request):
    user_id = _user_id(request)
    require_csrf(request)
    connection = get_connection()
    try:
        _collection_owned(connection, user_id, collection_id)
        connection.execute("DELETE FROM collection_items WHERE collection_id = ? AND video_id = ?", (collection_id, video_id))
        connection.execute("UPDATE collections SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (collection_id,))
        connection.commit()
        return {"ok": True}
    finally:
        connection.close()


@router.get("/history")
def history(request: Request, limit: int = 50):
    user_id = _user_id(request)
    limit = max(1, min(int(limit), 100))
    connection = get_connection()
    try:
        rows = connection.execute(
            "SELECT id, query, params_json, created_at FROM search_history WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        items = []
        for row in rows:
            try:
                params = json.loads(row["params_json"] or "{}")
            except ValueError:
                params = {}
            items.append({"id": row["id"], "query": row["query"], "params": params, "created_at": row["created_at"]})
        return {"items": items}
    finally:
        connection.close()


@router.post("/history")
def record_history(payload: HistoryPayload, request: Request):
    user_id = _user_id(request)
    require_csrf(request)
    query = _clean_text(payload.query, 120)
    if not query:
        raise HTTPException(status_code=422, detail="query обязателен")
    params_json = json.dumps(payload.params, ensure_ascii=False, separators=(",", ":"))[:12000]
    connection = get_connection()
    try:
        connection.execute("INSERT INTO search_history (user_id, query, params_json) VALUES (?, ?, ?)", (user_id, query, params_json))
        connection.execute(
            "DELETE FROM search_history WHERE user_id = ? AND id NOT IN (SELECT id FROM search_history WHERE user_id = ? ORDER BY id DESC LIMIT 100)",
            (user_id, user_id),
        )
        connection.commit()
        return {"ok": True}
    finally:
        connection.close()


@router.delete("/history")
def clear_history(request: Request):
    user_id = _user_id(request)
    require_csrf(request)
    connection = get_connection()
    try:
        connection.execute("DELETE FROM search_history WHERE user_id = ?", (user_id,))
        connection.commit()
        return {"ok": True}
    finally:
        connection.close()


@router.get("/filters")
def saved_filters(request: Request):
    user_id = _user_id(request)
    connection = get_connection()
    try:
        rows = connection.execute("SELECT id, name, query, filters_json, created_at, updated_at FROM saved_filters WHERE user_id = ? ORDER BY updated_at DESC, id DESC", (user_id,)).fetchall()
        items = []
        for row in rows:
            try:
                filters = json.loads(row["filters_json"] or "{}")
            except ValueError:
                filters = {}
            items.append({"id": row["id"], "name": row["name"], "query": row["query"], "filters": filters, "created_at": row["created_at"], "updated_at": row["updated_at"]})
        return {"items": items}
    finally:
        connection.close()


@router.post("/filters")
def create_saved_filter(payload: SavedFilterPayload, request: Request):
    user_id = _user_id(request)
    require_csrf(request)
    name = _clean_text(payload.name, 80)
    query = _clean_text(payload.query, 120)
    if len(name) < 2:
        raise HTTPException(status_code=422, detail="Название сохранённого фильтра слишком короткое")
    filters_json = json.dumps(payload.filters, ensure_ascii=False, separators=(",", ":"))[:16000]
    connection = get_connection()
    try:
        count = connection.execute("SELECT COUNT(*) AS c FROM saved_filters WHERE user_id = ?", (user_id,)).fetchone()["c"]
        if int(count) >= 50:
            raise HTTPException(status_code=409, detail="Можно сохранить не более 50 наборов фильтров")
        cursor = connection.execute("INSERT INTO saved_filters (user_id, name, query, filters_json) VALUES (?, ?, ?, ?)", (user_id, name, query, filters_json))
        connection.commit()
        return {"ok": True, "id": int(cursor.lastrowid), "name": name}
    finally:
        connection.close()


@router.delete("/filters/{filter_id}")
def delete_saved_filter(filter_id: int, request: Request):
    user_id = _user_id(request)
    require_csrf(request)
    connection = get_connection()
    try:
        connection.execute("DELETE FROM saved_filters WHERE id = ? AND user_id = ?", (filter_id, user_id))
        connection.commit()
        return {"ok": True, "id": filter_id}
    finally:
        connection.close()


@router.get("/export")
def export_library(request: Request, format: str = "json", collection_id: int | None = None):
    user_id = _user_id(request)
    fmt = str(format or "json").lower()
    if fmt not in {"json", "csv", "markdown"}:
        raise HTTPException(status_code=422, detail="format должен быть json, csv или markdown")

    connection = get_connection()
    try:
        collection_meta = None
        if collection_id is not None:
            collection_meta = _collection_owned(connection, user_id, collection_id)
            rows = connection.execute("SELECT video_id, video_json, created_at FROM collection_items WHERE collection_id = ? ORDER BY created_at DESC", (collection_id,)).fetchall()
            items = [_decode_snapshot(row) for row in rows]
            label = collection_meta["name"]
        else:
            rows = connection.execute("SELECT video_id, video_json, created_at FROM user_favorites WHERE user_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()
            items = [_decode_snapshot(row) for row in rows]
            label = "ClipFender Favorites"

        filename = "clipfender_collection" if collection_id is not None else "clipfender_favorites"
        if fmt == "json":
            payload = json.dumps({"name": label, "exported_at": datetime.now(timezone.utc).isoformat(), "items": items}, ensure_ascii=False, indent=2)
            return Response(payload, media_type="application/json; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{filename}.json"'})

        if fmt == "csv":
            buffer = io.StringIO(newline="")
            writer = csv.DictWriter(buffer, fieldnames=["id", "title", "channel", "url", "duration", "edit_score", "score", "views", "published_at"], extrasaction="ignore")
            writer.writeheader()
            writer.writerows(items)
            content = "\ufeff" + buffer.getvalue()
            return Response(content, media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{filename}.csv"'})

        lines = [f"# {label}", "", "Экспорт из ClipFender.", ""]
        for index, item in enumerate(items, 1):
            title = str(item.get("title") or "Без названия").strip()
            url = str(item.get("url") or "").strip()
            score = item.get("edit_score", item.get("score", 0))
            channel = str(item.get("channel") or "").strip()
            duration = str(item.get("duration") or "—").strip()
            lines.extend([f"## {index}. {title}", f"- Канал: {channel or '—'}", f"- Длительность: {duration}", f"- Edit Score: {score}", f"- YouTube: {url}", ""])
        return Response("\n".join(lines), media_type="text/markdown; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{filename}.md"'})
    finally:
        connection.close()

@router.get("/bookmarks")
def bookmarks(request: Request, video_id: str | None = None):
    user_id = _user_id(request)
    connection = get_connection()
    try:
        if video_id:
            rows = connection.execute(
                "SELECT id, video_id, video_json, start_seconds, end_seconds, note, created_at, updated_at FROM bookmarks WHERE user_id = ? AND video_id = ? ORDER BY start_seconds ASC, created_at ASC",
                (user_id, _clean_text(video_id, 128)),
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT id, video_id, video_json, start_seconds, end_seconds, note, created_at, updated_at FROM bookmarks WHERE user_id = ? ORDER BY created_at DESC LIMIT 200",
                (user_id,),
            ).fetchall()
        return {
            "items": [
                {
                    "id": row["id"],
                    "video_id": row["video_id"],
                    "video": _decode_snapshot(row),
                    "start_seconds": row["start_seconds"],
                    "end_seconds": row["end_seconds"],
                    "note": row["note"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
                for row in rows
            ]
        }
    finally:
        connection.close()


@router.post("/bookmarks")
def add_bookmark(payload: BookmarkPayload, request: Request):
    user_id = _user_id(request)
    require_csrf(request)
    video_id = _clean_text(payload.video_id, 128)
    if not video_id:
        raise HTTPException(status_code=422, detail="video_id обязателен")
    if float(payload.end_seconds) <= float(payload.start_seconds):
        raise HTTPException(status_code=422, detail="Конец таймкода должен быть позже начала")
    connection = get_connection()
    try:
        cursor = connection.execute(
            "INSERT INTO bookmarks (user_id, video_id, video_json, start_seconds, end_seconds, note) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, video_id, _snapshot(video_id, payload.video), float(payload.start_seconds), float(payload.end_seconds), _clean_text(payload.note, 500)),
        )
        connection.commit()
        return {"ok": True, "id": int(cursor.lastrowid), "video_id": video_id}
    finally:
        connection.close()


@router.delete("/bookmarks/{bookmark_id}")
def delete_bookmark(bookmark_id: int, request: Request):
    user_id = _user_id(request)
    require_csrf(request)
    connection = get_connection()
    try:
        cursor = connection.execute("DELETE FROM bookmarks WHERE id = ? AND user_id = ?", (int(bookmark_id), user_id))
        connection.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Закладка не найдена")
        return {"ok": True, "id": int(bookmark_id)}
    finally:
        connection.close()

