import re

import os

from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError



# ============================================================
# ENV
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]


ENV_PATH = BASE_DIR / ".env"


if ENV_PATH.exists():

    load_dotenv(
        ENV_PATH
    )

else:

    load_dotenv()





# ============================================================
# SETTINGS
# ============================================================

YOUTUBE_API_SERVICE_NAME = "youtube"

YOUTUBE_API_VERSION = "v3"


# Лимиты поиска

YOUTUBE_FETCH_LIMIT = 500

DEFAULT_LIMIT = 100

MAX_LIMIT = 500


# ============================================================
# EDIT SEARCH SIGNALS
# ============================================================

EDIT_QUERY_NEGATIVE_TERMS = (
    "-reaction "
    "-review "
    "-podcast "
    "-commentary "
    "-tutorial "
    "-amv "
    "-twixtor "
    "-stream "
    '-"fan edit" '
    '-"full episode" '
    '-"complete episode"'
)


EDIT_SEARCH_INTENTS = {
    "best_edit": (
        "scene",
        '"scene pack"',
        '"raw scene"',
        '"cinematic scene"',
        '"movie scene"',
        "clip",
    ),
    "action": (
        '"fight scene"',
        '"battle scene"',
        "combat",
        '"action scene"',
        "chase",
    ),
    "cinematic": (
        '"cinematic scene"',
        '"movie scene"',
        '"film scene"',
        '"dramatic scene"',
        '"wide shot"',
        '"close up"',
    ),
    "raw_scene": (
        '"raw scene"',
        '"raw footage"',
        "scenepack",
        '"scene pack"',
        '"clean footage"',
        "unedited",
    ),
    "scene_pack": (
        '"scene pack"',
        "scenepack",
        '"raw scene"',
        '"raw footage"',
        '"clean footage"',
    ),
    "slow_motion": (
        '"slow motion"',
        "60fps",
        "120fps",
        '"60 fps"',
        '"120 fps"',
        '"high fps"',
    ),
    "dialogue": (
        '"dialogue scene"',
        "conversation",
        "monologue",
        "speech",
        "talking",
    ),
    "emotion": (
        '"emotional scene"',
        '"sad scene"',
        "crying",
        "tears",
        "angry",
        "breakdown",
        '"death scene"',
        '"romantic scene"',
    ),
}


INTENT_ALIASES = {
    "best": "best_edit",
    "best_edit": "best_edit",
    "action": "action",
    "cinematic": "cinematic",
    "raw": "raw_scene",
    "raw_scene": "raw_scene",
    "raw_footage": "raw_scene",
    "scene_pack": "scene_pack",
    "slow": "slow_motion",
    "slow_motion": "slow_motion",
    "dialogue": "dialogue",
    "emotion": "emotion",
}


def normalize_edit_intent(intent: str | None) -> str:
    """Normalize a public edit intent to one supported retrieval profile."""
    value = " ".join(
        str(intent or "").strip().lower().split()
    )

    if not value:
        return "best_edit"

    return INTENT_ALIASES.get(
        value,
        "best_edit",
    )


def build_edit_search_query(
    query: str,
    intent: str | None = None,
) -> str:
    """Build an edit-oriented YouTube retrieval query.

    The user's character/topic query remains present in every alternative.
    Intent terms create several semantically related retrieval branches while
    the negative terms suppress common non-source material such as reactions,
    reviews, podcasts and fan edits.

    The Google client receives the pipe character as a Boolean OR expression.
    """
    clean = " ".join(
        str(query or "").strip().split()
    )

    if not clean:
        return ""

    normalized_intent = normalize_edit_intent(intent)
    variants = EDIT_SEARCH_INTENTS[normalized_intent]

    branches = [
        f"{clean} {variant}"
        for variant in variants
    ]

    joined = " | ".join(branches)

    return f"{joined} {EDIT_QUERY_NEGATIVE_TERMS}".strip()


