from __future__ import annotations

from datetime import datetime
from typing import Any
import sqlite3

from fastapi import APIRouter, Request
from backend.database.database import DATABASE_PATH
from fastapi import HTTPException

from backend.services.scoring import calculate_edit_suitability
from backend.api.search import (
    SAFE_YOUTUBE_FETCH_LIMIT,
    _check_public_rate_limit,
    _normalized_query,
    _reserve_search_quota,
    _soft_edit_pool,
    calculate_edit_score,
    calculate_score,
    remove_duplicates,
    sort_videos,
)
from backend.services.youtube import search_youtube
from backend.database.database import (
    get_cached_videos,
    get_search_state,
    save_search_state,
    save_videos,
)

router = APIRouter()

GENRES = {
    "action": {"action", "battle", "fight", "combat", "chase", "explosion", "war", "siege", "duel", "attack"},
    "drama": {"drama", "dramatic", "dialogue", "conflict", "betrayal", "politics", "decision", "grief", "argument"},
    "romance": {"romance", "love", "kiss", "relationship", "together", "wedding", "marry", "heart"},
    "horror_tragedy": {"horror", "terror", "fear", "death", "blood", "tragedy", "tragic", "murder", "scream", "doom", "dark"},
    "comedy": {"comedy", "funny", "humor", "humour", "laugh", "joke", "sarcasm", "comic"},
    "adventure": {"adventure", "journey", "travel", "quest", "explore", "escape", "road", "sea", "mountain"},
}

GENRE_LABELS = {
    "action": "экшн",
    "drama": "драма",
    "romance": "романтика",
    "horror_tragedy": "хоррор / трагедия",
    "comedy": "комедия",
    "adventure": "приключения",
}

GENRE_SEARCH_TERMS = {
    "action": "action battle fight",
    "drama": "drama dialogue conflict",
    "romance": "romance relationship emotional",
    "horror_tragedy": "horror tragedy dark death",
    "comedy": "comedy funny dialogue",
    "adventure": "adventure journey quest",
}


MOODS = {
    "action": {"action", "battle", "fight", "combat", "chase", "explosion"},
    "dark": {"dark", "night", "shadow", "death", "fear", "sorrow", "doom"},
    "drama": {"drama", "dramatic", "dialogue", "conflict", "betrayal"},
    "romance": {"romance", "love", "kiss", "relationship", "together"},
    "emotional": {"emotion", "emotional", "cry", "tears", "grief", "sad", "heart"},
    "epic": {"epic", "cinematic", "battle", "war", "king", "queen", "dragon"},
    "tension": {"tension", "threat", "danger", "confrontation", "fight", "chase"},
    "melancholy": {"melancholy", "lonely", "alone", "grief", "sad", "rain", "memory"},
}

TEMPO_VALUES = {"fast", "medium", "slow"}
MOOD_VALUES = set(MOODS)
GENRE_VALUES = set(GENRES)

STAGE_DEFS = (
    (
        "intro",
        "01",
        "ИНТРО",
        "Крупный план или спокойный вход, который задаёт персонажа и настроение.",
        {"cinematic": 5, "clean": 3, "emotional": 3, "drama": 2, "romance": 2},
    ),
    (
        "build_up",
        "02",
        "НАРАСТАНИЕ",
        "Переход от атмосферы к движению: диалог, напряжение и первые динамичные кадры.",
        {"dynamic": 4, "action": 4, "dialogue": 3, "tension": 3, "epic": 2},
    ),
    (
        "climax",
        "03",
        "КУЛЬМИНАЦИЯ",
        "Самые пригодные для нарезки динамичные и качественные материалы.",
        {"action": 7, "dynamic": 6, "raw": 4, "cinematic": 3, "epic": 3, "tension": 3},
    ),
    (
        "outro",
        "04",
        "КОНЦОВКА",
        "Финальный эмоциональный или кинематографичный кадр с местом для завершения монтажа.",
        {"cinematic": 5, "emotional": 4, "drama": 3, "romance": 3, "melancholy": 3},
    ),
)


