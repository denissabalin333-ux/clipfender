from __future__ import annotations

import io
from pathlib import Path

from PIL import Image
from fastapi.testclient import TestClient

from backend.character_profiles import CHARACTER_PROFILES
from backend.database.database import get_connection
from backend.main import app
from backend.services import character_catalog


def make_portrait_bytes(width: int = 1100, height: int = 1400) -> bytes:
    image = Image.new("RGB", (width, height), (34, 39, 45))
    # Deterministic high-frequency details so the quality heuristic passes.
    pixels = image.load()
    for y in range(0, height, 7):
        for x in range(0, width, 7):
            pixels[x, y] = ((x * 13) % 255, (y * 17) % 255, ((x + y) * 19) % 255)
    buffer = io.BytesIO()
    image.save(buffer, format="WEBP", quality=96)
    return buffer.getvalue()


def test_character_catalog_tables_exist():
    connection = get_connection()
    try:
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    finally:
        connection.close()
    assert "character_catalog" in tables
    assert "character_generation_guard" in tables


def test_static_character_does_not_trigger_external_generation():
    result = character_catalog.ensure_character("Джон Сноу")
    assert result["status"] == "ready"
    assert result["created"] is False
    assert result["character"]["slug"] == "jon-snow"
    assert "jon-snow" in CHARACTER_PROFILES


def test_new_character_can_be_discovered_with_mocked_ai(monkeypatch, tmp_path):
    monkeypatch.setattr(character_catalog, "GENERATED_DIR", tmp_path / "generated")
    monkeypatch.setattr(character_catalog, "_search_bing", lambda name: [])
    monkeypatch.setattr(character_catalog, "_reserve_generation_quota", lambda: True)
    monkeypatch.setattr(character_catalog, "IMAGE_GENERATION_ENABLED", True)
    monkeypatch.setattr(character_catalog, "OPENAI_API_KEY", "test-key")
    portrait = make_portrait_bytes()
    monkeypatch.setattr(character_catalog, "_generate_openai", lambda name: (portrait, {"width": 1100, "height": 1400, "edge_score": 30.0}))

    result = character_catalog.ensure_character("Санса Старк")

    assert result["status"] == "ready"
    assert result["created"] is True
    assert result["source"] == "ai_generation"
    assert result["character"]["slug"] == "sansa-stark"
    assert result["character"]["image"] == "/static/assets/reference/generated/sansa-stark-hq.webp"
    assert (tmp_path / "generated" / "sansa-stark-hq.webp").is_file()

    stored = character_catalog.get_dynamic_character("sansa-stark")
    assert stored is not None
    assert stored["name"] == "Санса Старк"
    assert "drama" in stored["edit_profile"]


def test_cross_site_discovery_is_rejected(monkeypatch):
    called = {"value": False}

    def fake_ensure(name):
        called["value"] = True
        return {"status": "ready", "created": True, "character": {"slug": "x"}}

    monkeypatch.setattr("backend.api.characters.ensure_character", fake_ensure)
    with TestClient(app) as client:
        response = client.post(
            "/api/characters/ensure",
            json={"name": "Новый Герой"},
            headers={"Sec-Fetch-Site": "cross-site"},
        )
    assert response.status_code == 403
    assert called["value"] is False


def test_characters_page_uses_dynamic_catalog_pipeline():
    page = Path("frontend/pages/characters.html").read_text(encoding="utf-8")
    assert "character.image" in page
    assert "stage16-character-autodiscovery.js" in page


def test_search_page_wires_character_discovery():
    page = Path("frontend/pages/search.html").read_text(encoding="utf-8")
    script = Path("frontend/js/stage16-character-autodiscovery.js").read_text(encoding="utf-8")
    assert "stage16-character-autodiscovery.js" in page
    assert "/api/characters/ensure" in script


def test_env_example_documents_external_providers_without_secrets():
    env = Path(".env.example").read_text(encoding="utf-8")
    assert "BING_IMAGE_SEARCH_API_KEY=" in env
    assert "OPENAI_API_KEY=" in env
    assert "CHARACTER_GENERATION_DAILY_GUARD=" in env
    assert "AKIA" not in env