def _classify_edit_signals(title: str, description: str) -> dict:
    """Classify practical edit-oriented signals from public metadata only."""
    text = " ".join(
        str(value or "").lower()
        for value in (title, description)
    )

    scene_pack_terms = (
        "scene pack",
        "scenepack",
        "scene collection",
        "clip pack",
        "raw clips",
        "raw scenes",
    )

    dialogue_terms = (
        "dialogue",
        "dialog",
        "conversation",
        "speech",
        "monologue",
    )

    emotion_terms = (
        "emotional",
        "emotion",
        "sad scene",
        "crying",
        "tears",
        "angry scene",
        "breakdown",
        "death scene",
        "romantic scene",
    )

    cinematic_terms = (
        "cinematic",
        "cinematic scene",
        "movie scene",
        "film scene",
    )

    action_terms = (
        "action",
        "fight",
        "battle",
        "combat",
        "chase",
        "war scene",
    )

    raw_terms = (
        "raw footage",
        "raw scenes",
        "raw clips",
        "clean footage",
        "un-edited",
        "unedited",
    )

    fps_signal = 0

    for match in re.finditer(
        r"(?<!\d)(120|100|90|60|59\.94|50)\s*(?:fps|frame\s*per\s*second)",
        text,
        flags=re.IGNORECASE,
    ):
        try:
            value = float(match.group(1))
            if value >= 59:
                normalized = 60 if value < 90 else int(value)
                fps_signal = max(fps_signal, normalized)
        except (TypeError, ValueError):
            pass

    compact = text.replace(" ", "")
    if "120fps" in compact:
        fps_signal = max(fps_signal, 120)
    if "60fps" in compact or "59.94fps" in compact:
        fps_signal = max(fps_signal, 60)

    return {
        "is_scene_pack": any(term in text for term in scene_pack_terms),
        "is_dialogue": any(term in text for term in dialogue_terms),
        "is_emotion": any(term in text for term in emotion_terms),
        "is_cinematic": any(term in text for term in cinematic_terms),
        "is_action": any(term in text for term in action_terms),
        "is_raw_footage": any(term in text for term in raw_terms),
        "slow_motion_fps_signal": fps_signal,
        "is_slow_motion_ready": fps_signal >= 60,
    }





# ============================================================
# API KEY
# ============================================================

def get_api_key() -> str:


    key = os.getenv(
        "YOUTUBE_API_KEY"
    )


    if not key:

        raise RuntimeError(
            "Не найден YOUTUBE_API_KEY.\n"
            "Создай файл .env:\n\n"
            "YOUTUBE_API_KEY=твой_ключ"
        )



    key = str(
        key
    ).strip()



    if (

        key.startswith('"')

        and

        key.endswith('"')

    ):

        key = key[1:-1]



    if (

        key.startswith("'")

        and

        key.endswith("'")

    ):

        key = key[1:-1]



    return key





# ============================================================
# YOUTUBE CLIENT
# ============================================================

def get_youtube_client():


    return build(

        YOUTUBE_API_SERVICE_NAME,

        YOUTUBE_API_VERSION,

        developerKey=get_api_key(),

        cache_discovery=False,

    )





# ============================================================
# HELPERS
# ============================================================

def _safe_int(
    value: Any,
    default: int = 0,
) -> int:


    try:

        return int(value)


    except (

        TypeError,

        ValueError,

    ):

        return default





def _extract_video_id(
    item: dict,
) -> str:


    video_id = item.get(
        "id",
        {}
    )


    if isinstance(
        video_id,
        dict
    ):


        return str(

            video_id.get(
                "videoId",
                ""
            )

            or ""

        )


    return ""





# ============================================================
# SCORE
# ============================================================

def calculate_score(
    title: str,
    is_4k=False,
    is_hd=False,
    is_clean=False,
    is_action=False,
    query="",
    views=0,
) -> int:


    title = str(
        title or ""
    ).lower()


    query = str(
        query or ""
    ).lower()



    score = 0



    # качество

    if is_4k or "4k" in title:
        score += 30


    if is_hd or "hd" in title:
        score += 15


    if is_clean or "clean" in title:
        score += 20



    # монтажные слова

    edit_words = [

        "cinematic",

        "cinema",

        "movie",

        "scene",

        "clip",

        "trailer",

        "gameplay",

        "fight",

        "battle",

        "action",

        "footage",

        "raw",

    ]


    for word in edit_words:

        if word in title:

            score += 10



    # плохие видео

    bad_words = [

        "reaction",

        "review",

        "podcast",

        "commentary",

        "tutorial",

        "amv",

    ]


    for word in bad_words:

        if word in title:

            score -= 30



    # просмотры

    try:

        views = int(views)

        if views > 100000:
            score += 5

        if views > 1000000:
            score += 10

    except:

        pass



    return score



    title = str(
        title or ""
    ).lower()



    score = 0



    if is_4k or "4k" in title:

        score += 30



    if is_hd or "hd" in title:

        score += 15



    if is_clean or "clean" in title:

        score += 20



    if is_action or "action" in title:

        score += 20




    bad_words = [

        "reaction",

        "review",

        "podcast",

        "commentary",

        "tutorial",

        "amv",

    ]



    for word in bad_words:


        if word in title:

            score -= 30



    return score
