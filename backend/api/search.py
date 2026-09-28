from fastapi import APIRouter, HTTPException, Request
import logging

from backend.services.youtube import (
    search_youtube,
    YOUTUBE_FETCH_LIMIT,
)

from backend.services.scoring import (
    calculate_score,
    calculate_edit_suitability,
)

from backend.services.edit_filter import (
    is_edit_material,
)

from backend.database.database import (
    DATABASE_PATH,
    get_cached_videos,
    save_videos,
    get_search_state,
    save_search_state,
)

from backend.security import client_ip, consume_rate_limit


router = APIRouter()


# ============================================================
# QUOTA PROTECTION
# ============================================================

from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import os


logger = logging.getLogger("clipfender.search")

# Safety guard below YouTube's documented search.list daily limit.
SEARCH_DAILY_GUARD = int(os.getenv("SEARCH_DAILY_GUARD", "70") or 70)
SEARCH_REQUEST_MIN_INTERVAL = float(os.getenv("SEARCH_REQUEST_MIN_INTERVAL", "0.35") or 0.35)
SEARCH_RATE_LIMIT = int(os.getenv("SEARCH_RATE_LIMIT", "30") or 30)
SEARCH_RATE_WINDOW = int(os.getenv("SEARCH_RATE_WINDOW", "60") or 60)
_REQUEST_TIMES = {}

# One cache miss = one search.list page, max 50 results.
SAFE_YOUTUBE_FETCH_LIMIT = 50

LEGACY_CACHE_PREFIXES = (
    "clipfinder_pool_v10:",
    "edit_materials_pool_v9:",
    "edit_materials_pool_v8:",
    "edit_materials_pool_v7:",
    "edit_materials_v6:",
    "edit_materials_v5:",
    "edit_materials_v4:",
)


def _check_public_rate_limit(request: Request):
    """Enforce a small per-IP burst guard plus a SQLite-backed shared limit."""
    import time
    now = time.monotonic()
    host = client_ip(request)
    previous = _REQUEST_TIMES.get(host, 0.0)
    if now - previous < SEARCH_REQUEST_MIN_INTERVAL:
        raise HTTPException(
            status_code=429,
            detail="Слишком много запросов подряд. Подождите мгновение.",
            headers={"Retry-After": "1"},
        )
    _REQUEST_TIMES[host] = now

    allowed, retry_after = consume_rate_limit(
        f"search:{host}",
        SEARCH_RATE_LIMIT,
        SEARCH_RATE_WINDOW,
    )
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Слишком много поисковых запросов. Повтори позже.",
            headers={"Retry-After": str(max(1, retry_after))},
        )

    if len(_REQUEST_TIMES) > 5000:
        cutoff = now - 3600
        stale = [key for key, value in _REQUEST_TIMES.items() if value < cutoff]
        for key in stale[:1000]:
            _REQUEST_TIMES.pop(key, None)




def _validate_search_query(query: str, *, required: bool = False) -> str:
    clean = " ".join(str(query or "").strip().split())
    if required and not clean:
        raise HTTPException(status_code=400, detail="query обязателен")
    if len(clean) > 120:
        raise HTTPException(status_code=422, detail="query не может быть длиннее 120 символов")
    return clean


def _quota_day():
    """
    YouTube quota day.
    Используем UTC-8 как безопасный фиксированный
    ориентир для дневного счётчика приложения.
    """

    from datetime import timedelta

    now_utc = datetime.now(timezone.utc)

    pacific_time = (
        now_utc
        - timedelta(hours=8)
    )

    return pacific_time.strftime(
        "%Y-%m-%d"
    )


def _quota_connection():
    connection = sqlite3.connect(
        DATABASE_PATH,
        check_same_thread=False,
    )
    connection.row_factory = sqlite3.Row
    return connection


