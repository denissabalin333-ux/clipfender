from __future__ import annotations

import os

from fastapi.testclient import TestClient

from backend.character_profiles import CHARACTER_PROFILES
from backend.main import PUBLIC_SITEMAP_PATHS, app
from backend.database.database import get_connection, init_database, migrate_database


def test_character_catalog_is_data_driven_and_includes_barristan():
    assert "barristan-selmy" in CHARACTER_PROFILES
    assert CHARACTER_PROFILES["barristan-selmy"]["image"].endswith("barristan-hq.webp")
    with TestClient(app) as client:
        response = client.get("/characters")
    assert response.status_code == 200
    body = response.text
    for slug, profile in CHARACTER_PROFILES.items():
        assert f"/characters/{slug}" in body
        assert profile["name"] in body
        assert profile["image"] in body
    assert 'id="cf12HouseFilter"' in body
    assert 'id="cf12ProfileFilter"' in body
    assert 'id="cf12CharacterSearch"' in body
    assert 'class="portrait jon"' not in body


def test_character_catalog_skips_missing_portrait(monkeypatch):
    import backend.main as main_module
    original_profiles = main_module.CHARACTER_PROFILES
    monkeypatch.setattr(main_module, "CHARACTER_PROFILES", {
        **original_profiles,
        "missing": {
            "slug": "missing",
            "name": "Missing",
            "house": "TEST",
            "query": "Missing",
            "image": "/static/assets/reference/final/missing-hq.webp",
            "summary": "Missing",
            "lore": ["a", "b"],
            "edit_profile": ["dark", "drama", "action"],
        },
    })
    try:
        catalog = main_module._available_character_catalog()
    finally:
        monkeypatch.setattr(main_module, "CHARACTER_PROFILES", original_profiles)
    assert all(item["slug"] != "missing" for item in catalog)


def test_character_sitemap_contains_all_real_profiles():
    for slug in CHARACTER_PROFILES:
        assert f"/characters/{slug}" in PUBLIC_SITEMAP_PATHS


def test_archive_has_single_visible_filter_rule_and_live_handler():
    from pathlib import Path
    css = Path("frontend/css/final-v7.css").read_text(encoding="utf-8")
    assert css.count("body.cf4-active .filters-wrap") == 1
    archive = Path("frontend/archive.html").read_text(encoding="utf-8")
    assert "/static/js/stage12-archive-filters.js?v=120.0" in archive
    js = Path("frontend/js/stage12-archive-filters.js").read_text(encoding="utf-8")
    assert "addEventListener('change'" in js
    assert "searchVideos();" in js


def test_admin_page_requires_admin_and_returns_for_allowlisted_user(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "admin@example.com")
    init_database()
    migrate_database()
    conn = get_connection()
    try:
        conn.execute("DELETE FROM users WHERE email IN (?, ?)", ("admin@example.com", "stage12-user@example.com"))
        conn.execute("DELETE FROM auth_sessions")
        conn.commit()
    finally:
        conn.close()

    with TestClient(app) as client:
        response = client.get("/admin")
        assert response.status_code == 401

        from argon2 import PasswordHasher
        connection = get_connection()
        try:
            connection.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                ("Admin", "admin@example.com", PasswordHasher().hash("StrongPass123!")),
            )
            connection.commit()
        finally:
            connection.close()

        csrf = client.get("/api/auth/csrf").cookies.get("cf_csrf")
        logged_in = client.post(
            "/api/auth/login",
            headers={"X-CSRF-Token": csrf},
            json={"login": "admin@example.com", "password": "StrongPass123!"},
        )
        assert logged_in.status_code == 200
        assert client.get("/admin").status_code == 200


def test_public_registration_cannot_claim_allowlisted_admin_email(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "locked-admin@example.com")
    init_database()
    migrate_database()
    connection = get_connection()
    try:
        connection.execute("DELETE FROM users WHERE email = ?", ("locked-admin@example.com",))
        connection.commit()
    finally:
        connection.close()

    with TestClient(app) as client:
        csrf = client.get("/api/auth/csrf").cookies.get("cf_csrf")
        response = client.post(
            "/api/auth/register",
            headers={"X-CSRF-Token": csrf},
            json={"name": "Attacker", "email": "locked-admin@example.com", "password": "StrongPass123!"},
        )
    assert response.status_code == 403


def test_contact_csrf_and_library_user_isolation():
    import backend.api.auth as auth_module
    assert auth_module.normalized_email("  USER@Example.COM  ") == "user@example.com"
    with TestClient(app) as client:
        assert client.post("/api/contact", json={"name":"Test","email":"test@example.com","message":"A sufficiently long message."}).status_code == 403
        assert client.get("/api/library/favorites").status_code == 401