# ============================================================
# VIDEO DETAILS
# ============================================================

def _get_video_details(
    youtube,
    video_ids: list[str],
) -> dict[str, dict]:


    if not video_ids:

        return {}



    result = {}



    for start in range(
        0,
        len(video_ids),
        50,
    ):


        chunk = video_ids[
            start:start + 50
        ]



        try:


            response = (

                youtube.videos()

                .list(

                    part=(

                        "statistics,"

                        "contentDetails,"

                        "status"

                    ),

                    id=",".join(chunk),

                )

                .execute()

            )



        except HttpError:


            continue




        for item in response.get(
            "items",
            []
        ):


            video_id = str(

                item.get(
                    "id",
                    ""
                )

                or ""

            )


            if not video_id:

                continue



            result[video_id] = {


                "statistics":

                    item.get(
                        "statistics",
                        {}
                    ),



                "contentDetails":

                    item.get(
                        "contentDetails",
                        {}
                    ),

                "status":

                    item.get(
                        "status",
                        {}
                    ),


            }



    return result





# ============================================================
# DURATION FORMAT
# ============================================================

def _format_duration(
    iso_duration: str,
) -> str:


    if not iso_duration:

        return ""



    value = iso_duration.replace(
        "PT",
        "",
    )



    hours = 0

    minutes = 0

    seconds = 0


    number = ""



    for char in value:


        if char.isdigit():

            number += char



        elif char == "H":

            hours = _safe_int(
                number
            )

            number = ""



        elif char == "M":

            minutes = _safe_int(
                number
            )

            number = ""



        elif char == "S":

            seconds = _safe_int(
                number
            )

            number = ""




    if hours > 0:


        return (

            f"{hours}:"

            f"{minutes:02d}:"

            f"{seconds:02d}"

        )



    return (

        f"{minutes}:"

        f"{seconds:02d}"

    )





# ============================================================
# DURATION TO SECONDS
# ============================================================

def _duration_to_seconds(
    iso_duration: str,
) -> int:



    if not iso_duration:

        return 0



    value = iso_duration.replace(
        "PT",
        "",
    )



    hours = 0

    minutes = 0

    seconds = 0


    number = ""



    for char in value:


        if char.isdigit():

            number += char



        elif char == "H":

            hours = _safe_int(
                number
            )

            number = ""



        elif char == "M":

            minutes = _safe_int(
                number
            )

            number = ""



        elif char == "S":

            seconds = _safe_int(
                number
            )

            number = ""




    return (

        hours * 3600

        +

        minutes * 60

        +

        seconds

    )





# ============================================================
# PARSE VIDEO
# ============================================================



def _classify_audio(title: str, description: str) -> dict:
    """
    Metadata-only audio classification.

    IMPORTANT: YouTube Data API does not expose the actual audio waveform.
    Therefore unknown is preserved instead of being treated as "no".
    """
    text = f"{title or ''} {description or ''}".lower()

    def detect(positive, negative):
        for phrase in negative:
            if phrase in text:
                return False, "high"
        for phrase in positive:
            if phrase in text:
                return True, "high" if phrase in positive[:3] else "medium"
        return False, "unknown"

    music_positive = [
        "with music", "music", "soundtrack", "instrumental", "song", "ost", "background music", "music video"
    ]
    music_negative = [
        "no music", "without music", "music removed", "clean audio"
    ]
    voice_positive = [
        "voiceover", "voice over", "narration", "narrator", "commentary", "talking", "spoken", "voice acting", "voice"
    ]
    voice_negative = [
        "no voice", "without voice", "no commentary", "without commentary", "mute voice"
    ]
    dialogue_positive = [
        "dialogue", "dialog", "conversation", "monologue", "interview", "speech"
    ]
    dialogue_negative = [
        "no dialogue", "without dialogue", "no dialog", "without dialog"
    ]

    has_music, music_confidence = detect(music_positive, music_negative)
    has_voice, voice_confidence = detect(voice_positive, voice_negative)
    has_dialogue, dialogue_confidence = detect(dialogue_positive, dialogue_negative)

    return {
        "has_music": has_music,
        "music_confidence": music_confidence,
        "has_voice": has_voice,
        "voice_confidence": voice_confidence,
        "has_dialogue": has_dialogue,
        "dialogue_confidence": dialogue_confidence,
        "music_source": "metadata",
        "voice_source": "metadata",
        "dialogue_source": "metadata",
        "is_no_music": (not has_music and music_confidence == "high" and any(p in text for p in music_negative)),
    }


