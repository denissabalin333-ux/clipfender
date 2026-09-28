from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.database.database import get_connection, init_database, migrate_database


@pytest.fixture()
def client():
    init_database()
    migrate_database()
    os.environ["ADMIN_EMAILS"] = "admin@example.com"
    connection = get_connection()
    try:
        connection.execute("DELETE FROM rate_limits WHERE rate_key LIKE 'auth:register:%'")
        connection.execute("DELETE FROM rate_limits WHERE rate_key LIKE 'report:%'")
        connection.execute("DELETE FROM users WHERE email IN (?, ?)", ("admin@example.com", "user@example.com"))
        connection.commit()
    finally:
        connection.close()
    with TestClient(app) as test_client:
        yield test_client
    connection = get_connection()
    try:
        connection.execute("DELETE FROM rate_limits WHERE rate_key LIKE 'auth:register:%'")
        connection.execute("DELETE FROM rate_limits WHERE rate_key LIKE 'report:%'")
        connection.execute("DELETE FROM users WHERE email IN (?, ?)", ("admin@example.com", "user@example.com"))
        connection.commit()
    finally:
        connection.close()


def csrf(client):
    response = client.get("/api/auth/csrf")
    assert response.status_code == 200
    return client.cookies.get("cf_csrf")


def register(client, email="user@example.com"):
    token = csrf(client)
    response = client.post("/api/auth/register", headers={"X-CSRF-Token": token}, json={"name":"Test User","email":email,"password":"StrongPass123!"})
    assert response.status_code == 200
    return client.cookies.get("cf_csrf") or token


def provision_user(connection, email="admin@example.com", name="Admin"):
    from argon2 import PasswordHasher
    from backend.security import create_session, set_session_cookie, set_csrf_cookie
    hasher = PasswordHasher()
    cursor = connection.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, hasher.hash("StrongPass123!")),
    )
    connection.commit()
    return int(cursor.lastrowid)


def test_admin_summary_requires_allowlist_and_login(client):
    response = client.get("/api/admin/summary")
    assert response.status_code == 401
    connection = get_connection()
    try:
        provision_user(connection)
    finally:
        connection.close()
    # Build a session through normal login so the test still exercises the real cookie/session path.
    token = csrf(client)
    response = client.post("/api/auth/login", headers={"X-CSRF-Token": token}, json={"login":"admin@example.com","password":"StrongPass123!"})
    assert response.status_code == 200
    token = client.cookies.get("cf_csrf") or token
    response = client.get("/api/admin/summary")
    assert response.status_code == 200
    assert "quota" in response.json()
    # account cleanup for test isolation
    client.request("DELETE", "/api/auth/me", headers={"X-CSRF-Token": token}, json={"password":"StrongPass123!"})


def test_report_create_and_admin_resolve(client):
    token = register(client, email="user@example.com")
    connection = get_connection()
    try:
        provision_user(connection)
    finally:
        connection.close()
    # Switch the client to the allowlisted admin for the admin operations.
    admin_csrf = csrf(client)
    login = client.post("/api/auth/login", headers={"X-CSRF-Token": admin_csrf}, json={"login":"admin@example.com","password":"StrongPass123!"})
    assert login.status_code == 200
    token = client.cookies.get("cf_csrf") or admin_csrf
    response = client.post("/api/reports", headers={"X-CSRF-Token": token}, json={"video_id":"abcdefghijk","reason":"broken","details":"Тест"})
    assert response.status_code == 200
    report_id = response.json()["id"]
    response = client.get("/api/admin/reports")
    assert response.status_code == 200
    assert response.json()["items"][0]["id"] == report_id
    response = client.patch(f"/api/admin/reports/{report_id}", headers={"X-CSRF-Token": token}, json={"status":"resolved"})
    assert response.status_code == 200
    assert response.json()["status"] == "resolved"
    response = client.get("/api/admin/reports?status=resolved")
    assert response.status_code == 200
    assert response.json()["items"][0]["status"] == "resolved"
    client.request("DELETE", "/api/auth/me", headers={"X-CSRF-Token": token}, json={"password":"StrongPass123!"})


def test_non_admin_user_cannot_access_admin(client):
    token = register(client, email="user@example.com")
    response = client.get("/api/admin/summary")
    assert response.status_code == 403
    client.request("DELETE", "/api/auth/me", headers={"X-CSRF-Token": token}, json={"password":"StrongPass123!"})


def test_localization_assets_and_admin_page(client):
    unauthorized = client.get("/admin")
    assert unauthorized.status_code == 401

    connection = get_connection()
    try:
        provision_user(connection)
    finally:
        connection.close()
    token = csrf(client)
    response = client.post(
        "/api/auth/login",
        headers={"X-CSRF-Token": token},
        json={"login": "admin@example.com", "password": "StrongPass123!"},
    )
    assert response.status_code == 200
    token = client.cookies.get("cf_csrf") or token

    response = client.get("/admin")
    assert response.status_code == 200
    assert "/static/js/stage11-i18n.js" in response.text
    assert "/static/js/stage11-admin.js" in response.text
    assert "noindex" in response.text.lower()
    response = client.get("/static/js/stage11-i18n.js")
    assert response.status_code == 200
    assert "Switch language" in response.text
    client.request("DELETE", "/api/auth/me", headers={"X-CSRF-Token": token}, json={"password": "StrongPass123!"})
