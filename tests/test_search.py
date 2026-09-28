from fastapi import Request

from backend.api import search as search_module


def _request(path="/api/search", host="10.0.0.10"):
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "headers": [],
            "query_string": b"",
            "client": (host, 12345),
            "server": ("testserver", 8000),
            "scheme": "http",
        }
    )


def test_search_cached_response_contract(monkeypatch):
    video = {
        "id": "dQw4w9WgXcQ",
        "title": "Jon Snow battle scene 4k",
        "description": "raw footage",
        "views": 1000,
        "is_4k": 1,
        "is_hd": 1,
        "is_action": 1,
        "is_cinematic": 1,
        "is_clip": 1,
        "is_raw_footage": 1,
        "is_clean": 1,
        "is_short": 0,
        "has_music": 0,
        "has_voice": 0,
        "has_dialogue": 1,
    }

    monkeypatch.setattr(search_module, "get_cached_videos", lambda key: [dict(video)])
    monkeypatch.setattr(search_module, "get_search_state", lambda key: {
        "youtube_total": 1,
        "next_page_token": "",
        "pages_loaded": 1,
    })

    payload = search_module.search(
        _request(),
        query="Jon Snow",
        limit=20,
        page=1,
    )

    assert payload["query"] == "Jon Snow"
    assert payload["source"] == "cache"
    assert isinstance(payload["results"], list)
    assert "pagination" in payload
    assert payload["pagination"]["returned"] == len(payload["results"])
    assert "has_more_youtube" in payload


def test_search_validates_long_query():
    try:
        search_module.search(_request(host="10.0.0.11"), query="x" * 121)
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 422
    else:
        raise AssertionError("Expected HTTPException for oversized query")