def _parse_video(
    item: dict,
    statistics: dict | None = None,
) -> dict:



    snippet = (

        item.get(
            "snippet",
            {}
        )

        or {}

    )



    statistics = statistics or {}



    video_id = _extract_video_id(
        item
    )



    title = str(

        snippet.get(
            "title",
            ""
        )

        or ""

    )



    channel = str(

        snippet.get(
            "channelTitle",
            ""
        )

        or ""

    )



    thumbnails = (

        snippet.get(
            "thumbnails",
            {}
        )

        or {}

    )



    thumbnail = ""



    for quality in [

        "maxres",

        "standard",

        "high",

        "medium",

        "default",

    ]:


        if quality in thumbnails:


            thumbnail = str(

                thumbnails[quality].get(
                    "url",
                    ""
                )

                or ""

            )

            break




    title_lower = title.lower()



    is_4k = (

        "4k" in title_lower

        or "2160" in title_lower

    )



    is_hd = (

        is_4k

        or "1080" in title_lower

        or "720" in title_lower

        or "hd" in title_lower

    )



    is_clean = (

        "clean" in title_lower

        or "no watermark" in title_lower

        or "without watermark" in title_lower

    )



    is_action = (

        "action" in title_lower

        or "fight" in title_lower

        or "battle" in title_lower

        or "combat" in title_lower

        or "gameplay" in title_lower

    )
    # ================================================
    # AUDIO / EDIT TYPE DETECTION
    # ================================================

    description = str(
        snippet.get(
            "description",
            "",
        )
        or ""
    )

    audio = _classify_audio(
        title,
        description,
    )

    has_music = audio["has_music"]
    has_voice = audio["has_voice"]
    has_dialogue = audio["has_dialogue"]
    is_no_music = audio["is_no_music"]

    is_raw_footage = (
        "raw footage" in title_lower
        or "raw" in title_lower
        or "footage" in title_lower
        or "clean footage" in title_lower
    )


    return {


        "id": video_id,


        "title": title,

        "description": description,


        "channel": channel,


        "thumbnail": thumbnail,


        "url":

            f"https://www.youtube.com/watch?v={video_id}",


        "views":

            _safe_int(

                statistics.get(
                    "viewCount",
                    0
                )

            ),


        "published_at":

            snippet.get(
                "publishedAt",
                ""
            ),


        "duration": "",


        "is_short": False,


        "is_4k": bool(is_4k),


        "is_hd": bool(is_hd),


        "is_clean": bool(is_clean),


        "is_action": bool(is_action),

        "has_music": bool(has_music),

        "has_voice": bool(has_voice),

        "has_dialogue": bool(has_dialogue),

        "music_confidence": audio["music_confidence"],
        "voice_confidence": audio["voice_confidence"],
        "dialogue_confidence": audio["dialogue_confidence"],
        "music_source": audio["music_source"],
        "voice_source": audio["voice_source"],
        "dialogue_source": audio["dialogue_source"],

        "is_raw_footage": bool(is_raw_footage),

        "is_no_music": bool(is_no_music),


        "score":

            calculate_score(

                title,

                is_4k,

                is_hd,

                is_clean,

                is_action,

            ),


    }
# ============================================================
# SEARCH YOUTUBE
# ============================================================