def _ensure_quota_table(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS clipfinder_quota_guard (
            bucket_date TEXT PRIMARY KEY,
            search_calls INTEGER NOT NULL DEFAULT 0
        )
        """
    )


def _reserve_search_quota():
    """
    Reserve one new search.list call atomically.
    Cached/local filtering never touches this counter.
    """

    day = _quota_day()
    connection = _quota_connection()

    try:
        cursor = connection.cursor()

        _ensure_quota_table(cursor)
        connection.commit()

        cursor.execute(
            "BEGIN IMMEDIATE"
        )

        cursor.execute(
            """
            SELECT search_calls
            FROM clipfinder_quota_guard
            WHERE bucket_date = ?
            """,
            (day,),
        )

        row = cursor.fetchone()

        used = (
            int(row["search_calls"])
            if row
            else 0
        )

        if used >= SEARCH_DAILY_GUARD:
            connection.rollback()

            return {
                "allowed": False,
                "used": used,
                "limit": SEARCH_DAILY_GUARD,
                "remaining": 0,
                "day": day,
            }

        new_used = used + 1

        cursor.execute(
            """
            INSERT INTO clipfinder_quota_guard (
                bucket_date,
                search_calls
            )
            VALUES (?, ?)

            ON CONFLICT(bucket_date)
            DO UPDATE SET
                search_calls = excluded.search_calls
            """,
            (
                day,
                new_used,
            ),
        )

        connection.commit()

        return {
            "allowed": True,
            "used": new_used,
            "limit": SEARCH_DAILY_GUARD,
            "remaining": (
                SEARCH_DAILY_GUARD
                - new_used
            ),
            "day": day,
        }

    finally:
        connection.close()


def _quota_status():

    day = _quota_day()
    connection = _quota_connection()

    try:
        cursor = connection.cursor()

        _ensure_quota_table(cursor)
        connection.commit()

        cursor.execute(
            """
            SELECT search_calls
            FROM clipfinder_quota_guard
            WHERE bucket_date = ?
            """,
            (day,),
        )

        row = cursor.fetchone()

        used = (
            int(row["search_calls"])
            if row
            else 0
        )

        return {
            "day": day,
            "used": used,
            "limit": SEARCH_DAILY_GUARD,
            "remaining": max(
                0,
                SEARCH_DAILY_GUARD - used,
            ),
        }

    finally:
        connection.close()


def _normalized_query(value):
    return " ".join(
        str(value or "")
        .strip()
        .lower()
        .split()
    )


def _legacy_cache(query):

    normalized = _normalized_query(
        query
    )

    for prefix in LEGACY_CACHE_PREFIXES:

        cached = get_cached_videos(
            prefix + normalized
        )

        if cached:
            return cached, prefix

    return [], None


# ============================================================
# REMOVE DUPLICATES
# ============================================================

def remove_duplicates(videos):

    seen = set()
    result = []

    for video in videos:

        video_id = video.get("id")

        if not video_id:
            continue

        if video_id in seen:
            continue

        seen.add(video_id)
        result.append(video)

    return result


# ============================================================
# SAFE INTEGER
# ============================================================

def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value, default=0):

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ============================================================
# DURATION TO SECONDS
# ============================================================

def duration_to_seconds(duration):

    if not duration:
        return 0

    try:
        parts = str(duration).split(":")

        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])

        if len(parts) == 3:
            return (
                int(parts[0]) * 3600
                + int(parts[1]) * 60
                + int(parts[2])
            )

    except (TypeError, ValueError):
        return 0

    return 0


# ============================================================
# EDIT SCORE 0-100
# ============================================================

def _soft_edit_pool(videos):
    """Drop only explicit non-editing junk; keep useful cinematic/gameplay/scene material."""
    return [video for video in videos if is_edit_material(video)]


def calculate_edit_score(video, query):

    score = 0

    title = str(
        video.get("title", "") or ""
    ).lower()

    description = str(
        video.get("description", "") or ""
    ).lower()

    text = title + " " + description
    # Explicit non-editing signals are most trustworthy in the title.
    title_text = title

    # --------------------------------------------------------
    # Relevance
    # --------------------------------------------------------

    relevance = 0
    query_text = " ".join(str(query or "").lower().split())
    query_words = [w for w in query_text.split() if len(w) >= 3]

    if query_text and query_text in title:
        relevance += 14

    matched = 0
    for word in query_words:
        if word in title:
            relevance += 4
            matched += 1
        elif word in description:
            relevance += 1

    if query_words and matched == len(query_words):
        relevance += 6

    score += min(relevance, 25)

    # --------------------------------------------------------
    # Material type
    # --------------------------------------------------------

    material = 0

    if video.get("is_cinematic"):
        material += 10

    if video.get("is_clip"):
        material += 8

    if video.get("is_action"):
        material += 8

    if video.get("is_dynamic"):
        material += 5

    if video.get("is_raw_footage"):
        material += 12

    for word in (
        "scene",
        "movie scene",
        "cinematic scene",
        "fight scene",
        "battle scene",
        "action scene",
        "cutscene",
        "footage",
        "raw footage",
        "b-roll",
    ):
        if word in text:
            material += 3

    score += min(material, 25)

    # --------------------------------------------------------
    # Quality
    # --------------------------------------------------------

    quality = 0

    if video.get("is_4k"):
        quality += 12
    elif video.get("is_hd"):
        quality += 7

    for word in (
        "8k",
        "4k",
        "2160p",
        "uhd",
        "hdr",
        "60fps",
        "120fps",
    ):
        if word in title:
            quality += 2

    score += min(quality, 20)

    # --------------------------------------------------------
    # Audio
    # --------------------------------------------------------

    audio = 0

    if video.get("is_no_music"):
        audio += 5

    if video.get("has_dialogue"):
        audio += 4

    if video.get("has_voice"):
        audio += 2

    if video.get("has_music"):
        audio += 2

    for word in (
        "no commentary",
        "without commentary",
        "clean audio",
        "dialogue",
        "conversation",
        "speech",
    ):
        if word in text:
            audio += 2

    score += min(audio, 15)

    # --------------------------------------------------------
    # Duration
    # --------------------------------------------------------

    duration = duration_to_seconds(
        video.get("duration", "")
    )

    if 5 <= duration <= 180:
        score += 10
    elif 181 <= duration <= 300:
        score += 7
    elif 301 <= duration <= 600:
        score += 4
    elif duration > 600:
        score += 2

    # --------------------------------------------------------
    # Positive words
    # --------------------------------------------------------

    for word in (
        "cinematic",
        "realistic",
        "rtx",
        "ray tracing",
        "shader",
        "shaders",
        "landscape",
        "environment",
        "showcase",
        "trailer",
        "battle",
        "fight",
        "action",
        "scene",
        "cutscene",
        "footage",
        "raw footage",
        "b-roll",
        "no hud",
        "no commentary",
    ):
        if word in text:
            score += 2

    # --------------------------------------------------------
    # Negative words
    # --------------------------------------------------------

    for word, penalty in {
        "reaction": 20,
        "review": 18,
        "podcast": 20,
        "tutorial": 18,
        "guide": 15,
        "stream": 20,
        "livestream": 20,
        "lets play": 15,
        "let's play": 15,
        "walkthrough": 10,
        "fan edit": 20,
        "amv": 20,
        "compilation": 8,
        "tiktok": 15,
        "instagram": 10,
    }.items():
        if word in title_text:
            score -= penalty

    # --------------------------------------------------------
    # Views bonus
    # --------------------------------------------------------

    views = safe_int(
        video.get("views", 0)
    )

    if views >= 100_000:
        score += 2

    if views >= 1_000_000:
        score += 3

    return max(
        0,
        min(
            100,
            int(score),
        ),
    )


# ============================================================
# HARD USER FILTERS
# ============================================================

def apply_filters(
    videos,
    shorts=None,
    hd=None,
    clean=None,
    action=None,
    has_music=None,
    has_voice=None,
    has_dialogue=None,
    material_type=None,
    video_type=None,
    quality=None,
    min_views=0,
    edit_min_score=0,
    duration_min=0,
    duration_max=0,
    filter_mode="smart",
    film=None,
):

    results = list(videos)

    # --------------------------------------------------------
    # Film / series soft metadata filter
    # --------------------------------------------------------

    if film:
        film_text = " ".join(str(film or "").strip().lower().split())
        if film_text:
            results = [
                video
                for video in results
                if film_text in " ".join(
                    str(video.get(key, "") or "").lower()
                    for key in ("title", "description", "channel")
                )
            ]

    # --------------------------------------------------------
    # Minimum views
    # --------------------------------------------------------

    results = [
        video
        for video in results
        if safe_int(video.get("views", 0)) >= min_views
    ]

    # --------------------------------------------------------
    # Edit Score threshold
    # --------------------------------------------------------

    if edit_min_score > 0 and material_type != "best_edit":
        results = [
            video
            for video in results
            if safe_float(video.get("edit_score", 0)) >= edit_min_score
        ]

    # "Лучшие для эдита" is an adaptive preset: prefer 90+, but never
    # return an empty list just because this query has fewer high-scoring
    # candidates. The final ranking still puts the highest scores first.

    # --------------------------------------------------------
    # Duration range (seconds)
    # --------------------------------------------------------

    if duration_min > 0 or duration_max > 0:
        filtered = []
        for video in results:
            seconds = duration_to_seconds(video.get("duration", ""))
            if duration_min > 0 and seconds < duration_min:
                continue
            if duration_max > 0 and seconds > duration_max:
                continue
            filtered.append(video)
        results = filtered

    # --------------------------------------------------------
    # Shorts
    # --------------------------------------------------------

    if shorts is not None:

        results = [
            video
            for video in results
            if bool(video.get("is_short", False)) == shorts
        ]

    # --------------------------------------------------------
    # HD
    # --------------------------------------------------------

    if hd is not None:

        results = [
            video
            for video in results
            if bool(video.get("is_hd", False)) == hd
        ]

    # --------------------------------------------------------
    # Clean
    # --------------------------------------------------------

    if clean is not None:

        results = [
            video
            for video in results
            if bool(video.get("is_clean", False)) == clean
        ]

    # --------------------------------------------------------
    # Action
    # --------------------------------------------------------

    if action is not None:

        results = [
            video
            for video in results
            if bool(video.get("is_action", False)) == action
        ]

    # --------------------------------------------------------
    # Music
    #
    # Теперь ЭТО НАСТОЯЩИЙ ФИЛЬТР.
    #
    # "С музыкой"   -> только has_music=True
    # "Без музыки"  -> только has_music=False
    # --------------------------------------------------------

    if filter_mode == "strict" and has_music is not None:

        results = [
            video
            for video in results
            if (
                str(video.get("music_confidence", "unknown")) in ("high", "medium")
                and bool(video.get("has_music", False)) == has_music
            )
        ]

    # --------------------------------------------------------
    # Voice
    # --------------------------------------------------------

    if filter_mode == "strict" and has_voice is not None:

        results = [
            video
            for video in results
            if (
                str(video.get("voice_confidence", "unknown")) in ("high", "medium")
                and bool(video.get("has_voice", False)) == has_voice
            )
        ]

    # --------------------------------------------------------
    # Dialogue
    # --------------------------------------------------------

    if filter_mode == "strict" and has_dialogue is not None:

        results = [
            video
            for video in results
            if (
                str(video.get("dialogue_confidence", "unknown")) in ("high", "medium")
                and bool(video.get("has_dialogue", False)) == has_dialogue
            )
        ]

    # --------------------------------------------------------
    # Material type
    # --------------------------------------------------------

    if material_type == "best_edit":

        # Keep all edit-eligible rows, then prioritize 90+ candidates.
        # If there are fewer than 90+ rows, lower-scoring rows stay visible
        # instead of producing a misleading empty state.
        results = list(results)

    elif filter_mode == "strict" and material_type == "cinematic":

        results = [
            video
            for video in results
            if bool(video.get("is_cinematic", False))
        ]

    elif filter_mode == "strict" and material_type == "action":

        results = [
            video
            for video in results
            if bool(video.get("is_action", False))
        ]

    elif filter_mode == "strict" and material_type == "gameplay":

        results = [
            video
            for video in results
            if bool(video.get("is_gameplay", False))
        ]

    elif filter_mode == "strict" and material_type == "raw_footage":

        results = [
            video
            for video in results
            if bool(video.get("is_raw_footage", False))
        ]

    # --------------------------------------------------------
    # Video type
    # --------------------------------------------------------

    if video_type == "short":

        results = [
            video
            for video in results
            if bool(video.get("is_short", False))
        ]

    elif video_type == "regular":

        results = [
            video
            for video in results
            if not bool(video.get("is_short", False))
        ]

    # --------------------------------------------------------
    # Quality
    # --------------------------------------------------------

    if quality == "hd":

        results = [
            video
            for video in results
            if bool(video.get("is_hd", False))
        ]

    elif quality == "sd":

        results = [
            video
            for video in results
            if not bool(video.get("is_hd", False))
        ]

    return results


# ============================================================
# SMART PREFERENCES
# ============================================================

def apply_preferences(videos, has_music=None, has_voice=None, has_dialogue=None, material_type=None):
    """Soft preferences: matching videos are promoted without deleting unknown/non-matching rows."""
    results = []
    for video in videos:
        bonus = 0
        if has_music is not None:
            confidence = str(video.get("music_confidence", "unknown"))
            if confidence in ("high", "medium") and bool(video.get("has_music", False)) == has_music:
                bonus += 12
        if has_voice is not None:
            confidence = str(video.get("voice_confidence", "unknown"))
            if confidence in ("high", "medium") and bool(video.get("has_voice", False)) == has_voice:
                bonus += 10
        if has_dialogue is not None:
            confidence = str(video.get("dialogue_confidence", "unknown"))
            if confidence in ("high", "medium") and bool(video.get("has_dialogue", False)) == has_dialogue:
                bonus += 10
        if material_type:
            matches = {
                "best_edit": safe_float(video.get("edit_score", 0)) >= 90,
                "cinematic": bool(video.get("is_cinematic", False)),
                "action": bool(video.get("is_action", False)),
                "gameplay": bool(video.get("is_gameplay", False)),
                "raw_footage": bool(video.get("is_raw_footage", False)),
            }
            if matches.get(material_type, False):
                bonus += 18
            if material_type == "best_edit":
                bonus += int(max(0, min(12, safe_float(video.get("edit_score", 0)) - 78)) / 2)
        copy = dict(video)
        copy["preference_score"] = bonus
        results.append(copy)
    return results


# ============================================================
# SORT
# ============================================================

def sort_videos(videos, sort, query=None, film=None):
    """Always rank edit-suitable material first, then apply the user sort.

    This is intentionally backend-side so archive, normal search, cached results,
    and load-more pools obey the same primary ranking rule.
    """
    ordered = list(videos)

    for video in ordered:
        suitability = calculate_edit_suitability(video, query=query, film=film)
        video["edit_suitability_score"] = suitability["score"]
        video["score_estimated"] = suitability["estimated"]
        video["score_version"] = suitability["version"]

    # Secondary sort: preserve the user's preference only inside the same
    # primary suitability tier. Stable sorting makes the primary criterion
    # absolute while keeping views/newest/oldest/score meaningful.
    if sort == "views":
        ordered.sort(key=lambda video: safe_int(video.get("views", 0)), reverse=True)
    elif sort == "score":
        ordered.sort(
            key=lambda video: (
                safe_float(video.get("edit_score", 0)) + safe_float(video.get("preference_score", 0)),
                safe_float(video.get("score", 0)),
                safe_int(video.get("views", 0)),
                bool(video.get("is_4k", False)),
                str(video.get("id", "")),
            ),
            reverse=True,
        )
    elif sort == "newest":
        ordered.sort(key=lambda video: str(video.get("published_at", "") or ""), reverse=True)
    elif sort == "oldest":
        ordered.sort(key=lambda video: str(video.get("published_at", "") or ""))

    ordered.sort(
        key=lambda video: (
            not bool(video.get("score_estimated", False)),
            safe_float(video.get("edit_suitability_score", 0)),
        ),
        reverse=True,
    )
    return ordered


# ============================================================
# RESPONSE
# ============================================================

def build_response(
    query,
    results,
    source,
    page,
    limit,
    youtube_total=None,
    pool_total=None,
    has_more_youtube=False,
    youtube_loaded=None,
    film=None,
):

    total = len(results)

    total_pages = (
        (total + limit - 1) // limit
        if total > 0
        else 0
    )

    offset = (
        page - 1
    ) * limit

    page_results = results[
        offset:offset + limit
    ]

    return {
        "query": query,
        "film": film or "",
        "results": page_results,
        "source": source,
        "search_mode": "edit_materials",
        "pool_total": pool_total if pool_total is not None else total,
        "edit_pool_total": pool_total if pool_total is not None else total,
        "filtered_total": total,
        "audio_detection": "metadata_only",
        "has_more_youtube": bool(has_more_youtube),
        "youtube_loaded": youtube_loaded if youtube_loaded is not None else (pool_total if pool_total is not None else total),
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "youtube_total": youtube_total,
            "total_pages": total_pages,
            "returned": len(page_results),
            "has_next": page < total_pages,
            "has_previous": page > 1,
        },
    }


# ============================================================
# SEARCH
# ============================================================

@router.get("/search")
def search(
    request: Request,
    query: str,
    shorts: bool | None = None,
    hd: bool | None = None,
    clean: bool | None = None,
    action: bool | None = None,

    has_music: bool | None = None,
    has_voice: bool | None = None,
    has_dialogue: bool | None = None,

    material_type: str | None = None,
    edit_min_score: int = 0,
    duration_min: int = 0,
    duration_max: int = 0,
    filter_mode: str = "smart",

    video_type: str | None = None,
    quality: str | None = None,
    min_views: int = 0,
    sort: str = "score",
    limit: int = 20,
    page: int = 1,
    film: str | None = None,
):

    _check_public_rate_limit(request)

    query = _validate_search_query(query)
    film = _validate_search_query(film or "") if film else ""

    if not query:

        return build_response(
            query="",
            results=[],
            source="none",
            page=1,
            limit=limit,
            youtube_total=0,
        )

    if limit < 1:
        limit = 1

    if limit > 50:
        limit = 50

    if page < 1:
        page = 1

    if min_views < 0:
        min_views = 0

    edit_min_score = max(0, min(100, int(edit_min_score or 0)))
    duration_min = max(0, int(duration_min or 0))
    duration_max = max(0, int(duration_max or 0))
    if duration_max and duration_min and duration_max < duration_min:
        duration_min, duration_max = duration_max, duration_min

    if filter_mode not in ("smart", "strict"):
        raise HTTPException(status_code=400, detail="filter_mode должен быть smart или strict")

    if video_type not in (
        None,
        "short",
        "regular",
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "video_type должен быть "
                "'short' или 'regular'"
            ),
        )

    if quality not in (
        None,
        "hd",
        "sd",
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "quality должен быть "
                "'hd' или 'sd'"
            ),
        )

    if material_type not in (
        None,
        "best_edit",
        "cinematic",
        "action",
        "gameplay",
        "raw_footage",
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "material_type должен быть: "
                "best_edit, cinematic, action, gameplay или raw_footage"
            ),
        )

    allowed_sort = [
        "score",
        "views",
        "newest",
        "oldest",
    ]

    if sort not in allowed_sort:
        raise HTTPException(
            status_code=400,
            detail=(
                "sort должен быть: "
                "score, views, newest или oldest"
            ),
        )

    # --------------------------------------------------------
    # New cache version.
    #
    # Old V4/V5 caches are ignored.
    # --------------------------------------------------------

    normalized_query = _normalized_query(
        query
    )

    # One shared pool per unique query.
    # Filter values are not part of the cache key.
    cache_key = (
        "clipfinder_shared:"
        + normalized_query
    )

    # ========================================================
    # 1. CACHE
    # ========================================================

    cached_videos = get_cached_videos(
        cache_key
    )

    cache_source = "cache"

    if not cached_videos:

        cached_videos, legacy_prefix = _legacy_cache(
            normalized_query
        )

        if cached_videos:
            cache_source = (
                "legacy-cache:"
                + legacy_prefix
            )

    if cached_videos:

        state = get_search_state(cache_key) or {}
        cached_videos = _soft_edit_pool(cached_videos)

        # Recalculate ranking for cached rows so older cache entries
        # do not lose the newest edit-ranking rules.
        for video in cached_videos:
            video["edit_score"] = calculate_edit_score(video, query)
            video["score"] = calculate_score(
                title=video.get("title", ""),
                query=query,
                views=video.get("views", 0),
            ) + safe_float(video.get("edit_score", 0))

        results = apply_filters(
            cached_videos,
            shorts=shorts,
            hd=hd,
            clean=clean,
            action=action,
            has_music=has_music,
            has_voice=has_voice,
            has_dialogue=has_dialogue,
            material_type=material_type,
            video_type=video_type,
            quality=quality,
            min_views=min_views,
            edit_min_score=edit_min_score,
            duration_min=duration_min,
            duration_max=duration_max,
            filter_mode=filter_mode,
            film=film,
        )

        if filter_mode == "smart":
            results = apply_preferences(results, has_music, has_voice, has_dialogue, material_type)
        results = sort_videos(
            results,
            sort,
            query=query,
            film=film,
        )
        for video in results:
            video.pop("preference_score", None)

        results = remove_duplicates(
            results
        )

        return build_response(
            query=query,
            results=results,
            source=cache_source,
            page=page,
            limit=limit,
            youtube_total=(state.get("youtube_total") if state else None),
            pool_total=len(cached_videos),
            has_more_youtube=bool(state.get("next_page_token") if state else False),
            youtube_loaded=len(cached_videos),
            film=film,
        )

    # ========================================================
    # 2. YOUTUBE
    # ========================================================

    quota = _reserve_search_quota()

    if not quota["allowed"]:

        raise HTTPException(
            status_code=429,
            detail=(
                "ClipFinder включил защиту квоты. "
                "Новые обращения к YouTube сегодня "
                "временно отключены, чтобы не исчерпать "
                "квоту проекта. Сохранённые результаты "
                "продолжают работать."
            ),
            headers={
                "Retry-After": "3600",
            },
        )

    # ========================================================
    # 2. YOUTUBE — ONE PAGE ONLY
    # ========================================================

    try:

        videos, youtube_total, next_page_token = search_youtube(
            query,
            limit=SAFE_YOUTUBE_FETCH_LIMIT,
            return_total=True,
            return_next_page_token=True,
        )

    except Exception as error:
        logger.exception("YouTube search failed for query=%r", query, exc_info=error)
        raise HTTPException(
            status_code=503,
            detail="Не удалось получить данные YouTube. Повтори попытку позже.",
        ) from error

    videos = _soft_edit_pool(videos)

    videos = remove_duplicates(
        videos
    )

    # ========================================================
    # 3. BASE SCORE + EDIT SCORE
    # ========================================================

    all_results = []

    for video in videos:

        base_score = calculate_score(
            title=video.get("title", ""),
            query=query,
            views=video.get("views", 0),
        )

        edit_score = calculate_edit_score(
            video,
            query,
        )

        video["edit_score"] = edit_score

        video["score"] = (
            base_score
            + edit_score
        )

        all_results.append(
            video
        )

    # ========================================================
    # 5. SORT BASE RESULTS
    # ========================================================

    all_results = sort_videos(
        all_results,
        "score",
        query=query,
        film=film,
    )

    # ========================================================
    # 6. SAVE CACHE
    #
    # В кэш сохраняется полный набор результатов.
    # Выбранные пользовательские фильтры не записываются
    # в кэш, поэтому разные комбинации фильтров работают
    # независимо.
    # ========================================================

    save_videos(
        all_results,
        cache_key,
    )

    save_search_state(
        cache_key,
        next_page_token,
        youtube_total,
        1,
    )

    # ========================================================
    # 7. HARD USER FILTERS
    # ========================================================

    results = apply_filters(
        all_results,
        shorts=shorts,
        hd=hd,
        clean=clean,
        action=action,
        has_music=has_music,
        has_voice=has_voice,
        has_dialogue=has_dialogue,
        material_type=material_type,
        video_type=video_type,
        quality=quality,
        min_views=min_views,
        edit_min_score=edit_min_score,
        duration_min=duration_min,
        duration_max=duration_max,
        filter_mode=filter_mode,
        film=film,
    )

    # ========================================================
    # 8. SMART PREFERENCES / SORT AFTER FILTER
    # ========================================================

    if filter_mode == "smart":
        results = apply_preferences(
            results,
            has_music,
            has_voice,
            has_dialogue,
            material_type,
        )

    results = sort_videos(
        results,
        sort,
        query=query,
        film=film,
    )

    for video in results:
        video.pop("preference_score", None)

    # ========================================================
    # 9. REMOVE DUPLICATES
    # ========================================================

    results = remove_duplicates(
        results
    )

    # ========================================================
    # 10. RESPONSE
    # ========================================================

    return build_response(
        query=query,
        results=results,
        source="youtube",
        page=page,
        limit=limit,
        youtube_total=youtube_total,
        pool_total=len(all_results),
        has_more_youtube=bool(next_page_token),
        youtube_loaded=len(all_results),
        film=film,
    )


# ============================================================
# LOAD MORE YOUTUBE RESULTS
# ============================================================

@router.get("/load-more")
def load_more(
    request: Request,
    query: str,
):
    _check_public_rate_limit(request)
    query = _validate_search_query(query, required=True)

    normalized_query = _normalized_query(query)
    cache_key = "clipfinder_shared:" + normalized_query
    state = get_search_state(cache_key)

    if not state or not state.get("next_page_token"):
        return {
            "ok": False,
            "message": "Больше страниц YouTube для этого поиска сейчас нет.",
            "has_more_youtube": False,
        }

    quota = _reserve_search_quota()
    if not quota["allowed"]:
        raise HTTPException(
            status_code=429,
            detail="Защита квоты ClipFinder временно отключила новые запросы к YouTube.",
            headers={"Retry-After": "3600"},
        )

    try:
        videos, youtube_total, next_page_token = search_youtube(
            query,
            limit=SAFE_YOUTUBE_FETCH_LIMIT,
            return_total=True,
            page_token=str(state.get("next_page_token") or ""),
            return_next_page_token=True,
        )
    except Exception as error:
        logger.exception("YouTube load-more failed for query=%r", query, exc_info=error)
        raise HTTPException(
            status_code=503,
            detail="Не удалось загрузить следующую страницу YouTube. Повтори попытку позже.",
        ) from error

    videos = _soft_edit_pool(videos)
    videos = remove_duplicates(videos)

    scored = []
    for video in videos:
        video["edit_score"] = calculate_edit_score(video, query)
        video["score"] = calculate_score(
            title=video.get("title", ""),
            query=query,
            views=video.get("views", 0),
        ) + video["edit_score"]
        scored.append(video)

    save_videos(scored, cache_key)

    pages_loaded = int(state.get("pages_loaded") or 1) + 1
    save_search_state(cache_key, next_page_token, youtube_total, pages_loaded)

    full_pool = _soft_edit_pool(get_cached_videos(cache_key))

    return {
        "ok": True,
        "query": query,
        "loaded_now": len(scored),
        "pool_total": len(full_pool),
        "youtube_total": youtube_total,
        "has_more_youtube": bool(next_page_token),
        "source": "youtube",
    }


# ============================================================
# QUOTA STATUS
# ============================================================

@router.get("/quota")
def quota_status():
    return _quota_status()
