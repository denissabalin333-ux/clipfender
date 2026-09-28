"""Session-based authentication endpoints for ClipFender."""
from __future__ import annotations

import re

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.database.database import get_connection
from backend.security import (
    client_ip,
    clear_session_cookie,
    SESSION_SHORT_MAX_AGE,
    admin_emails,
    consume_rate_limit,
    create_session,
    csrf_token_from_cookie,
    delete_session,
    get_current_user,
    require_csrf,
    set_csrf_cookie,
    set_session_cookie,
)

router = APIRouter(prefix="/auth", tags=["auth"])
password_hasher = PasswordHasher()
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegisterPayload(BaseModel):
    name: str
    email: str
    password: str


class LoginPayload(BaseModel):
    login: str
    password: str
    remember: bool = False


def normalized_email(value: str) -> str:
    return " ".join(str(value or "").strip().split()).lower()


def validate_credentials(name: str, email: str, password: str) -> tuple[str, str, str]:
    clean_name = " ".join(str(name or "").strip().split())
    clean_email = normalized_email(email)
    clean_password = str(password or "")
    if len(clean_name) < 2 or len(clean_name) > 80:
        raise HTTPException(status_code=422, detail="Имя должно содержать от 2 до 80 символов")
    if not EMAIL_RE.fullmatch(clean_email) or len(clean_email) > 254:
        raise HTTPException(status_code=422, detail="Укажи корректный email")
    if len(clean_password) < 8 or len(clean_password) > 128:
        raise HTTPException(status_code=422, detail="Пароль должен содержать от 8 до 128 символов")
    return clean_name, clean_email, clean_password


@router.get("/csrf")
def csrf(request: Request):
    token = csrf_token_from_cookie(request)
    response = JSONResponse({"ok": True})
    set_csrf_cookie(response, request, token)
    return response


@router.post("/register")
def register(payload: RegisterPayload, request: Request):
    require_csrf(request)
    allowed, retry_after = consume_rate_limit(f"auth:register:{client_ip(request)}", 5, 15 * 60)
    if not allowed:
        raise HTTPException(status_code=429, detail=f"Слишком много попыток регистрации. Повтори через {retry_after} сек.")

    name, email, password = validate_credentials(payload.name, payload.email, payload.password)

    # An ADMIN_EMAILS entry grants privileged access by design. Public self-registration
    # must therefore never be able to claim an allowlisted admin address without the
    # owner first creating the account through a non-public provisioning step or by
    # registering the address before adding it to ADMIN_EMAILS.
    if email in admin_emails():
        raise HTTPException(
            status_code=403,
            detail="Этот email зарезервирован для администратора и не может быть зарегистрирован через публичную форму.",
        )

    connection = get_connection()
    try:
        existing = connection.execute("SELECT id FROM users WHERE email = ? COLLATE NOCASE LIMIT 1", (email,)).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="Пользователь с таким email уже существует")
        password_hash = password_hasher.hash(password)
        cursor = connection.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash),
        )
        user_id = int(cursor.lastrowid)
        connection.commit()
    finally:
        connection.close()

    session_token, csrf_token = create_session(user_id)
    response = JSONResponse({"ok": True, "user": {"id": user_id, "name": name, "email": email}})
    set_session_cookie(response, request, session_token)
    set_csrf_cookie(response, request, csrf_token)
    return response


@router.post("/login")
def login(payload: LoginPayload, request: Request):
    require_csrf(request)
    allowed, retry_after = consume_rate_limit(f"auth:login:{client_ip(request)}", 8, 15 * 60)
    if not allowed:
        raise HTTPException(status_code=429, detail=f"Слишком много попыток входа. Повтори через {retry_after} сек.")

    identifier = " ".join(str(payload.login or "").strip().split()).lower()
    password = str(payload.password or "")
    if not identifier or not password or len(password) > 128:
        raise HTTPException(status_code=422, detail="Заполни логин и пароль")

    connection = get_connection()
    try:
        row = connection.execute(
            """
            SELECT id, name, email, password_hash
            FROM users
            WHERE lower(email) = ? OR lower(name) = ?
            ORDER BY id ASC
            LIMIT 1
            """,
            (identifier, identifier),
        ).fetchone()
    finally:
        connection.close()

    if not row:
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")

    try:
        password_hasher.verify(row["password_hash"], password)
    except (VerifyMismatchError, VerificationError):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль") from None

    session_max_age = 60 * 60 * 24 * 30 if payload.remember else SESSION_SHORT_MAX_AGE
    session_token, csrf_token = create_session(int(row["id"]), max_age=session_max_age)
    response = JSONResponse({"ok": True, "user": {"id": int(row["id"]), "name": row["name"], "email": row["email"]}})
    set_session_cookie(response, request, session_token, max_age=session_max_age)
    set_csrf_cookie(response, request, csrf_token)
    return response


@router.post("/logout")
def logout(request: Request):
    require_csrf(request)
    delete_session(request)
    response = JSONResponse({"ok": True})
    clear_session_cookie(response)
    return response




class DeleteAccountPayload(BaseModel):
    password: str


@router.delete("/me")
def delete_account(payload: DeleteAccountPayload, request: Request):
    require_csrf(request)
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Требуется вход в аккаунт")

    password = str(payload.password or "")
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT id, password_hash FROM users WHERE id = ? LIMIT 1",
            (int(user["id"]),),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        try:
            password_hasher.verify(row["password_hash"], password)
        except (VerifyMismatchError, VerificationError):
            raise HTTPException(status_code=401, detail="Пароль указан неверно") from None

        user_id = int(row["id"])
        connection.execute("DELETE FROM collection_items WHERE collection_id IN (SELECT id FROM collections WHERE user_id = ?)", (user_id,))
        connection.execute("DELETE FROM collections WHERE user_id = ?", (user_id,))
        connection.execute("DELETE FROM user_favorites WHERE user_id = ?", (user_id,))
        connection.execute("DELETE FROM search_history WHERE user_id = ?", (user_id,))
        connection.execute("DELETE FROM saved_filters WHERE user_id = ?", (user_id,))
        connection.execute("DELETE FROM bookmarks WHERE user_id = ?", (user_id,))
        connection.execute("DELETE FROM video_reports WHERE user_id = ?", (user_id,))
        connection.execute("DELETE FROM auth_sessions WHERE user_id = ?", (user_id,))
        connection.execute("DELETE FROM users WHERE id = ?", (user_id,))
        connection.commit()
    finally:
        connection.close()

    response = JSONResponse({"ok": True})
    clear_session_cookie(response)
    return response


@router.get("/me")
def me(request: Request):
    user = get_current_user(request)
    if not user:
        return {"authenticated": False, "user": None}
    return {"authenticated": True, "user": user}
