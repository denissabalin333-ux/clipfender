from __future__ import annotations

import sqlite3

from fastapi import Request
from backend.api import edit_idea as idea_module
from backend.api import search as search_module
from backend.database.database import get_connection, init_database, migrate_database
from backend.services.scoring import calculate_edit_suitability


def _sample_video(video_id, title, *, edit_score=80, views=1000, action=False, dynamic=False, cinematic=False, clean=True, hd=True, duration="00:45", description=""):
    return {
        "id": video_id,
        "title": title,
        "description": description,
        "channel": "Test Channel",
        "thumbnail": "https://example.com/test.jpg",
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "views": views,
        "published_at": "2026-09-22T00:00:00Z",
        "duration": duration,
        "is_short": False,
        "is_4k": False,
        "is_hd": hd,
        "is_clean": clean,
        "is_action": action,
        "is_clip": True,
        "is_cinematic": cinematic,
        "is_gameplay": False,
        "is_dynamic": dynamic,
        "has_music": False,
        "has_voice": False,
        "has_dialogue": False,
        "is_raw_footage": True,
        "is_no_music": True,
        "edit_score": edit_score,
        "score": edit_score,
        "query": "Jon Snow",
    }


def test_edit_suitability_is_primary_over_views():
    good_material = _sample_video(
        "GOODGOOD001",
        "Jon Snow 4K raw footage battle cinematic",
        edit_score=82,
        views=1200,
        action=True,
        dynamic=True,
        cinematic=True,
    )
    viral_bad_material = _sample_video(
        "BADBAD0001",
        "Jon Snow reaction review podcast",
        edit_score=90,
        views=50_000_000,
        action=False,
        dynamic=False,
        cinematic=False,
        clean=False,
        hd=True,
        duration="25:00",
    )
    ranked = search_module.sort_videos(
        [viral_bad_material, good_material],
        "views",
        query="Jon Snow",
    )
    assert ranked[0]["id"] == "GOODGOOD001"
    assert ranked[0]["edit_suitability_score"] > ranked[1]["edit_suitability_score"]
    assert ranked[1]["score_estimated"] is False


def test_estimated_scores_are_below_calculated_scores():
    calculated = _sample_video("CALC000001", "Battle footage", edit_score=70, action=True, dynamic=True)
    estimated = {
        "id": "EST0000001",
        "title": "Old cached material",
        "description": "",
        "duration": "",
        "edit_score": 0,
    }
    ordered = search_module.sort_videos([estimated, calculated], "newest", query="Battle")
    assert ordered[0]["id"] == "CALC000001"
    assert ordered[1]["score_estimated"] is True


def test_film_filter_is_hard_and_optional():
    videos = [
        _sample_video("GOT00000001", "Jon Snow battle", description="Game of Thrones scene"),
        _sample_video("WIT00000001", "Jon Snow battle", description="Another series scene"),
    ]
    all_rows = search_module.apply_filters(videos, film=None)
    got_rows = search_module.apply_filters(videos, film="Game of Thrones")
    assert len(all_rows) == 2
    assert [row["id"] for row in got_rows] == ["GOT00000001"]


