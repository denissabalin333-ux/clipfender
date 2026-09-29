"""Security helpers for authentication, CSRF and SQLite-backed rate limits."""

from __future__ import annotations

import hashlib
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, Request

from backend.database.database import get_connection

SESSION_COOKIE = "cf_session"
CSRF_COOKIE = "cf_csrf"
SESSION_MAX_AGE = 60 * 60 * 24 * 30
SESSION_SHORT_MAX_AGE = 60 * 60 * 8
CSRF_MAX_AGE = 60 * 60 * 12


def admin_emails() -> set[str]:
    raw = os.getenv("ADMIN_EMAILS", "")
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def is_admin_user(user: Optional[dict]) -> bool:
    if not user:
        return False
    return str(user.get("email") or "").strip().lower() in admin_emails()


def require_admin(request: Request) -> dict:
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Требуется вход в аккаунт")
    if not is_admin_user(user):
        raise HTTPException(status_code=403, detail="Доступ к панели администратора запрещён")
    return user


def is_https(request: Request) -> bool:
    return request.url.scheme == "https"


def new_token(size: int = 32) -> str:
    return secrets.token_urlsafe(size)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def client_ip(request: Request) -> str:
    return (request.client.host if request.client else None) or "unknown"


def require_csrf(request: Request) -> str:
    cookie_token = request.cookies.get(CSRF_COOKIE, "")
    header_token = request.headers.get("X-CSRF-Token", "")
    if not cookie_token or not header_token or not secrets.compare_digest(cookie_token, header_token):
        raise HTTPException(status_code=403, detail="CSRF-токен недействителен")
    return cookie_token


def csrf_token_from_cookie(request: Request) -> str:
    token = request.cookies.get(CSRF_COOKIE, "")
    return token if token else new_token(24)


def set_csrf_cookie(response, request: Request, token: str) -> None:
    response.set_cookie(
        CSRF_COOKIE,
        token,
        max_age=CSRF_MAX_AGE,
        httponly=False,
        secure=is_https(request),
        samesite="lax",
        path="/",
    )


def set_session_cookie(response, request: Request, token: str, max_age: int = SESSION_MAX_AGE) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=max_age,
        httponly=True,
        secure=is_https(request),
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")


def consume_rate_limit(key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
    """Atomically consume one request from a SQLite-backed fixed window.

    Returns (allowed, retry_after_seconds). The table is shared by all worker
    processes that point at the same SQLite database, unlike an in-memory map.
    """

    now = time.time()
    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT count, window_started_at FROM rate_limits WHERE rate_key = ?",
            (key,),
        ).fetchone()

        if row is None or now - float(row["window_started_at"]) >= window_seconds:
            connection.execute(
                """
                INSERT INTO rate_limits (rate_key, count, window_started_at)
                VALUES (?, 1, ?)
                ON CONFLICT(rate_key) DO UPDATE SET
                    count=excluded.count,
                    window_started_at=excluded.window_started_at
                """,
                (key, now),
            )
            connection.commit()
            return True, 0

        count = int(row["count"] or 0)
        elapsed = max(0.0, now - float(row["window_started_at"]))
        if count >= limit:
            connection.commit()
            return False, max(1, int(window_seconds - elapsed))

        connection.execute(
            "UPDATE rate_limits SET count = count + 1 WHERE rate_key = ?",
            (key,),
        )
        connection.commit()
        return True, 0
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def create_session(user_id: int, csrf_token: Optional[str] = None, max_age: int = SESSION_MAX_AGE) -> tuple[str, str]:
    session_token = new_token(32)
    csrf_token = csrf_token or new_token(24)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=max_age)
    connection = get_connection()
    try:
        connection.execute(
            """
            INSERT INTO auth_sessions (token_hash, user_id, csrf_token, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (token_hash(session_token), int(user_id), csrf_token, expires_at.isoformat()),
        )
        connection.commit()
        return session_token, csrf_token
    finally:
        connection.close()


def get_current_user(request: Request) -> Optional[dict]:
    session_token = request.cookies.get(SESSION_COOKIE)
    if not session_token:
        return None

    connection = get_connection()
    try:
        row = connection.execute(
            """
            SELECT u.id, u.name, u.email, u.created_at, s.expires_at
            FROM auth_sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ?
              AND datetime(s.expires_at) > datetime('now')
            LIMIT 1
            """,
            (token_hash(session_token),),
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def delete_session(request: Request) -> None:
    session_token = request.cookies.get(SESSION_COOKIE)
    if not session_token:
        return
    connection = get_connection()
    try:
        connection.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (token_hash(session_token),))
        connection.commit()
    finally:
        connection.close()
