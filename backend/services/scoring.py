# ============================================================
# CLIPFINDER SMART SCORING
# Умная оценка видео для монтажа
# ============================================================


# ============================================================
# GOOD WORDS
# ============================================================

GOOD_WORDS = {

    # --------------------------------------------------------
    # СЦЕНЫ
    # --------------------------------------------------------

    "cinematic": 40,
    "cinematic edit": 45,

    "scene": 20,
    "movie scene": 30,
    "cinematic scene": 35,
    "character scene": 25,

    "cutscene": 30,
    "cut scene": 25,

    "fight scene": 35,
    "battle scene": 35,
    "action scene": 30,


    # --------------------------------------------------------
    # КИНО / ФИЛЬМЫ
    # --------------------------------------------------------

    "movie": 25,
    "film": 25,
    "trailer": 20,
    "teaser": 15,


    # --------------------------------------------------------
    # RAW / FOOTAGE
    # --------------------------------------------------------

    "raw footage": 45,
    "raw": 15,

    "footage": 30,
    "b-roll": 40,

    "background footage": 30,
    "free footage": 30,
    "stock footage": 30,


    # --------------------------------------------------------
    # КАЧЕСТВО
    # --------------------------------------------------------

    "8k": 35,
    "4k": 30,
    "2160p": 30,
    "uhd": 25,
    "hdr": 25,

    "60fps": 15,
    "120fps": 20,


    # --------------------------------------------------------
    # ГРАФИКА
    # --------------------------------------------------------

    "rtx": 30,
    "ray tracing": 30,

    "realistic": 25,

    "shader": 25,
    "shaders": 25,

    "ultra realistic": 30,


    # --------------------------------------------------------
    # ДИНАМИКА
    # --------------------------------------------------------

    "action": 20,
    "battle": 25,
    "fight": 25,
    "combat": 20,

    "chase": 20,
    "explosion": 20,
    "explosions": 20,


    # --------------------------------------------------------
    # ОКРУЖЕНИЕ
    # --------------------------------------------------------

    "landscape": 20,
    "environment": 25,
    "nature": 20,

    "world": 10,
    "forest": 10,
    "mountain": 10,
    "city": 10,


    # --------------------------------------------------------
    # ЧИСТЫЙ МАТЕРИАЛ
    # --------------------------------------------------------

    "no commentary": 35,
    "without commentary": 35,

    "no hud": 30,
    "no ui": 25,

    "clean footage": 35,
    "clean": 15,

}


# ============================================================
# BAD WORDS
# ============================================================

BAD_WORDS = {

    # --------------------------------------------------------
    # РЕАКЦИИ / ОБЗОРЫ
    # --------------------------------------------------------

    "reaction": -70,
    "review": -55,
    "podcast": -80,

    "commentary": -35,


    # --------------------------------------------------------
    # ОБУЧЕНИЕ
    # --------------------------------------------------------

    "tutorial": -60,
    "how to": -55,
    "guide": -45,
    "explained": -45,


    # --------------------------------------------------------
    # СТРИМЫ
    # --------------------------------------------------------

    "stream": -65,
    "livestream": -70,
    "live stream": -70,

    # Слово live отдельно штрафуем меньше,
    # потому что оно может встречаться в других названиях.
    "live": -20,


    # --------------------------------------------------------
    # LET'S PLAY
    # --------------------------------------------------------

    "lets play": -65,
    "let's play": -65,

    "walkthrough": -35,


    # --------------------------------------------------------
    # СЕРИИ
    # --------------------------------------------------------

    "episode": -25,

    "part 1": -15,
    "part 2": -15,
    "part 3": -15,


    # --------------------------------------------------------
    # SHORTS
    # --------------------------------------------------------

    "shorts": -35,
    "#shorts": -40,


    # --------------------------------------------------------
    # ФАНАТСКИЙ КОНТЕНТ
    # --------------------------------------------------------

    "fan edit": -50,
    "amv": -40,

    "compilation": -30,


    # --------------------------------------------------------
    # СОЦСЕТИ
    # --------------------------------------------------------

    "tiktok": -45,
    "instagram": -35,


    # --------------------------------------------------------
    # НОВОСТИ
    # --------------------------------------------------------

    "news": -35,
}


# ============================================================
# HELPER
# ============================================================

