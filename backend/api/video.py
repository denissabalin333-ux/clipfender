import logging
import re

from fastapi import APIRouter, HTTPException

from backend.services.youtube import (
    get_video_details,
)
from backend.database.database import get_connection
from backend.services.scoring import calculate_edit_suitability, explain_edit_suitability


router = APIRouter()
logger = logging.getLogger("clipfender.video")
VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


@router.get("/video/{video_id}")
def get_video(video_id: str):

    # ==============================
    # ПРОВЕРКА ID
    # ==============================

    if not video_id:
        raise HTTPException(
            status_code=400,
            detail="video_id обязателен",
        )

    if not VIDEO_ID_RE.fullmatch(video_id):
        raise HTTPException(
            status_code=422,
            detail="Некорректный video_id",
        )

    # ==============================
    # ПОЛУЧАЕМ ДАННЫЕ YOUTUBE
    # ==============================

    try:
        details = get_video_details([video_id])
    except Exception as error:
        logger.exception("YouTube video details failed for video_id=%s", video_id, exc_info=error)
        raise HTTPException(
            status_code=503,
            detail="Не удалось получить данные видео. Повтори попытку позже.",
        ) from error

    video = details.get(video_id)

    # ==============================
    # НЕ НАЙДЕНО
    # ==============================

    if video is None:
        raise HTTPException(
            status_code=404,
            detail="Видео не найдено",
        )

    # ==============================
    # ОТВЕТ
    # ==============================

    return {
        "source": "youtube",
        "video": video,
    }

def _video_row(row):
    video = dict(row)
    for key in (
        "is_short", "is_4k", "is_hd", "is_clean", "is_action", "is_clip",
        "is_cinematic", "is_gameplay", "is_dynamic", "has_music", "has_voice",
        "has_dialogue", "is_raw_footage", "is_no_music",
    ):
        video[key] = bool(video.get(key, 0))
    return video


@router.get("/video/{video_id}/score-explanation")
def get_score_explanation(video_id: str, query: str = "", film: str = ""):
    if not VIDEO_ID_RE.fullmatch(video_id):
        raise HTTPException(status_code=422, detail="Некорректный video_id")
    connection = get_connection()
    try:
        row = connection.execute("SELECT * FROM videos WHERE id = ? LIMIT 1", (video_id,)).fetchone()
    finally:
        connection.close()
    if not row:
        raise HTTPException(status_code=404, detail="Материал отсутствует в локальной базе")
    video = _video_row(row)
    explanation = explain_edit_suitability(video, query=query or video.get("query", ""), film=film)
    return {"ok": True, "video_id": video_id, **explanation}


@router.get("/video/{video_id}/similar")
def get_similar_videos(video_id: str, limit: int = 6):
    if not VIDEO_ID_RE.fullmatch(video_id):
        raise HTTPException(status_code=422, detail="Некорректный video_id")
    limit = max(1, min(int(limit or 6), 12))
    connection = get_connection()
    try:
        target_row = connection.execute("SELECT * FROM videos WHERE id = ? LIMIT 1", (video_id,)).fetchone()
        if not target_row:
            raise HTTPException(status_code=404, detail="Материал отсутствует в локальной базе")
        target = _video_row(target_row)
        rows = connection.execute("SELECT * FROM videos WHERE id <> ? ORDER BY datetime(created_at) DESC LIMIT 250", (video_id,)).fetchall()
    finally:
        connection.close()

    stopwords = {
        "the", "and", "for", "with", "this", "that", "game", "video", "scene", "footage",
        "movie", "film", "edit", "clip", "raw", "test", "channel", "series", "episode",
        "это", "как", "для", "видео", "сцена", "ролик", "фильм", "серия", "и", "или",
    }
    target_title_tokens = {
        token for token in re.findall(r"[a-zа-я0-9]{3,}", str(target.get("title", "") or "").lower())
        if token not in stopwords
    }
    target_query_tokens = {
        token for token in re.findall(r"[a-zа-я0-9]{3,}", str(target.get("query", "") or "").lower())
        if token not in stopwords
    }
    candidates = []
    for row in rows:
        video = _video_row(row)
        title_tokens = {
            token for token in re.findall(r"[a-zа-я0-9]{3,}", str(video.get("title", "") or "").lower())
            if token not in stopwords
        }
        query_tokens = {
            token for token in re.findall(r"[a-zа-я0-9]{3,}", str(video.get("query", "") or "").lower())
            if token not in stopwords
        }
        title_overlap = len(target_title_tokens & title_tokens)
        query_overlap = len(target_query_tokens & query_tokens)
        overlap = title_overlap * 2 + query_overlap
        if overlap <= 0:
            continue
        suitability = calculate_edit_suitability(video, query=target.get("query", ""))
        video["edit_suitability_score"] = suitability["score"]
        video["score_estimated"] = suitability["estimated"]
        video["score_version"] = suitability["version"]
        candidates.append((
            not bool(video["score_estimated"]),
            video["edit_suitability_score"],
            overlap,
            video.get("edit_score", 0),
            video,
        ))
    candidates.sort(key=lambda item: item[:4], reverse=True)
    items = []
    for _, _, overlap, _, video in candidates[:limit]:
        items.append({
            "video_id": video.get("id", ""),
            "title": video.get("title", ""),
            "source": video.get("channel", ""),
            "thumbnail": video.get("thumbnail", ""),
            "url": video.get("url", ""),
            "duration": video.get("duration", ""),
            "edit_score": video.get("edit_score", 0),
            "edit_suitability_score": video.get("edit_suitability_score", 0),
            "score_estimated": bool(video.get("score_estimated", False)),
            "score_version": video.get("score_version", "stage8-v1"),
            "match_signals": overlap,
        })
    return {"ok": True, "video_id": video_id, "items": items, "count": len(items)}

