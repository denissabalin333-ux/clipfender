from __future__ import annotations

from backend.api.search import (
    _resolve_search_intent,
    apply_filters,
)
from backend.services.youtube import (
    build_edit_search_query,
    normalize_edit_intent,
)


def video(**overrides):
    item = {
        "id": "test",
        "is_short": False,
        "is_hd": True,
        "is_4k": True,
        "is_clean": True,
        "is_action": True,
        "is_cinematic": True,
        "is_raw_footage": True,
        "is_scene_pack": True,
        "is_dialogue": True,
        "is_emotion": True,
        "has_captions": False,
        "slow_motion_fps_signal": 120,
        "duration": "2:00",
        "views": 1000,
        "edit_score": 90,
    }
    item.update(overrides)
    return item


def test_scene_pack_filter():
    rows = [
        video(id="scene", is_scene_pack=True),
        video(id="other", is_scene_pack=False),
    ]

    result = apply_filters(
        rows,
        material_type="scene_pack",
        filter_mode="strict",
    )

    assert [row["id"] for row in result] == ["scene"]


def test_dialogue_filter():
    rows = [
        video(id="dialogue", is_dialogue=True),
        video(id="action", is_dialogue=False),
    ]

    result = apply_filters(
        rows,
        material_type="dialogue",
        filter_mode="strict",
    )

    assert [row["id"] for row in result] == ["dialogue"]


def test_emotion_filter():
    rows = [
        video(id="emotion", is_emotion=True),
        video(id="action", is_emotion=False),
    ]

    result = apply_filters(
        rows,
        material_type="emotion",
        filter_mode="strict",
    )

    assert [row["id"] for row in result] == ["emotion"]


def test_4k_filter():
    rows = [
        video(id="4k", is_4k=True),
        video(id="hd", is_4k=False),
    ]

    result = apply_filters(
        rows,
        quality="4k",
    )

    assert [row["id"] for row in result] == ["4k"]


def test_60fps_signal_filter():
    rows = [
        video(id="120", slow_motion_fps_signal=120),
        video(id="30", slow_motion_fps_signal=30),
        video(id="unknown", slow_motion_fps_signal=0),
    ]

    result = apply_filters(
        rows,
        fps_signal=60,
    )

    assert [row["id"] for row in result] == ["120"]


def test_120fps_signal_filter():
    rows = [
        video(id="120", slow_motion_fps_signal=120),
        video(id="60", slow_motion_fps_signal=60),
    ]

    result = apply_filters(
        rows,
        fps_signal=120,
    )

    assert [row["id"] for row in result] == ["120"]


def test_no_cc_filter():
    rows = [
        video(id="clean", has_captions=False),
        video(id="cc", has_captions=True),
    ]

    result = apply_filters(
        rows,
        caption_mode="none",
    )

    assert [row["id"] for row in result] == ["clean"]


def test_cc_available_filter():
    rows = [
        video(id="cc", has_captions=True),
        video(id="clean", has_captions=False),
    ]

    result = apply_filters(
        rows,
        caption_mode="available",
    )

    assert [row["id"] for row in result] == ["cc"]


def test_edit_search_query_contains_negative_terms():
    query = build_edit_search_query("Jon Snow")

    assert query.startswith("Jon Snow ")
    assert "-reaction" in query
    assert "-review" in query
    assert "-podcast" in query
    assert "-twixtor" in query
    assert "-stream" in query


def test_edit_intent_aliases():
    assert normalize_edit_intent("raw") == "raw_scene"
    assert normalize_edit_intent("raw_footage") == "raw_scene"
    assert normalize_edit_intent("slow") == "slow_motion"
    assert normalize_edit_intent("best") == "best_edit"


def test_action_intent_query_contains_action_variants():
    query = build_edit_search_query(
        "Jon Snow",
        "action",
    )

    assert "Jon Snow" in query
    assert '"fight scene"' in query
    assert '"battle scene"' in query
    assert "combat" in query
    assert "-reaction" in query
    assert '-"fan edit"' in query


def test_slow_motion_intent_query_contains_fps_variants():
    query = build_edit_search_query(
        "Jon Snow",
        "slow_motion",
    )

    assert "slow motion" in query
    assert "60fps" in query
    assert "120fps" in query
    assert "-reaction" in query


def test_raw_scene_intent_query_contains_source_terms():
    query = build_edit_search_query(
        "Jon Snow",
        "raw_scene",
    )

    assert "raw footage" in query
    assert "scenepack" in query
    assert "clean footage" in query


def test_dialogue_intent_query_contains_dialogue_terms():
    query = build_edit_search_query(
        "Jon Snow",
        "dialogue",
    )

    assert "dialogue scene" in query
    assert "conversation" in query
    assert "monologue" in query


def test_scene_pack_intent_query_contains_scene_pack_terms():
    query = build_edit_search_query(
        "Jon Snow",
        "scene_pack",
    )

    assert "Jon Snow" in query
    assert '"scene pack"' in query
    assert "scenepack" in query
    assert "raw scene" in query
    assert "-reaction" in query
    assert '-"fan edit"' in query


def test_unknown_intent_falls_back_to_best_edit():
    unknown = build_edit_search_query(
        "Jon Snow",
        "something_unknown",
    )
    best = build_edit_search_query(
        "Jon Snow",
        "best_edit",
    )

    assert unknown == best


def test_search_intent_resolver_from_material_type():
    assert _resolve_search_intent(None, "action") == "action"
    assert _resolve_search_intent(None, "cinematic") == "cinematic"
    assert _resolve_search_intent(None, "raw_footage") == "raw_scene"
    assert _resolve_search_intent(None, "scene_pack") == "scene_pack"
    assert _resolve_search_intent(None, "emotion") == "emotion"


def test_explicit_search_intent_wins_over_material_type():
    assert _resolve_search_intent(
        "slow_motion",
        "action",
    ) == "slow_motion"


def test_search_intent_defaults_to_best_edit():
    assert _resolve_search_intent(None, None) == "best_edit"