def test_edit_idea_uses_only_db_materials(monkeypatch):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM videos")
    videos = [
        _sample_video("IDEA000001", "Jon Snow battle 4K cinematic", edit_score=85, action=True, dynamic=True, cinematic=True, description="Game of Thrones"),
        _sample_video("IDEA000002", "Jon Snow emotional dialogue", edit_score=78, cinematic=True, description="Game of Thrones drama"),
        _sample_video("IDEA000003", "Jon Snow dark night", edit_score=74, cinematic=True, description="Game of Thrones dark scene"),
        _sample_video("IDEA000004", "Jon Snow reaction review", edit_score=95, views=10_000_000, description="Game of Thrones reaction"),
    ]
    for video in videos:
        cursor.execute(
            """
            INSERT INTO videos (
                id,title,channel,thumbnail,url,views,published_at,duration,description,
                is_short,is_4k,is_hd,is_clean,is_action,is_clip,is_cinematic,is_gameplay,is_dynamic,
                has_music,has_voice,has_dialogue,is_raw_footage,is_no_music,score,edit_score,query
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                video["id"], video["title"], video["channel"], video["thumbnail"], video["url"], video["views"],
                video["published_at"], video["duration"], video["description"],
                int(video["is_short"]), int(video["is_4k"]), int(video["is_hd"]), int(video["is_clean"]),
                int(video["is_action"]), int(video["is_clip"]), int(video["is_cinematic"]), int(video["is_gameplay"]), int(video["is_dynamic"]),
                int(video["has_music"]), int(video["has_voice"]), int(video["has_dialogue"]), int(video["is_raw_footage"]), int(video["is_no_music"]),
                video["score"], video["edit_score"], video["query"],
            ),
        )
    connection.commit()
    connection.close()

    payload = idea_module.edit_idea(
        request=None,
        query="Jon Snow",
        mood="action",
        tempo="fast",
        film="Game of Thrones",
        limit_per_stage=2,
    )
    try:
        assert payload["ok"] is True
        assert payload["status"] == "ok"
        assert payload["stages"]
        ids = [item["video_id"] for stage in payload["stages"] for item in stage["items"]]
        assert set(ids).issubset({video["id"] for video in videos})
        first_items = [stage["items"][0] for stage in payload["stages"] if stage["items"]]
        assert first_items[0]["video_id"] == "IDEA000001"
        assert all(item["edit_suitability_score"] >= 0 for item in first_items)
    finally:
        connection = get_connection()
        connection.execute("DELETE FROM videos WHERE id LIKE 'IDEA%'")
        connection.commit()
        connection.close()


def test_edit_suitability_function_exposes_version_and_estimation():
    result = calculate_edit_suitability(_sample_video("SCORE00001", "battle 4k raw footage", edit_score=80, action=True, dynamic=True), query="battle")
    assert 0 <= result["score"] <= 100
    assert result["version"] == "stage13-v2"
    assert isinstance(result["estimated"], bool)


def test_stage8_public_search_route_and_idea_endpoint(monkeypatch):
    from fastapi.testclient import TestClient
    from backend.main import app

    live_calls = []
    monkeypatch.setattr(idea_module, "_run_live_search_and_cache", lambda query: live_calls.append(query) or {
        "videos": [], "query": query, "cache_key": "clipfinder_shared:" + query.lower(),
        "youtube_total": 0, "next_page_token": None, "quota_remaining": 68,
    })

    with TestClient(app) as client:
        page = client.get("/search")
        assert page.status_code == 200
        assert "ИДЕЯ ДЛЯ ЭДИТА" in page.text

        idea = client.get("/api/edit-idea", params={"query": "Jon Snow"})
        assert idea.status_code == 200
        payload = idea.json()
        assert payload["ok"] is True
        assert payload["status"] == "no_material"
        assert live_calls and live_calls[0] == "Jon Snow"

        sitemap = client.get("/sitemap.xml")
        assert sitemap.status_code == 200
        assert "/search" in sitemap.text


def _stage8_request(host="10.0.0.88"):
    return Request({
        "type": "http",
        "method": "GET",
        "path": "/api/search",
        "headers": [],
        "query_string": b"",
        "client": (host, 12345),
        "server": ("testserver", 8000),
        "scheme": "http",
    })


def test_api_search_film_parameter_preserves_old_contract(monkeypatch):
    film_video = _sample_video(
        "FILM000001",
        "Jon Snow battle",
        edit_score=84,
        description="Game of Thrones scene",
        action=True,
        dynamic=True,
    )
    other_video = _sample_video(
        "FILM000002",
        "Jon Snow battle",
        edit_score=82,
        description="Another series scene",
        action=True,
        dynamic=True,
    )
    monkeypatch.setattr(search_module, "get_cached_videos", lambda key: [dict(film_video), dict(other_video)])
    monkeypatch.setattr(search_module, "get_search_state", lambda key: {"youtube_total": 2, "next_page_token": "", "pages_loaded": 1})
    payload = search_module.search(
        _stage8_request(host="10.0.0.88"),
        query="Jon Snow",
        film="Game of Thrones",
        limit=20,
        page=1,
    )
    assert payload["query"] == "Jon Snow"
    assert payload["film"] == "Game of Thrones"
    assert [row["id"] for row in payload["results"]] == ["FILM000001"]
    assert payload["pagination"]["returned"] == 1
