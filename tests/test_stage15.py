from __future__ import annotations

import re
from pathlib import Path

from backend.main import FRONTEND_DIR, app

ROOT = Path(__file__).resolve().parents[1]


def test_stage15_archive_search_icon_has_explicit_svg_geometry_and_stroke_contract():
    html = (ROOT / "frontend/archive.html").read_text(encoding="utf-8")
    css = (ROOT / "frontend/css/stage15-release.css").read_text(encoding="utf-8")

    assert '<svg class="cf4-search-icon" width="18" height="18"' in html
    assert 'viewBox="0 0 24 24"' in html
    assert ".cf4-search-field > svg" in css
    assert "width: 18px !important" in css
    assert "height: 18px !important" in css
    assert "fill: none !important" in css
    assert "stroke: currentColor !important" in css


def test_stage15_archive_app_cache_busted_and_stage15_css_loaded():
    html = (ROOT / "frontend/archive.html").read_text(encoding="utf-8")
    app = (ROOT / "frontend/css/app.css").read_text(encoding="utf-8")

    assert '/static/css/app.css?v=73.0' in html
    assert '@import url("./stage15-release.css");' in app


def test_stage15_character_portrait_runtime_contract_uses_fresh_source_version():
    characters = (ROOT / "frontend/pages/characters.html").read_text(encoding="utf-8")
    detail = (ROOT / "frontend/pages/character.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend/js/stage14-portraits.js").read_text(encoding="utf-8")

    assert '{{ character.image }}?v=1520' in characters
    assert '{{ character.image }}?v=1520' in detail
    assert "const CACHE_VERSION = '1520';" in js
    assert 'loading="eager"' in characters
    assert 'loading="eager"' in detail


def test_stage15_archive_svg_does_not_allow_large_intrinsic_viewport():
    css = (ROOT / "frontend/css/stage15-release.css").read_text(encoding="utf-8")
    html = (ROOT / "frontend/archive.html").read_text(encoding="utf-8")

    assert "body.cf4-active .cf4-search-field" in css
    assert "overflow: hidden !important" in css
    assert re.search(r'<svg class="cf4-search-icon" width="18" height="18"', html)


def test_stage15_character_assets_are_local_and_have_native_resolution():
    expected = {
        "jon-snow": "frontend/assets/reference/final/jon-hq.webp",
        "jaime-lannister": "frontend/assets/reference/final/jaime-hq.webp",
        "daenerys-targaryen": "frontend/assets/reference/final/daenerys-hq.webp",
        "tyrion-lannister": "frontend/assets/reference/final/tyrion-hq.webp",
        "arya-stark": "frontend/assets/reference/final/arya-hq.webp",
        "barristan-selmy": "frontend/assets/reference/final/barristan-hq.webp",
        "cersei-lannister": "frontend/assets/reference/final/cersei-hq.webp",
    }
    from backend.main import _available_character_catalog

    catalog = {item["slug"]: item for item in _available_character_catalog()}
    assert set(catalog) == set(expected)

    for slug, rel in expected.items():
        actual = ROOT / rel
        assert actual.is_file(), (slug, actual)
        assert actual.stat().st_size > 0