def _safe_int(value, default=0):

    try:

        return int(value)

    except (
        TypeError,
        ValueError,
    ):

        return default


# ============================================================
# MAIN SCORE
# ============================================================

def calculate_score(
    title,
    query=None,
    views=0,
):
    """
    Основной score.

    Чем выше score, тем выше видео
    поднимается в выдаче.

    Здесь НЕ происходит жёсткого удаления.
    """

    score = 0


    title = str(
        title or ""
    ).strip().lower()


    query = str(
        query or ""
    ).strip().lower()


    # ========================================================
    # 1. СОВПАДЕНИЕ С ПОИСКОМ
    # ========================================================

    if query:

        query_words = query.split()

        for word in query_words:

            word = word.strip()

            if not word:

                continue


            if word in title:

                score += 12


    # Полное совпадение запроса

    if query and query in title:

        score += 20


    # ========================================================
    # 2. GOOD WORDS
    # ========================================================

    for word, points in GOOD_WORDS.items():

        if word in title:

            score += points


    # ========================================================
    # 3. BAD WORDS
    # ========================================================

    for word, points in BAD_WORDS.items():

        if word in title:

            score += points


    # ========================================================
    # 4. VIEWS
    # ========================================================

    views = _safe_int(
        views
    )


    if views >= 10_000:

        score += 2


    if views >= 100_000:

        score += 5


    if views >= 1_000_000:

        score += 10


    if views >= 10_000_000:

        score += 5


    # ========================================================
    # 5. SCORE НЕ МОЖЕТ БЫТЬ ОТРИЦАТЕЛЬНЫМ
    # ========================================================

    return max(
        0,
        score,
    )

# ============================================================
# EDIT SUITABILITY v2 — STAGE 13
# ============================================================

EDIT_SUITABILITY_VERSION = "stage13-v2"


RELEVANCE_STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "of",
    "to",
    "in",
    "on",
    "for",
    "with",
    "from",
    "из",
    "для",
    "и",
    "или",
    "в",
    "на",
    "с",
    "по",
}


def _clamp_score(value, minimum=0, maximum=100):
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    return max(minimum, min(maximum, number))


def _text_blob(video):
    return " ".join(
        str(video.get(key, "") or "").strip().lower()
        for key in ("title", "description", "channel")
    )


def _title_text(video):
    return str(video.get("title", "") or "").strip().lower()


def _normalise_search_phrase(value):
    return " ".join(str(value or "").strip().lower().split())


def _search_words(value):
    phrase = _normalise_search_phrase(value)
    return [
        word
        for word in phrase.split()
        if len(word) >= 2 and word not in RELEVANCE_STOPWORDS
    ]


def _query_relevance_details(video, query=None, film=None):
    """Return relevance points using title matches first, description second.

    The current ClipFender model has no scene transcript, so this deliberately
    avoids pretending to know semantic scene relevance that is not present in
    the stored YouTube metadata.
    """
    title = _title_text(video)
    description = str(video.get("description", "") or "").strip().lower()

    total = 0.0
    parts = []
    phrases = ((query, 7.0, "query"), (film, 5.0, "film"))

    for value, weight, label in phrases:
        phrase = _normalise_search_phrase(value)
        if not phrase:
            continue

        words = _search_words(phrase)
        if phrase in title:
            total += weight
            parts.append((label, "exact title"))
            continue

        if not words:
            continue

        title_hits = sum(1 for word in words if word in title)
        description_hits = sum(1 for word in words if word in description)

        if title_hits == len(words):
            total += weight * 0.85
            parts.append((label, "all title words"))
        elif title_hits:
            ratio = title_hits / len(words)
            total += min(weight * 0.70, weight * ratio)
            parts.append((label, f"{title_hits}/{len(words)} title words"))
        elif description_hits:
            ratio = min(1.0, description_hits / len(words))
            total += weight * 0.30 * ratio
            parts.append((label, f"{description_hits}/{len(words)} description words"))

    return min(12.0, total), parts


def _duration_seconds(value):
    duration = str(value or "").strip()
    if not duration:
        return 0
    try:
        parts = [int(part) for part in duration.split(":")]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
    except (TypeError, ValueError):
        return 0
    return 0