def _clean(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _bool(value: Any) -> bool:
    return bool(value)


def _duration_seconds(value: Any) -> int:
    text = _clean(value)
    if not text:
        return 0
    try:
        parts = [int(part) for part in text.split(":")]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
    except (TypeError, ValueError):
        return 0
    return 0


def _duration_label(seconds: int) -> str:
    if seconds <= 0:
        return ""
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{sec:02d}"
    return f"{minutes}:{sec:02d}"


def _text(video: dict) -> str:
    return " ".join(
        _clean(video.get(key)).lower()
        for key in ("title", "description", "channel")
    )


def _mood_score(video: dict, mood: str) -> int:
    if mood not in MOOD_VALUES:
        return 0
    text = _text(video)
    score = 0
    for word in MOODS[mood]:
        if word in text:
            score += 2
    flags = {
        "action": ("is_action", "is_dynamic"),
        "dark": (),
        "drama": ("has_dialogue",),
        "romance": (),
        "emotional": (),
        "epic": ("is_cinematic", "is_action"),
        "tension": ("is_action", "is_dynamic"),
        "melancholy": ("is_cinematic",),
    }
    for key in flags.get(mood, ()):
        if _bool(video.get(key)):
            score += 3
    return min(score, 10)


def _tempo_score(video: dict, tempo: str) -> tuple[int, str]:
    if tempo not in TEMPO_VALUES:
        return 0, "none"
    text = _text(video)
    seconds = _duration_seconds(video.get("duration"))
    dynamic = _bool(video.get("is_dynamic")) or _bool(video.get("is_action"))
    fast_words = any(word in text for word in ("battle", "fight", "action", "chase", "explosion", "combat"))
    slow_words = any(word in text for word in ("dialogue", "emotional", "cinematic", "drama", "romance", "melancholy"))

    if tempo == "fast":
        score = (6 if dynamic else 0) + (3 if fast_words else 0) + (1 if 5 <= seconds <= 90 else 0)
    elif tempo == "slow":
        score = (4 if slow_words else 0) + (3 if _bool(video.get("is_cinematic")) else 0) + (2 if seconds >= 120 else 0) - (3 if dynamic else 0)
    else:
        score = (4 if not dynamic else 2) + (2 if 60 < seconds <= 180 else 0) + (2 if slow_words and not fast_words else 0)
    return max(0, min(10, score)), "heuristic"


def _genre_score(video: dict, genre: str) -> int:
    if genre not in GENRE_VALUES:
        return 0
    text = _text(video)
    score = sum(2 for word in GENRES[genre] if word in text)
    if genre == "action" and (_bool(video.get("is_action")) or _bool(video.get("is_dynamic"))):
        score += 4
    elif genre == "drama" and _bool(video.get("has_dialogue")):
        score += 4
    elif genre == "romance" and _bool(video.get("is_cinematic")):
        score += 2
    elif genre == "horror_tragedy" and (_bool(video.get("is_cinematic")) or _bool(video.get("is_action"))):
        score += 2
    elif genre == "comedy" and _bool(video.get("has_dialogue")):
        score += 2
    elif genre == "adventure" and (_bool(video.get("is_action")) or _bool(video.get("is_cinematic"))):
        score += 2
    return min(score, 10)


def _character_score(video: dict, character: str) -> int:
    character = _clean(character).lower()
    if not character:
        return 0
    text = _text(video)
    if character in text:
        return 10
    tokens = [token for token in character.split() if len(token) > 2]
    if not tokens:
        return 0
    return min(8, sum(2 for token in tokens if token in text))


def _relevance_score(video: dict, query: str, film: str, genre: str, character: str) -> float:
    return (
        _character_score(video, character) * 2.0
        + (8 if query and _clean(query).lower() in _text(video) else 0)
        + (10 if film and _clean(film).lower() in _text(video) else 0)
        + _genre_score(video, genre) * 1.25
    )


def _stage_score(video: dict, signals: dict[str, int], mood: str, tempo: str, film: str, query: str, genre: str, character: str) -> float:
    base = float(video.get("edit_suitability_score", 0) or 0)
    score = base + _relevance_score(video, query, film, genre, character)
    text = _text(video)
    if "cinematic" in signals:
        score += signals["cinematic"] if _bool(video.get("is_cinematic")) else 0
    if "dynamic" in signals:
        score += signals["dynamic"] if _bool(video.get("is_dynamic")) else 0
    if "action" in signals:
        score += signals["action"] if _bool(video.get("is_action")) else 0
    if "raw" in signals:
        score += signals["raw"] if _bool(video.get("is_raw_footage")) else 0
    if "clean" in signals:
        score += signals["clean"] if _bool(video.get("is_clean")) else 0
    if "dialogue" in signals:
        score += signals["dialogue"] if _bool(video.get("has_dialogue")) else 0
    if mood:
        score += _mood_score(video, mood) * 1.5
    if tempo:
        tempo_score, _ = _tempo_score(video, tempo)
        score += tempo_score * 1.5
    if film:
        film_norm = film.lower()
        if film_norm in text:
            score += 8
    if query:
        query_norm = query.lower()
        if query_norm in text:
            score += 8
    return score


def _why(video: dict, mood: str, tempo: str, film: str, query: str, stage_key: str, genre: str = "", character: str = "") -> str:
    reasons = []
    if genre and character:
        reasons.append(f"выбрано под жанр «{GENRE_LABELS.get(genre, genre)}» и персонажа «{character}»")
    elif genre:
        reasons.append(f"выбрано под жанр «{GENRE_LABELS.get(genre, genre)}»")
    elif character:
        reasons.append(f"совпадает с персонажем «{character}»")
    if video.get("edit_suitability_score", 0) >= 75:
        reasons.append("высокая пригодность для монтажа")
    elif video.get("edit_suitability_score", 0) >= 55:
        reasons.append("хорошая база для нарезки")
    if video.get("is_action") or video.get("is_dynamic"):
        reasons.append("есть динамический/action-сигнал")
    if video.get("is_cinematic"):
        reasons.append("cinematic-сигнал")
    if video.get("is_clean"):
        reasons.append("есть clean-сигнал")
    if video.get("is_4k"):
        reasons.append("4K")
    elif video.get("is_hd"):
        reasons.append("HD")
    if video.get("has_dialogue") and stage_key in ("intro", "build_up"):
        reasons.append("подходит для диалога/нарастания")
    if stage_key == "climax" and (video.get("is_action") or video.get("is_dynamic")):
        reasons.append("подходит для кульминации")
    if stage_key == "outro" and video.get("is_cinematic"):
        reasons.append("даёт кинематографичное завершение")
    if mood:
        mood_fit = _mood_score(video, mood)
        if mood_fit >= 3:
            reasons.append(f"совпадает с настроением «{mood}»")
    if tempo:
        tempo_fit, source = _tempo_score(video, tempo)
        if tempo_fit >= 3:
            reasons.append(f"подходит под темп «{tempo}» ({source})")
    if film and film.lower() in _text(video):
        reasons.append(f"найдено совпадение с «{film}»")
    if genre and not (genre and character):
        genre_fit = _genre_score(video, genre)
        if genre_fit >= 3 and not any("жанр" in reason for reason in reasons):
            reasons.append(f"выбрано под жанр «{GENRE_LABELS.get(genre, genre)}»")
    if character and not (genre and character):
        character_fit = _character_score(video, character)
        if character_fit >= 4 and not any("персонаж" in reason for reason in reasons):
            reasons.append(f"совпадает с персонажем «{character}»")
    return "; ".join(reasons[:5]) or "подобран по доступным метаданным, Edit Suitability и сценарию"


def _row_to_video(row: sqlite3.Row) -> dict:
    video = dict(row)
    for key in (
        "is_short", "is_4k", "is_hd", "is_clean", "is_action", "is_clip",
        "is_cinematic", "is_gameplay", "is_dynamic", "has_music", "has_voice",
        "has_dialogue", "is_raw_footage", "is_no_music",
    ):
        video[key] = bool(video.get(key, 0))
    return video


def _cache_key(query: str) -> str:
    normalized = _normalized_query(query)
    return f"clipfinder_shared:{normalized}" if normalized else ""


def _scenario_query(query: str, film: str, genre: str, character: str) -> str:
    parts = []
    for value in (character, film, query):
        clean_value = _clean(value)
        if clean_value and clean_value.lower() not in " ".join(part.lower() for part in parts):
            parts.append(clean_value)
    if genre in GENRE_SEARCH_TERMS:
        parts.append(GENRE_SEARCH_TERMS[genre])
    if not parts:
        parts.append("cinematic edit material")
    return " ".join(parts)[:120].strip()


def _load_candidates(query: str, film: str, genre: str = "", character: str = "", limit: int = 180) -> list[dict]:
    requested_keys = []
    for raw in (
        _scenario_query(query, film, genre, character),
        query,
        character,
        film,
    ):
        key = _cache_key(raw)
        if key and key not in requested_keys:
            requested_keys.append(key)

    cached = []
    seen_cached = set()
    for key in requested_keys:
        for video in get_cached_videos(key):
            video = _row_to_video(video)
            video_id = _clean(video.get("id"))
            if not video_id or video_id in seen_cached:
                continue
            seen_cached.add(video_id)
            cached.append(video)

    if cached:
        rows = cached[: int(limit)]
    else:
        connection = sqlite3.connect(DATABASE_PATH)
        connection.row_factory = sqlite3.Row
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT * FROM videos
                WHERE datetime(created_at) >= datetime('now', '-24 hours')
                ORDER BY datetime(created_at) DESC
                LIMIT ?
                """,
                (int(limit),),
            )
            rows = [_row_to_video(row) for row in cursor.fetchall()]
        finally:
            connection.close()

    candidates = []
    seen = set()
    for video in rows:
        video_id = _clean(video.get("id"))
        if not video_id or video_id in seen:
            continue
        seen.add(video_id)
        video["edit_score"] = calculate_edit_score(video, query or character or film or video.get("query", ""))
        suitability = calculate_edit_suitability(video, query=query, film=film)
        video["edit_suitability_score"] = suitability["score"]
        video["score_estimated"] = suitability["estimated"]
        video["score_version"] = suitability["version"]
        relevance = _relevance_score(video, query, film, genre, character)
        if any((_clean(query), _clean(film), _clean(character), genre)) and relevance <= 0:
            stored_query = _clean(video.get("query")).lower()
            if stored_query and any(
                token and token in stored_query
                for token in (
                    _clean(query).lower(),
                    _clean(character).lower(),
                    _clean(film).lower(),
                )
            ):
                relevance = 1
            else:
                # A recent DB row is not enough to satisfy Idea Mode. When none of
                # the requested signals match, exclude it so the endpoint can fall
                # through to the real live-search path instead of building a scenario
                # from unrelated material.
                continue
        video["scenario_relevance_score"] = relevance
        candidates.append(video)

    candidates.sort(
        key=lambda item: (
            float(item.get("scenario_relevance_score", 0)),
            not bool(item.get("score_estimated", False)),
            float(item.get("edit_suitability_score", 0)),
        ),
        reverse=True,
    )
    return candidates


def _run_live_search_and_cache(query: str) -> dict:
    quota = _reserve_search_quota()
    if not quota["allowed"]:
        raise HTTPException(
            status_code=429,
            detail=(
                "ClipFinder включил защиту квоты. Новое обращение к YouTube сегодня "
                "временно отключено, чтобы не исчерпать квоту проекта. Сохранённые результаты продолжают работать."
            ),
            headers={"Retry-After": "3600"},
        )

    try:
        videos, youtube_total, next_page_token = search_youtube(
            query,
            limit=SAFE_YOUTUBE_FETCH_LIMIT,
            return_total=True,
            return_next_page_token=True,
        )
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail="Не удалось автоматически найти материалы на YouTube. Повтори попытку позже.",
        ) from error

    videos = remove_duplicates(_soft_edit_pool(videos))
    all_results = []
    for video in videos:
        base_score = calculate_score(
            title=video.get("title", ""),
            query=query,
            views=video.get("views", 0),
        )
        edit_score = calculate_edit_score(video, query)
        video["edit_score"] = edit_score
        video["score"] = base_score + edit_score
        all_results.append(video)

    all_results = sort_videos(all_results, "score", query=query, film="")
    cache_key = _cache_key(query)
    if cache_key:
        save_videos(all_results, cache_key)
        save_search_state(cache_key, next_page_token, youtube_total, 1)

    return {
        "videos": all_results,
        "query": query,
        "cache_key": cache_key,
        "youtube_total": youtube_total,
        "next_page_token": next_page_token,
        "quota_remaining": quota.get("remaining"),
    }


@router.get("/edit-idea")
def edit_idea(
    request: Request,
    query: str = "",
    mood: str = "",
    tempo: str = "",
    film: str = "",
    genre: str = "",
    character: str = "",
    limit_per_stage: int = 3,
):
    if request is not None:
        _check_public_rate_limit(request)
    query = _clean(query)
    mood = _clean(mood).lower()
    tempo = _clean(tempo).lower()
    film = _clean(film)
    genre = _clean(genre).lower()
    character = _clean(character)

    if mood and mood not in MOOD_VALUES:
        return {"ok": False, "error": "Неизвестное настроение.", "allowed_moods": sorted(MOOD_VALUES)}
    if tempo and tempo not in TEMPO_VALUES:
        return {"ok": False, "error": "Неизвестный темп.", "allowed_tempos": sorted(TEMPO_VALUES)}
    if genre and genre not in GENRE_VALUES:
        return {"ok": False, "error": "Неизвестный жанр.", "allowed_genres": sorted(GENRE_VALUES)}

    limit_per_stage = max(2, min(4, int(limit_per_stage or 3)))
    scenario_query = _scenario_query(query, film, genre, character)
    candidates = _load_candidates(query, film, genre, character)
    material_search = {
        "performed": False,
        "source": "cache",
        "query": scenario_query,
        "message": "Использованы релевантные материалы из локального кэша.",
    }

    if not candidates:
        live = _run_live_search_and_cache(scenario_query)
        material_search = {
            "performed": True,
            "source": "youtube",
            "query": scenario_query,
            "loaded": len(live["videos"]),
            "youtube_total": live["youtube_total"],
            "quota_remaining": live["quota_remaining"],
            "message": "Материалы автоматически найдены по параметрам сценария и сохранены в общий кэш поиска.",
        }
        candidates = _load_candidates(query, film, genre, character)

    if not candidates:
        return {
            "ok": True,
            "status": "no_material",
            "query": query,
            "film": film,
            "mood": mood,
            "tempo": tempo,
            "genre": genre,
            "character": character,
            "scenario_query": scenario_query,
            "material_search": material_search,
            "tempo_source": "heuristic" if tempo else "none",
            "message": "Не удалось получить подходящие реальные материалы. Попробуй другой фильм, персонажа или запрос.",
            "stages": [],
        }

    remaining = {video["id"]: video for video in candidates}
    stages = []
    stage_search_focus = {
        "intro": "cinematic · dialogue · close-up",
        "build_up": "dialogue · tension · movement",
        "climax": "action · dynamic · epic",
        "outro": "cinematic · emotional · resolution",
    }
    for stage_key, number, title, description, signals in STAGE_DEFS:
        ranked = sorted(
            remaining.values(),
            key=lambda video: (
                _stage_score(video, signals, mood, tempo, film, query, genre, character),
                not bool(video.get("score_estimated", False)),
                float(video.get("edit_suitability_score", 0)),
            ),
            reverse=True,
        )
        chosen = ranked[:limit_per_stage]
        items = []
        for video in chosen:
            seconds = _duration_seconds(video.get("duration"))
            items.append(
                {
                    "video_id": video.get("id", ""),
                    "title": video.get("title", ""),
                    "source": video.get("channel", ""),
                    "url": video.get("url", ""),
                    "thumbnail": video.get("thumbnail", ""),
                    "duration": video.get("duration", ""),
                    "timecode": f"00:00–{_duration_label(seconds)}" if seconds else "00:00–точный момент не определён",
                    "timecode_exact": False,
                    "edit_score": video.get("edit_score", 0),
                    "edit_suitability_score": video.get("edit_suitability_score", 0),
                    "score_estimated": bool(video.get("score_estimated", False)),
                    "score_version": video.get("score_version", "stage8-v1"),
                    "why": _why(video, mood, tempo, film, query, stage_key, genre, character),
                }
            )
        for video in chosen:
            remaining.pop(video["id"], None)
        if items:
            stages.append(
                {
                    "key": stage_key,
                    "number": number,
                    "title": title,
                    "label": stage_key.upper().replace("_", "-"),
                    "description": description,
                    "search_focus": stage_search_focus.get(stage_key, "cinematic material"),
                    "items": items,
                }
            )

    return {
        "ok": True,
        "status": "ok",
        "query": query,
        "film": film,
        "mood": mood,
        "tempo": tempo,
        "genre": genre,
        "character": character,
        "scenario_query": scenario_query,
        "material_search": material_search,
        "tempo_source": "heuristic" if tempo else "none",
        "timecode_source": "full_video_only",
        "candidate_total": len(candidates),
        "stages": stages,
        "note": "Сценарий строится только на реальных материалах ClipFender. При нехватке релевантного кэша сервис автоматически выполняет один живой поиск по параметрам сценария, сохраняет результаты в общий cache и затем распределяет их по INTRO → BUILD-UP → CLIMAX → OUTRO.",
    }

