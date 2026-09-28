"""Contact form endpoint with SQLite persistence and optional delivery."""
from __future__ import annotations

import asyncio
import os
import re
import smtplib
from email.message import EmailMessage

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.database.database import get_connection
from backend.security import client_ip, consume_rate_limit, require_csrf

router = APIRouter(prefix="/contact", tags=["contact"])
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ContactPayload(BaseModel):
    name: str
    email: str
    message: str
    website: str = ""


def _send_smtp(subject: str, body: str, sender_email: str) -> bool:
    host = os.getenv("CONTACT_SMTP_HOST", "").strip()
    to_email = os.getenv("CONTACT_TO_EMAIL", "").strip()
    if not host or not to_email:
        return False

    port = int(os.getenv("CONTACT_SMTP_PORT", "587"))
    username = os.getenv("CONTACT_SMTP_USER", "").strip()
    password = os.getenv("CONTACT_SMTP_PASSWORD", "")
    use_tls = os.getenv("CONTACT_SMTP_TLS", "1").strip().lower() not in {"0", "false", "no"}

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = os.getenv("CONTACT_FROM_EMAIL", username or sender_email or to_email)
    message["To"] = to_email
    if sender_email:
        message["Reply-To"] = sender_email
    message.set_content(body)

    with smtplib.SMTP(host, port, timeout=12) as smtp:
        smtp.ehlo()
        if use_tls:
            smtp.starttls()
            smtp.ehlo()
        if username:
            smtp.login(username, password)
        smtp.send_message(message)
    return True


async def _send_telegram(text: str) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(url, json={"chat_id": chat_id, "text": text})
        response.raise_for_status()
    return True


@router.post("")
async def contact(payload: ContactPayload, request: Request):
    require_csrf(request)
    allowed, retry_after = consume_rate_limit(f"contact:{client_ip(request)}", 4, 15 * 60)
    if not allowed:
        raise HTTPException(status_code=429, detail=f"Слишком много сообщений. Повтори через {retry_after} сек.")

    name = " ".join(str(payload.name or "").strip().split())
    email = str(payload.email or "").strip().lower()
    message = str(payload.message or "").strip()

    if payload.website.strip():
        return {"ok": True, "message": "Сообщение принято."}
    if len(name) < 2 or len(name) > 80:
        raise HTTPException(status_code=422, detail="Укажи имя от 2 до 80 символов")
    if len(email) > 254 or not EMAIL_RE.fullmatch(email):
        raise HTTPException(status_code=422, detail="Укажи корректный email")
    if len(message) < 10 or len(message) > 6000:
        raise HTTPException(status_code=422, detail="Сообщение должно содержать от 10 до 6000 символов")

    ip = client_ip(request)
    user_agent = request.headers.get("user-agent", "")[:500]
    connection = get_connection()
    try:
        cursor = connection.execute(
            """
            INSERT INTO contact_messages (name, email, message, ip_address, user_agent, status, delivery)
            VALUES (?, ?, ?, ?, ?, 'new', 'saved')
            """,
            (name, email, message, ip, user_agent),
        )
        message_id = int(cursor.lastrowid)
        connection.commit()
    finally:
        connection.close()

    subject = f"ClipFender: сообщение #{message_id} от {name}"
    body = f"Имя: {name}\nEmail: {email}\nIP: {ip}\n\n{message}"

    deliveries: list[str] = []
    if os.getenv("CONTACT_SMTP_HOST", "").strip() and os.getenv("CONTACT_TO_EMAIL", "").strip():
        try:
            if await asyncio.to_thread(_send_smtp, subject, body, email):
                deliveries.append("email")
        except Exception:
            pass

    if os.getenv("TELEGRAM_BOT_TOKEN", "").strip() and os.getenv("TELEGRAM_CHAT_ID", "").strip():
        try:
            if await _send_telegram(f"{subject}\n\n{body}"):
                deliveries.append("telegram")
        except Exception:
            pass

    delivery_status = ",".join(deliveries) if deliveries else "saved"
    connection = get_connection()
    try:
        connection.execute(
            "UPDATE contact_messages SET delivery = ?, status = 'processed' WHERE id = ?",
            (delivery_status, message_id),
        )
        connection.commit()
    finally:
        connection.close()

    return {
        "ok": True,
        "message": "Сообщение сохранено и принято в обработку.",
        "delivery": delivery_status,
    }