def _intent_signal_score(video, search_intent=None):
    """Score metadata signals that match the requested edit intent.

    This remains metadata-only. It does not claim to inspect actual frames,
    timestamps, motion vectors or the audio waveform.
    """
    intent = str(search_intent or "").strip().lower()
    text = _text_blob(video)
    title = _title_text(video)

    scores = {
        "best_edit": 0.0,
        "action": 0.0,
        "cinematic": 0.0,
        "raw_scene": 0.0,
        "scene_pack": 0.0,
        "slow_motion": 0.0,
        "dialogue": 0.0,
        "emotion": 0.0,
    }

    # --------------------------------------------------------
    # Shared source-quality signals
    # --------------------------------------------------------

    if video.get("is_scene_pack"):
        scores["best_edit"] += 3
        scores["raw_scene"] += 6
        scores["scene_pack"] += 8

    if video.get("is_raw_footage"):
        scores["best_edit"] += 3
        scores["raw_scene"] += 7

    if video.get("is_clean"):
        scores["raw_scene"] += 3
        scores["cinematic"] += 1
        scores["best_edit"] += 1

    if video.get("is_4k"):
        scores["best_edit"] += 2
        scores["cinematic"] += 1

    if video.get("is_hd"):
        scores["best_edit"] += 1

    # --------------------------------------------------------
    # Action
    # --------------------------------------------------------

    if video.get("is_action"):
        scores["action"] += 7

    if video.get("is_dynamic"):
        scores["action"] += 6

    for phrase, points in (
        ("fight scene", 7),
        ("battle scene", 7),
        ("action scene", 6),
        ("combat", 5),
        ("chase", 4),
        ("war scene", 4),
        ("fight", 3),
        ("battle", 3),
    ):
        if phrase in text:
            scores["action"] += points

    # --------------------------------------------------------
    # Cinematic
    # --------------------------------------------------------

    if video.get("is_cinematic"):
        scores["cinematic"] += 7

    for phrase, points in (
        ("cinematic scene", 7),
        ("movie scene", 6),
        ("film scene", 6),
        ("dramatic scene", 5),
        ("wide shot", 4),
        ("close up", 4),
        ("close-up", 4),
        ("cinematic", 4),
    ):
        if phrase in text:
            scores["cinematic"] += points

    # --------------------------------------------------------
    # Raw source / scene pack
    # --------------------------------------------------------

    if video.get("is_raw_footage"):
        scores["raw_scene"] += 6

    if video.get("is_scene_pack"):
        scores["raw_scene"] += 6

    for phrase, points in (
        ("raw footage", 8),
        ("raw scene", 7),
        ("scene pack", 7),
        ("scenepack", 7),
        ("clean footage", 6),
        ("unedited", 5),
        ("un-edited", 5),
        ("raw clips", 5),
    ):
        if phrase in text:
            scores["raw_scene"] += points

    # --------------------------------------------------------
    # Slow motion
    # --------------------------------------------------------

    fps_signal = _clamp_score(
        video.get("slow_motion_fps_signal", 0),
        0,
        120,
    )

    if fps_signal >= 120:
        scores["slow_motion"] += 14
    elif fps_signal >= 60:
        scores["slow_motion"] += 9

    for phrase, points in (
        ("slow motion", 8),
        ("120fps", 7),
        ("120 fps", 7),
        ("60fps", 5),
        ("60 fps", 5),
        ("high fps", 4),
    ):
        if phrase in text:
            scores["slow_motion"] += points

    # --------------------------------------------------------
    # Dialogue
    # --------------------------------------------------------

    if video.get("is_dialogue"):
        scores["dialogue"] += 8

    if video.get("has_dialogue"):
        scores["dialogue"] += 5

    for phrase, points in (
        ("dialogue scene", 8),
        ("conversation", 6),
        ("monologue", 6),
        ("speech", 5),
        ("talking", 3),
        ("dialogue", 4),
    ):
        if phrase in text:
            scores["dialogue"] += points

    # --------------------------------------------------------
    # Emotion
    # --------------------------------------------------------

    if video.get("is_emotion"):
        scores["emotion"] += 8

    for phrase, points in (
        ("emotional scene", 8),
        ("sad scene", 7),
        ("death scene", 7),
        ("romantic scene", 6),
        ("crying", 6),
        ("tears", 5),
        ("breakdown", 5),
        ("angry scene", 5),
        ("emotional", 4),
        ("sad", 3),
        ("angry", 3),
    ):
        if phrase in text:
            scores["emotion"] += points

    return min(
        20.0,
        max(
            0.0,
            scores.get(intent, 0.0),
        ),
    )


