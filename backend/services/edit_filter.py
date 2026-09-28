# ============================================================
# CLIPFINDER EDIT FILTER
# МЯГКИЙ ФИЛЬТР МАТЕРИАЛОВ ДЛЯ МОНТАЖА
# ============================================================

# ------------------------------------------------------------
# Только ЯВНЫЙ мусор.
#
# Не добавляем сюда:
# cinematic
# 4k
# gameplay
# survival
# scene
# movie
# trailer
#
# Потому что такие видео тоже могут быть полезны монтажёру.
# ------------------------------------------------------------

BLOCKED_WORDS = [

    # реакции / обзоры
    "reaction",
    "review",
    "podcast",

    # обучение
    "tutorial",
    "guide",
    "how to",
    "explained",

    # стримы
    "stream",
    "livestream",

    # Let's Play
    "lets play",
    "let's play",
    "walkthrough",

    # чужие монтажи
    "fan edit",
    "amv",

    # сборники
    "compilation",

    # соцсети
    "tiktok",
    "instagram",

]


def is_edit_material(video):
    """
    Мягкий фильтр.

    False = явный мусор
    True  = оставляем для дальнейшего scoring

    Видео не обязано содержать:
    cinematic / 4k / footage и т.д.
    """

    title = str(
        video.get(
            "title",
            "",
        ) or ""
    ).lower()

    # The title is the reliable signal for excluding obvious non-editing
    # content. Descriptions often contain boilerplate links, channel info,
    # or unrelated words such as "review"/"guide", so they must not
    # silently remove an otherwise useful editing source.
    text = title

    # --------------------------------------------------------
    # Убираем только явный мусор
    # --------------------------------------------------------

    for word in BLOCKED_WORDS:

        if word in text:

            return False

    # --------------------------------------------------------
    # Всё остальное оставляем
    # --------------------------------------------------------

    return True