def search_youtube(
    query: str,
    limit: int = DEFAULT_LIMIT,
    return_total: bool = False,
    page_token: str | None = None,
    return_next_page_token: bool = False,
    search_intent: str | None = None,
):


    youtube = get_youtube_client()



    query = str(
        query or ""
    ).strip()



    if not query:


        if return_total:

            return [], 0


        return []




    try:

        limit = int(limit)


    except (

        TypeError,

        ValueError,

    ):

        limit = DEFAULT_LIMIT




    limit = max(

        1,

        min(

            limit,

            MAX_LIMIT

        )

    )





    videos = []

    current_page_token = page_token
    next_page_token = None

    total_results = 0






    while len(videos) < limit:



        remaining = limit - len(videos)




        params = {


            "part":

                "snippet",



            "q":

                build_edit_search_query(
                    query,
                    search_intent,
                ),



            "type":

                "video",



            "maxResults":

                min(
                    remaining,
                    50
                ),


        }





        if current_page_token:


            params["pageToken"] = current_page_token






        try:


            response = (

                youtube.search()

                .list(

                    **params

                )

                .execute()

            )



        except HttpError as error:


            raise RuntimeError(

                f"YouTube API error: {error}"

            )






        page_info = (

            response.get(

                "pageInfo",

                {}

            )

            or {}

        )



        total_results = _safe_int(

            page_info.get(

                "totalResults",

                0

            )

        )






        items = (

            response.get(

                "items",

                []

            )

            or []

        )





        if not items:

            break






        video_ids = []




        for item in items:


            video_id = _extract_video_id(
                item
            )


            if video_id:

                video_ids.append(
                    video_id
                )






        details = _get_video_details(

            youtube,

            video_ids

        )







        for item in items:



            video_id = _extract_video_id(
                item
            )



            if not video_id:

                continue






            detail = details.get(

                video_id,

                {}

            )





            video = _parse_video(

                item,

                detail.get(

                    "statistics",

                    {}

                )

            )






            content = (

                detail.get(

                    "contentDetails",

                    {}

                )

                or {}

            )






            duration_iso = str(

                content.get(

                    "duration",

                    ""

                )

                or ""

            )





            video["duration"] = _format_duration(

                duration_iso

            )






            seconds = _duration_to_seconds(

                duration_iso

            )





            caption_value = str(
                content.get(
                    "caption",
                    "false",
                )
                or "false"
            ).lower()

            status = (
                detail.get(
                    "status",
                    {}
                )
                or {}
            )

            video["has_captions"] = caption_value == "true"
            video["is_embeddable"] = bool(
                status.get("embeddable", False)
            )

            video.update(
                _classify_edit_signals(
                    video.get("title", ""),
                    video.get("description", ""),
                )
            )

            if (

                seconds > 0

                and seconds <= 60

            ):

                video["is_short"] = True






            # ================================================
            # МАТЕРИАЛЫ ДЛЯ МОНТАЖА
            # ================================================


            title = video["title"].lower()



            video["is_clip"] = (

                "clip" in title

                or "scene" in title

                or "moment" in title

            )




            video["is_cinematic"] = (

                "cinematic" in title

                or "movie" in title

                or "film" in title

            )




            video["is_gameplay"] = (

                "gameplay" in title

                or "walkthrough" in title

            )




            video["is_dynamic"] = (

                "battle" in title

                or "fight" in title

                or "action" in title

            )






            videos.append(
                video
            )






            if len(videos) >= limit:

                break

        next_page_token = response.get(
            "nextPageToken"
        )

        if len(videos) >= limit:
            break

        if not next_page_token:
            break

        current_page_token = next_page_token






    # ========================================================
    # SORT
    # ========================================================

    videos.sort(

        key=lambda video: (

            float(

                video.get(

                    "score",

                    0

                )

                or 0

            ),



            int(

                video.get(

                    "views",

                    0

                )

                or 0

            ),

        ),

        reverse=True,

    )






    if return_total and return_next_page_token:
        return (
            videos,
            total_results,
            next_page_token,
        )

    if return_total:
        return (
            videos,
            total_results
        )

    return videos
# ============================================================
# EDIT MATERIAL FILTER
# ============================================================