def _intent_signal_label(search_intent):
    return {
        "best_edit": "best edit",
        "action": "action",
        "cinematic": "cinematic",
        "raw_scene": "raw scene",
        "scene_pack": "scene pack",
        "slow_motion": "slow motion",
        "dialogue": "dialogue",
        "emotion": "emotion",
    }.get(
        str(search_intent or "").strip().lower(),
        "best edit",
    )


def _edit_suitability_components(
    video,
    query=None,
    film=None,
    search_intent=None,
):
    """Calculate suitability from stored metadata plus the requested intent."""
    edit_score = _clamp_score(video.get("edit_score", 0))
    edit_component = edit_score * 0.40

    material_raw = 0.0
    material_signals = []
    for key, amount, label in (
        ("is_raw_footage", 12, "raw footage"),
        ("is_dynamic", 10, "dynamic"),
        ("is_action", 10, "action"),
        ("is_clip", 7, "clip"),
        ("is_cinematic", 6, "cinematic"),
        ("is_clean", 5, "clean"),
    ):
        if video.get(key):
            material_raw += amount
            material_signals.append(label)
    material = min(material_raw, 24.0)

    quality_raw = 0.0
    quality_signals = []
    if video.get("is_4k"):
        quality_raw += 10
        quality_signals.append("4K")
    elif video.get("is_hd"):
        quality_raw += 7
        quality_signals.append("HD")
    if video.get("is_clean"):
        quality_raw += 3
        quality_signals.append("clean")
    quality = min(quality_raw, 15.0)

    duration_seconds = _duration_seconds(video.get("duration", ""))
    if 5 <= duration_seconds <= 45:
        duration_bonus = 8.0
        duration_label = "короткий источник"
    elif 46 <= duration_seconds <= 120:
        duration_bonus = 7.0
        duration_label = "удобная длина источника"
    elif 121 <= duration_seconds <= 180:
        duration_bonus = 6.0
        duration_label = "средняя монтажная длина"
    elif 181 <= duration_seconds <= 300:
        duration_bonus = 4.0
        duration_label = "средняя длина источника"
    elif 301 <= duration_seconds <= 600:
        duration_bonus = 2.0
        duration_label = "длинный источник"
    else:
        duration_bonus = 0.0
        duration_label = "нет бонуса за длительность"

    duration_penalty = 2.0 if duration_seconds > 1200 else 0.0
    if duration_penalty:
        duration_label = "очень длинный источник"

    relevance, relevance_parts = _query_relevance_details(
        video,
        query=query,
        film=film,
    )

    intent_signal = _intent_signal_score(
        video,
        search_intent=search_intent,
    )

    audio_raw = 0.0
    audio_signals = []
    if video.get("has_dialogue"):
        audio_raw += 2
        audio_signals.append("dialogue")
    if video.get("has_voice"):
        audio_raw += 1
        audio_signals.append("voice")
    if video.get("is_no_music"):
        audio_raw += 2
        audio_signals.append("no music")
    audio_scene = min(5.0, audio_raw)

    text = _text_blob(video)
    title = _title_text(video)

    positive_text = 0.0
    positive_signals = []
    for phrase, amount, label in (
        ("no commentary", 1.0, "no commentary"),
        ("without commentary", 1.0, "without commentary"),
        ("no subtitles", 1.5, "no subtitles"),
        ("without subtitles", 1.5, "without subtitles"),
        ("no watermark", 1.5, "no watermark"),
        ("without watermark", 1.5, "without watermark"),
    ):
        if phrase in text:
            positive_text += amount
            positive_signals.append(label)
    positive_text = min(4.0, positive_text)

    penalty = 0.0
    penalty_signals = []
    for word, amount, label in (
        ("reaction", 10, "reaction"),
        ("review", 8, "review"),
        ("podcast", 12, "podcast"),
        ("tutorial", 10, "tutorial"),
        ("stream", 10, "stream"),
        ("livestream", 10, "livestream"),
        ("walkthrough", 8, "walkthrough"),
        ("fan edit", 12, "fan edit"),
        ("amv", 10, "AMV"),
        ("compilation", 6, "compilation"),
    ):
        if word in title:
            penalty += amount
            penalty_signals.append(label)

    # Metadata-only cleanliness hints. These are deliberately small because
    # a title can mention subtitles/watermarks without the video itself being
    # unusable, and the current model does not perform visual detection.
    cleanliness_penalties = (
        ("watermark", 6, "watermark keyword"),
        ("watermarked", 6, "watermarked keyword"),
        ("subtitles", 4, "subtitles keyword"),
        ("subtitled", 4, "subtitled keyword"),
        ("subbed", 3, "subbed keyword"),
    )
    if not any(phrase in text for phrase in ("no subtitles", "without subtitles")):
        for word, amount, label in cleanliness_penalties:
            if word in text:
                penalty += amount
                penalty_signals.append(label)

    if duration_penalty:
        penalty += duration_penalty
        penalty_signals.append("very long source")

    score = (
        edit_component
        + material
        + quality
        + duration_bonus
        + relevance
        + audio_scene
        + positive_text
        + intent_signal
        - penalty
    )

    observed = 0
    for key in (
        "is_action",
        "is_dynamic",
        "is_cinematic",
        "is_clip",
        "is_raw_footage",
        "is_clean",
        "is_hd",
        "is_4k",
        "has_dialogue",
        "has_voice",
        "is_no_music",
    ):
        if key in video:
            observed += 1
    if duration_seconds:
        observed += 1
    if str(video.get("description", "") or "").strip():
        observed += 1
    if edit_score > 0:
        observed += 1

    return {
        "score": int(round(_clamp_score(score))),
        "estimated": observed < 3,
        "version": EDIT_SUITABILITY_VERSION,
        "components": {
            "edit_score": {
                "value": round(edit_component, 2),
                "max": 40,
                "source": round(edit_score, 2),
            },
            "material": {
                "value": round(material, 2),
                "max": 24,
                "signals": material_signals,
            },
            "quality": {
                "value": round(quality, 2),
                "max": 15,
                "signals": quality_signals,
            },
            "duration": {
                "value": round(duration_bonus, 2),
                "max": 8,
                "label": duration_label,
            },
            "relevance": {
                "value": round(relevance, 2),
                "max": 12,
                "query": query or "",
                "film": film or "",
                "signals": [f"{label}: {reason}" for label, reason in relevance_parts],
            },
            "intent": {
                "value": round(intent_signal, 2),
                "max": 20,
                "intent": _intent_signal_label(search_intent),
            },
            "audio_scene": {
                "value": round(audio_scene, 2),
                "max": 5,
                "signals": audio_signals,
            },
            "positive_text": {
                "value": round(positive_text, 2),
                "max": 4,
                "signals": positive_signals,
            },
            "penalties": {
                "value": round(-penalty, 2),
                "signals": penalty_signals,
            },
        },
    }


