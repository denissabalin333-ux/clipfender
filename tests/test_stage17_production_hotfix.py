from __future__ import annotations

from pathlib import Path


def test_archive_loads_runtime_svg_fix_css():
    html = Path("frontend/archive.html").read_text(encoding="utf-8")
    assert '/static/css/stage15-release.css?v=1510' in html
    assert '/static/css/stage17-production-hotfix.css?v=1710' in html
    assert 'fill="none"' in html
    assert 'stroke="currentColor"' in html
    assert 'width="18" height="18"' in html


def test_archive_hides_legacy_section_title_for_real_results_shell():
    css = Path("frontend/css/stage17-production-hotfix.css").read_text(encoding="utf-8")
    assert "body.cf4-active .content-shell > .section-title" in css
    assert "display: none !important" in css


def test_login_uses_fresh_auth_assets():
    html = Path("frontend/pages/login.html").read_text(encoding="utf-8")
    assert '/static/css/app.css?v=73.0' in html
    assert '/static/js/site.js?v=7.6' in html


def test_register_handler_persists_email_for_fallback_login():
    js = Path("frontend/js/site.js").read_text(encoding="utf-8")
    assert "clipfender_last_auth_email" in js
    assert "/api/auth/me" in js
    assert "/login?email=" in js
    assert "clipfender_last_auth_email" in js


def test_registration_is_transactional_and_blocks_duplicate_email():
    auth = Path("backend/api/auth.py").read_text(encoding="utf-8")
    security = Path("backend/security.py").read_text(encoding="utf-8")
    db = Path("backend/database/database.py").read_text(encoding="utf-8")
    assert 'connection.execute("BEGIN IMMEDIATE")' in auth
    assert 'create_session(user_id, connection=connection)' in auth
    assert 'duplicate_user_email' in auth
    assert 'CREATE TRIGGER IF NOT EXISTS trg_users_email_unique_insert' in db
    assert 'CREATE TRIGGER IF NOT EXISTS trg_users_email_unique_update' in db
    assert 'def create_session(' in security
    assert 'connection=None' in security


def test_register_creates_authenticated_session_and_rejects_duplicate():
    from fastapi.testclient import TestClient
    from backend.database.database import get_connection, init_database, migrate_database
    from backend.main import app

    init_database()
    migrate_database()
    connection = get_connection()
    try:
        connection.execute("DELETE FROM auth_sessions")
        connection.execute("DELETE FROM users WHERE email = ?", ("stage17-auth@example.com",))
        connection.commit()
    finally:
        connection.close()

    with TestClient(app, base_url="https://clipfender.example") as client:
        csrf_response = client.get("/api/auth/csrf")
        csrf = client.cookies.get("cf_csrf") or csrf_response.cookies.get("cf_csrf")
        payload = {
            "name": "Stage 17 User",
            "email": "stage17-auth@example.com",
            "password": "StrongPass123!",
        }
        first = client.post("/api/auth/register", headers={"X-CSRF-Token": csrf}, json=payload)
        assert first.status_code == 200
        assert first.json().get("authenticated") is True
        assert client.get("/api/auth/me").json()["authenticated"] is True

        csrf = client.cookies.get("cf_csrf") or csrf
        second = client.post("/api/auth/register", headers={"X-CSRF-Token": csrf}, json=payload)
        assert second.status_code == 409
        assert "email" in second.json()["detail"].lower()
