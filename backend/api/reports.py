"""Authenticated user reports for YouTube materials."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.database.database import get_connection
from backend.security import client_ip, consume_rate_limit, get_current_user, require_csrf

router = APIRouter(prefix="/reports", tags=["reports"])
ALLOWED_REASONS = {"copyright", "wrong_content", "broken", "duplicate", "other"}


class ReportPayload(BaseModel):
    video_id: str
    reason: str
    details: str = ""


def _user_id(request: Request) -> int:
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Требуется вход в аккаунт")
    return int(user["id"])


@router.post("")
def create_report(payload: ReportPayload, request: Request):
    user_id = _user_id(request)
    require_csrf(request)
    allowed, retry_after = consume_rate_limit(f"report:{client_ip(request)}", 4, 15 * 60)
    if not allowed:
        raise HTTPException(status_code=429, detail=f"Слишком много жалоб. Повтори через {retry_after} сек.")

    video_id = " ".join(str(payload.video_id or "").strip().split())
    reason = str(payload.reason or "").strip().lower()
    details = " ".join(str(payload.details or "").strip().split())
    if not video_id or len(video_id) > 128:
        raise HTTPException(status_code=422, detail="video_id обязателен")
    if reason not in ALLOWED_REASONS:
        raise HTTPException(status_code=422, detail="Неизвестная причина жалобы")
    if len(details) > 1200:
        raise HTTPException(status_code=422, detail="Описание слишком длинное")

    connection = get_connection()
    try:
        existing = connection.execute(
            "SELECT id FROM video_reports WHERE user_id = ? AND video_id = ? AND status = 'open' LIMIT 1",
            (user_id, video_id),
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="По этому материалу у тебя уже есть открытая жалоба")
        cursor = connection.execute(
            "INSERT INTO video_reports (user_id, video_id, reason, details) VALUES (?, ?, ?, ?)",
            (user_id, video_id, reason, details),
        )
        connection.commit()
        return {"ok": True, "id": int(cursor.lastrowid), "status": "open"}
    finally:
        connection.close()