def calculate_edit_suitability(
    video,
    query=None,
    film=None,
    search_intent=None,
):
    """Return the Stage 13 0-100 edit suitability score.

    The ranking uses only information already available in the current
    ClipFender video model. It improves title/description relevance, usable
    clip length and explicit cleanliness/junk signals without inventing
    visual detection, scene timestamps or true measured tempo.
    """
    calculated = _edit_suitability_components(
        video,
        query=query,
        film=film,
        search_intent=search_intent,
    )
    return {
        "score": calculated["score"],
        "estimated": calculated["estimated"],
        "version": calculated["version"],
    }


# ============================================================
# EDIT SUITABILITY EXPLANATION
# ============================================================

def explain_edit_suitability(
    video,
    query=None,
    film=None,
    search_intent=None,
):
    """Return suitability plus a human-readable contribution breakdown."""
    calculated = _edit_suitability_components(
        video,
        query=query,
        film=film,
        search_intent=search_intent,
    )
    return {
        "score": calculated["score"],
        "estimated": calculated["estimated"],
        "version": calculated["version"],
        "components": calculated["components"],
        "note": (
            "Сценовый тайминг, реальный tempo, субтитры и вотермарк не "
            "оцениваются визуально: используются только доступные поля YouTube "
            "и сохранённые текстовые сигналы, например явные слова в названии "
            "или описании."
        ),
    }

