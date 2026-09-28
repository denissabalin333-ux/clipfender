import pytest

from backend.api import video as video_module


VIDEO_ID = "dQw4w9WgXcQ"


def test_video_endpoint_returns_existing_video(monkeypatch):
    monkeypatch.setattr(
        video_module,
        "get_video_details",
        lambda ids: {VIDEO_ID: {"id": VIDEO_ID, "title": "Test clip", "url": "https://www.youtube.com/watch?v=" + VIDEO_ID}},
    )

    payload = video_module.get_video(VIDEO_ID)

    assert payload["source"] == "youtube"
    assert payload["video"]["id"] == VIDEO_ID


def test_video_endpoint_rejects_invalid_id():
    with pytest.raises(Exception) as exc_info:
        video_module.get_video("not-an-id")
    assert getattr(exc_info.value, "status_code", None) == 422
