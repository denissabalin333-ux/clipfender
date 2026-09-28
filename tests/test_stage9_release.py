from __future__ import annotations

import json
from pathlib import Path
import re

from fastapi.testclient import TestClient

from backend.main import app


ROOT = Path(__file__).resolve().parents[1]


def test_legacy_character_search_is_permanent_redirect():
    with TestClient(app) as client:
        response = client.get("/character-search", follow_redirects=False)
    assert response.status_code == 301
    assert response.headers["location"] == "/search"


def test_sitemap_and_robots_exclude_private_and_retired_pages():
    with TestClient(app) as client:
        sitemap = client.get("/sitemap.xml")
        robots = client.get("/robots.txt")
    assert sitemap.status_code == 200
    assert "/character-search" not in sitemap.text
    assert "/search" in sitemap.text
    assert "Disallow: /api/" in robots.text
    assert "Disallow: /admin" in robots.text
    assert "Disallow: /login" in robots.text
    assert "Disallow: /library" in robots.text


def test_favicon_and_manifest_assets_are_real():
    with TestClient(app) as client:
        favicon = client.get("/favicon.svg")
        favicon_ico = client.get("/favicon.ico")
        favicon_png = client.get("/favicon-32x32.png")
        apple = client.get("/apple-touch-icon.png")
        icon192 = client.get("/icon-192.png")
        icon512 = client.get("/icon-512.png")
        manifest = client.get("/manifest.webmanifest")
    assert favicon.status_code == 200 and favicon.headers["content-type"].startswith("image/svg+xml")
    assert favicon_ico.status_code == 200 and favicon_ico.content[:4] == b"\x00\x00\x01\x00"
    assert favicon_png.status_code == 200 and favicon_png.content[:8] == b"\x89PNG\r\n\x1a\n"
    assert apple.status_code == 200
    assert icon192.status_code == 200
    assert icon512.status_code == 200
    data = manifest.json()
    assert {entry["sizes"] for entry in data["icons"]} >= {"any", "192x192", "512x512"}


def test_default_character_and_video_og_images():
    with TestClient(app) as client:
        home = client.get("/")
        character = client.get("/characters/jon-snow")
        video = client.get("/video?id=dQw4w9WgXcQ")
    assert '/static/assets/meta/clipfender-og-1200x630.jpg' in home.text
    assert '/static/assets/reference/final/jon-hq.webp' in character.text
    assert 'https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg' in video.text


def test_search_is_in_hero_and_archive_links_target_current_flow():
    search = (ROOT / "frontend/pages/search.html").read_text(encoding="utf-8")
    assert search.index('id="cf8SearchForm"') < search.index('id="cf8Results"')

    for relative in [
        "frontend/components/header.html",
        "frontend/pages/edit-ideas.html",
        "frontend/pages/help.html",
        "frontend/pages/project.html",
        "frontend/js/final-v6.js",
    ]:
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "/character-search" not in text, relative

    assert not (ROOT / "frontend/pages/character-search.html").exists()
    assert (ROOT / "_archive/frontend/pages/character-search.html").exists()


def test_decorative_images_are_explicitly_hidden_from_assistive_tech():
    for path in (ROOT / "frontend").rglob("*.html"):
        if "_archive" in path.parts or "_backup" in path.parts:
            continue
        html = path.read_text(encoding="utf-8")
        for img in re.findall(r"<img\b[^>]*>", html, flags=re.I | re.S):
            if 'alt=' not in img.lower():
                raise AssertionError(f"missing alt in {path}: {img}")
            if 'alt=""' in img or "alt=''" in img:
                assert "aria-hidden=\"true\"" in img or "aria-hidden='true'" in img, (
                    f"decorative img without aria-hidden in {path}: {img}"
                )


def test_stage9_visual_values_are_not_the_old_dark_wash():
    final_v7 = (ROOT / "frontend/css/final-v7.css").read_text(encoding="utf-8")
    assert "brightness(.78)" not in final_v7
    assert "rgba(0,0,0,.82)" not in final_v7.split(".home-stage3__scene::after", 1)[1].split("}", 1)[0]
    assert "rgba(5,7,8,.95)" not in final_v7.split(".home-stage3__veil", 1)[1].split("}", 1)[0]
    assert ".home-stage3__fog{opacity:.10" in final_v7
    assert ".cf-search-page__fog{background:" in final_v7 and "opacity:.12!important" in final_v7
