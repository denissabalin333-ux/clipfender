from __future__ import annotations

from pathlib import Path

from backend.api.search import sort_videos
from backend.services.scoring import calculate_edit_suitability, explain_edit_suitability


def _video(video_id: str, title: str, *, edit_score: int, duration: str, description: str = "", **flags):
    base = {
        "id": video_id,
        "title": title,
        "description": description,
        "channel": "Test Channel",
        "views": 100,
        "duration": duration,
        "edit_score": edit_score,
        "is_raw_footage": False,
        "is_dynamic": False,
        "is_action": False,
        "is_clip": True,
        "is_cinematic": False,
        "is_clean": False,
        "is_hd": False,
        "is_4k": False,
        "has_dialogue": False,
        "has_voice": False,
        "is_no_music": False,
    }
    base.update(flags)
    return base


def test_stage13_default_ranking_promotes_clean_edit_material():
    usable = _video(
        "CLEAN001",
        "Jon Snow battle scene raw footage",
        edit_score=65,
        duration="00:34",
        description="Game of Thrones clean footage",
        is_raw_footage=True,
        is_dynamic=True,
        is_action=True,
        is_cinematic=True,
        is_clean=True,
        is_hd=True,
        is_4k=True,
        is_no_music=True,
    )
    dirty = _video(
        "DIRTY001",
        "Jon Snow 4K cinematic subtitles watermark",
        edit_score=100,
        duration="00:34",
        description="Game of Thrones",
        is_cinematic=True,
        is_hd=True,
        is_4k=True,
    )

    ranked = sort_videos([dirty, usable], "score", query="Jon Snow", film="Game of Thrones")

    # Before Stage 13 the same deterministic metadata ranked DIRTY001 first
    # (88 vs 84). Stage 13 uses the existing metadata-only cleanliness signals
    # and promotes the genuinely cleaner edit source to first place (82 vs 70).
    assert ranked[0]["id"] == "CLEAN001"
    assert ranked[0]["edit_suitability_score"] > ranked[1]["edit_suitability_score"]
    assert ranked[0]["score_version"] == "stage13-v2"


def test_stage13_clean_metadata_signals_are_bounded_and_explained():
    clean = _video(
        "CLEAN0001",
        "Jon Snow scene — no subtitles no watermark",
        edit_score=70,
        duration="00:35",
        description="clean footage",
        is_clean=True,
    )
    result = calculate_edit_suitability(clean, query="Jon Snow")
    explanation = explain_edit_suitability(clean, query="Jon Snow")

    assert 0 <= result["score"] <= 100
    assert result["version"] == "stage13-v2"
    assert explanation["version"] == "stage13-v2"
    assert explanation["components"]["positive_text"]["value"] > 0
    assert explanation["components"]["penalties"]["value"] <= 0


def test_stage13_guides_uses_wide_full_width_idea_section():
    css = Path("frontend/css/stage13-release.css").read_text(encoding="utf-8")
    assert ".cf-guides-v7 .cf-guide-idea {\n  grid-column: 1 / -1;" in css
    assert ".cf-guides-v7 .cf-guide-idea-grid {\n  display: grid;" in css
    assert "grid-template-columns: repeat(4, minmax(0, 1fr));" in css
    assert "@media (max-width: 760px)" in css


def test_stage13_archive_crest_is_always_bounded():
    css = Path("frontend/css/stage13-release.css").read_text(encoding="utf-8")
    assert ".cf4-results-head .cf4-signet" in css
    assert "width: 68px !important;" in css
    assert "height: 76px !important;" in css
    assert "max-width: 46px !important;" in css
    assert "max-height: 58px !important;" in css


def test_stage13_default_edit_ranking_contract_is_score():
    import inspect
    from backend.api import search as search_module
    from pathlib import Path

    assert inspect.signature(search_module.search).parameters["sort"].default == "score"
    archive = Path("frontend/archive.html").read_text(encoding="utf-8")
    assert '<option value="score">⚔ Лучшие материалы для эдита</option>' in archive
    assert '"sort"' in archive and '"score"' in archive
    idea = Path("frontend/js/stage8-idea.js").read_text(encoding="utf-8")
    assert "api.searchParams.set('sort', 'score')" in idea
    edit_idea = Path("backend/api/edit_idea.py").read_text(encoding="utf-8")
    assert 'sort_videos(all_results, "score"' in edit_idea