def filter_edit_materials(
    videos: list[dict],
) -> list[dict]:

    """
    Оставляет только материалы,
    которые подходят для монтажа.
    """

    result = []



    bad_words = [

        "tutorial",

        "guide",

        "how to",

        "review",

        "reaction",

        "podcast",

        "stream",

        "livestream",

        "news",

        "commentary",

        

    ]





    for video in videos:


        title = str(

            video.get(

                "title",

                ""

            )

        ).lower()





        # --------------------------------------------
        # Убираем плохие видео
        # --------------------------------------------


        bad = False



        for word in bad_words:


            if word in title:

                bad = True

                break




        if bad:

            continue






        # --------------------------------------------
        # Считаем пригодность для монтажа
        # --------------------------------------------


        edit_score = 0
        # ==========================================
        # AUDIO SCORE
        # ==========================================


        if video.get("is_raw_footage"):

            edit_score += 25



        if video.get("is_no_music"):

            edit_score += 20



        if video.get("has_dialogue"):

            edit_score += 15



        if video.get("has_music"):

            edit_score += 10





        if video.get(
            "is_action"
        ):

            edit_score += 20




        if video.get(
            "is_dynamic"
        ):

            edit_score += 20




        if video.get(
            "is_clip"
        ):

            edit_score += 20




        if video.get(
            "is_cinematic"
        ):

            edit_score += 25




        if video.get(
            "is_hd"
        ):

            edit_score += 10




        if video.get(
            "is_4k"
        ):

            edit_score += 15






        duration = video.get(

            "duration",

            ""

        )





        if duration:


            parts = duration.split(":")



            try:


                if len(parts) == 2:


                    seconds = (

                        int(parts[0]) * 60

                        +

                        int(parts[1])

                    )


                elif len(parts) == 3:


                    seconds = (

                        int(parts[0]) * 3600

                        +

                        int(parts[1]) * 60

                        +

                        int(parts[2])

                    )


                else:

                    seconds = 0






                # хорошие куски для клипов

                if 5 <= seconds <= 180:


                    edit_score += 15



            except:


                pass







        video["edit_score"] = edit_score





        # минимальный порог

        if edit_score < 10:

            continue





        result.append(
            video
        )





    return result







# ============================================================
# NORMALIZE VIDEO
# ============================================================


def normalize_video(
    video: dict,
) -> dict:


    defaults = {


        "id": "",


        "title": "",


        "channel": "",


        "thumbnail": "",


        "url": "",


        "views": 0,


        "published_at": "",


        "duration": "",



        "is_short": False,


        "is_4k": False,


        "is_hd": False,


        "is_clean": False,


        "is_action": False,


        "is_clip": False,


        "is_scene": False,


        "is_cinematic": False,


        "is_gameplay": False,


        "is_dynamic": False,

        "has_music": False,

        "has_voice": False,

        "has_dialogue": False,

        "is_raw_footage": False,

        "is_no_music": False,


        "edit_score": 0,


        "score": 0,

    }




    for key, value in defaults.items():


        if key not in video:


            video[key] = value





    return video








# ============================================================
# PREPARE RESULTS
# ============================================================


def prepare_results(
    videos: list[dict],
) -> list[dict]:


    result = []



    for video in videos:


        result.append(

            normalize_video(
                video
            )

        )



    return result







# ============================================================
# SEARCH FOR EDITS
# ============================================================


def search_for_edits(
    query: str,
    limit: int = DEFAULT_LIMIT,
):


    """
    Главный поиск ClipFinder.
    """



    videos = search_youtube(

        query=query,

        limit=limit

    )





    videos = filter_edit_materials(

        videos

    )





    videos = prepare_results(

        videos

    )






    videos.sort(

        key=lambda video: (


            video.get(

                "edit_score",

                0

            ),



            video.get(

                "score",

                0

            ),



            video.get(

                "views",

                0

            ),


        ),

        reverse=True

    )





    return videos







# ============================================================
# SAFE SEARCH
# ============================================================


def safe_search_youtube(
    query: str,
    limit: int = DEFAULT_LIMIT,
):


    try:


        return search_for_edits(

            query,

            limit

        )



    except Exception as error:


        print(

            "YOUTUBE ERROR:",

            error

        )


        return []


# ============================================================
# PUBLIC VIDEO DETAILS
# ============================================================

def get_video_details(
    video_ids: list[str],
) -> dict[str, dict]:
    """
    Получение деталей видео
    для API video.py
    """

    youtube = get_youtube_client()

    return _get_video_details(
        youtube,
        video_ids,
    )




# ============================================================
# TEST
# ============================================================


if __name__ == "__main__":



    results = safe_search_youtube(

        "minecraft cinematic",

        10

    )




    print(

        "FOUND:",

        len(results)

    )




    for video in results:


        print(

            video["title"],

            "|",

            "EDIT SCORE:",

            video["edit_score"]

        )
