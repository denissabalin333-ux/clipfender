from __future__ import annotations

import os

from fastapi import APIRouter, Body, HTTPException, Request

from backend.security import client_ip, consume_rate_limit
from backend.services.character_catalog import ensure_character, existing_character

router = APIRouter()


@router.post("/characters/ensure")
def ensure_character_endpoint(request: Request, payload: dict = Body(default_factory=dict)):
    """Ensure a requested character has a verified local portrait/profile.

    This endpoint is deliberately rate-limited because a missing portrait may
    trigger an external image-search request or a paid image-generation call.
    """
    fetch_site = request.headers.get("Sec-Fetch-Site", "").strip().lower()
    if fetch_site == "cross-site":
        raise HTTPException(status_code=403, detail="Запрос к каталогу персонажей должен идти с самого сайта ClipFender.")

    allowed, retry_after = consume_rate_limit(
        f"character-discovery:{client_ip(request)}",
        int(os.getenv("CHARACTER_DISCOVERY_RATE_LIMIT", "3") or 3),
        int(os.getenv("CHARACTER_DISCOVERY_RATE_WINDOW", "86400") or 86400),
    )
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Лимит автоматического добавления персонажей на сегодня исчерпан для этого подключения.",
            headers={"Retry-After": str(max(1, retry_after))},
        )

    name = " ".join(str(payload.get("name") or "").strip().split())
    if len(name) < 3 or len(name) > 80:
        raise HTTPException(status_code=422, detail="Имя персонажа должно содержать от 3 до 80 символов.")

    already = existing_character(name)
    if already:
        return {"ok": True, "status": "ready", "created": False, "character": already}

    try:
        result = ensure_character(name)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=503, detail="Не удалось подготовить профиль персонажа. Повтори позже.") from error

    if result.get("status") == "ready":
        return {"ok": True, **result}
    return {"ok": False, **result}
