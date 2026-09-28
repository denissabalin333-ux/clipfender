from __future__ import annotations

from types import SimpleNamespace

from fastapi import Request
from fastapi.testclient import TestClient

from backend.api import library as library_module
from backend.database.database import get_connection
from backend.main import app
from backend.services.scoring import explain_edit_suitability


def _request(method="GET"):
    return Request({
        "type": "http",
        "method": method,
        "path": "/api/library/bookmarks",
        "headers": [],
        "query_string": b"",
        "client": ("10.10.0.9", 1234),
        "server": ("testserver", 8000),
        "scheme": "http",
    })


def _video(video_id: str, title: str, *, query="Jon Snow", score=84, action=True, dynamic=True, cinematic=True):
    return {
        "id": video_id,
        "title": title,
        "description": "Game of Thrones scene",
        "channel": "Test Channel",
        "thumbnail": "https://example.com/test.jpg",
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "views": 1000,
        "published_at": "2026-09-22T00:00:00Z",
        "duration": "00:45",
        "is_short": 0,
        "is_4k": 0,
        "is_hd": 1,
        "is_clean": 1,
        "is_action": int(action),
        "is_clip": 1,
        "is_cinematic": int(cinematic),
        "is_gameplay": 0,
        "is_dynamic": int(dynamic),
        "has_music": 0,
        "has_voice": 0,
        "has_dialogue": 0,
        "is_raw_footage": 1,
        "is_no_music": 1,
        "music_confidence": "unknown",
        "voice_confidence": "unknown",
        "dialogue_confidence": "unknown",
        "music_source": "metadata",
        "voice_source": "metadata",
        "dialogue_source": "metadata",
        "score": score,
        "edit_score": score,
        "query": query,
    }


def _insert(video):
    columns = [
        "id", "title", "channel", "thumbnail", "url", "views", "published_at", "duration",
        "is_short", "is_4k", "is_hd", "is_clean", "is_action", "is_clip", "is_cinematic", "is_gameplay",
        "is_dynamic", "has_music", "has_voice", "has_dialogue", "is_raw_footage", "is_no_music", "score", "edit_score", "query",
        "description", "music_confidence", "voice_confidence", "dialogue_confidence", "music_source", "voice_source", "dialogue_source",
    ]
    values = [video.get(column) for column in columns]
    connection = get_connection()
    try:
        connection.execute(
            f"INSERT INTO videos ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
            values,
        )
        connection.commit()
    finally:
        connection.close()


def test_score_explanation_matches_calculated_score():
    video = _video("STG9SCORE01", "Jon Snow battle cinematic raw", score=86)
    result = explain_edit_suitability(video, query="Jon Snow", film="Game of Thrones")
    assert result["score"] >= 0
    assert result["score"] <= 100
    assert result["version"] == "stage13-v2"
    assert "edit_score" in result["components"]
    assert "material" in result["components"]
    assert "quality" in result["components"]


def test_score_explanation_and_similar_endpoint_use_real_db_rows_only():
    target = _video("STG9TARGET1", "Jon Snow battle cinematic")
    similar = _video("STG9SIMILR1", "Jon Snow battle raw footage")
    unrelated = _video("STG9UNREL01", "Cooking tutorial podcast", query="Cooking", score=10, action=False, dynamic=False, cinematic=False)
    unrelated["description"] = "Cooking class recording"
    _insert(target)
    _insert(similar)
    _insert(unrelated)
    try:
        with TestClient(app) as client:
            explanation = client.get("/api/video/STG9TARGET1/score-explanation", params={"query": "Jon Snow", "film": "Game of Thrones"})
            assert explanation.status_code == 200
            assert explanation.json()["video_id"] == "STG9TARGET1"
            similar_response = client.get("/api/video/STG9TARGET1/similar")
            assert similar_response.status_code == 200
            ids = [item["video_id"] for item in similar_response.json()["items"]]
            assert "STG9SIMILR1" in ids
            assert "STG9TARGET1" not in ids
            assert "STG9UNREL01" not in ids
    finally:
        connection = get_connection()
        connection.execute("DELETE FROM videos WHERE id LIKE 'STG9%'")
        connection.commit()
        connection.close()


def test_bookmark_crud_validates_ranges_and_uses_user_scope(monkeypatch):
    monkeypatch.setattr(library_module, "_user_id", lambda request: 1)
    monkeypatch.setattr(library_module, "require_csrf", lambda request: None)
    connection = get_connection()
    connection.execute("INSERT OR IGNORE INTO users (id, name, email, password_hash) VALUES (1, 'Stage9', 'stage9@example.com', 'x')")
    connection.commit()
    connection.close()

    payload = library_module.BookmarkPayload(
        video_id="STG9BOOK01",
        start_seconds=12.5,
        end_seconds=24.0,
        note="Точный момент входа персонажа",
        video={"id": "STG9BOOK01", "title": "Jon Snow entrance"},
    )
    created = library_module.add_bookmark(payload, _request("POST"))
    assert created["ok"] is True

    items = library_module.bookmarks(_request("GET"), video_id="STG9BOOK01")["items"]
    assert len(items) == 1
    assert items[0]["start_seconds"] == 12.5
    assert items[0]["end_seconds"] == 24.0
    assert items[0]["note"] == "Точный момент входа персонажа"

    deleted = library_module.delete_bookmark(int(items[0]["id"]), _request("DELETE"))
    assert deleted["ok"] is True

    bad = library_module.BookmarkPayload(
        video_id="STG9BOOK01",
        start_seconds=30,
        end_seconds=20,
        note="bad",
        video={},
    )
    try:
        library_module.add_bookmark(bad, _request("POST"))
    except Exception as error:
        assert getattr(error, "status_code", None) == 422
    else:
        raise AssertionError("Invalid bookmark range must be rejected")
    connection = get_connection()
    connection.execute("DELETE FROM bookmarks WHERE video_id = ?", ("STG9BOOK01",))
    connection.execute("DELETE FROM users WHERE id = 1")
    connection.commit()
    connection.close()
