from __future__ import annotations

import base64
import io
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from PIL import Image, ImageFilter, ImageStat

from backend.config import APP_ENV, BASE_DIR
from backend.character_profiles import CHARACTER_PROFILES
from backend.database.database import REMOTE_DATABASE_ENABLED, get_connection

logger = logging.getLogger("clipfender.character_catalog")

FRONTEND_DIR = BASE_DIR / "frontend"
DEFAULT_CHARACTER_STORAGE = BASE_DIR / "data" / "characters"
GENERATED_DIR = Path(os.getenv("CHARACTER_STORAGE_DIR", str(DEFAULT_CHARACTER_STORAGE))).expanduser().resolve()

# Bing Image Search is retired. The legacy implementation is preserved below for archive/history
# compatibility but is permanently disabled in the active production pipeline.
IMAGE_SEARCH_ENABLED = False
IMAGE_SEARCH_API_KEY = os.getenv("BING_IMAGE_SEARCH_API_KEY", "").strip()
IMAGE_SEARCH_ENDPOINT = os.getenv(
    "BING_IMAGE_SEARCH_ENDPOINT",
    "https://api.bing.microsoft.com/v7.0/images/search",
).strip()
IMAGE_SEARCH_COUNT = max(1, min(50, int(os.getenv("CHARACTER_IMAGE_SEARCH_COUNT", "12") or 12)))
IMAGE_SEARCH_ALLOWED_HOSTS = {
    host.strip().lower()
    for host in os.getenv("CHARACTER_IMAGE_SEARCH_ALLOWED_HOSTS", "").split(",")
    if host.strip()
}

IMAGE_GENERATION_ENABLED = os.getenv("CHARACTER_IMAGE_GENERATION_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_IMAGE_ENDPOINT = os.getenv(
    "OPENAI_IMAGE_ENDPOINT",
    "https://api.openai.com/v1/images/generations",
).strip()
OPENAI_IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2").strip() or "gpt-image-2"
OPENAI_IMAGE_SIZE = os.getenv("OPENAI_IMAGE_SIZE", "1024x1536").strip() or "1024x1536"

MIN_SHORT_SIDE = max(600, int(os.getenv("CHARACTER_IMAGE_MIN_SHORT_SIDE", "900") or 900))
MAX_DOWNLOAD_BYTES = max(1_000_000, int(os.getenv("CHARACTER_IMAGE_MAX_BYTES", "12000000") or 12000000))
MIN_EDGE_SCORE = float(os.getenv("CHARACTER_IMAGE_MIN_EDGE_SCORE", "7") or 7)
DISCOVERY_RATE_LIMIT = max(1, int(os.getenv("CHARACTER_DISCOVERY_RATE_LIMIT", "3") or 3))
DISCOVERY_RATE_WINDOW = max(60, int(os.getenv("CHARACTER_DISCOVERY_RATE_WINDOW", "86400") or 86400))
GENERATION_DAILY_GUARD = max(1, int(os.getenv("CHARACTER_GENERATION_DAILY_GUARD", "10") or 10))

KNOWN_CHARACTER_HINTS: dict[str, dict[str, Any]] = {
    "санса старк": {"house": "СТАРК · СЕВЕР · ВИНТЕРФЕЛЛ", "edit_profile": ["drama", "emotional", "dark", "tension"]},
    "эддард старк": {"house": "СТАРК · СЕВЕР · ВИНТЕРФЕЛЛ", "edit_profile": ["drama", "dark", "tension", "epic"]},
    "нед старк": {"house": "СТАРК · СЕВЕР · ВИНТЕРФЕЛЛ", "edit_profile": ["drama", "dark", "tension", "epic"]},
    "робб старк": {"house": "СТАРК · СЕВЕР · КОРОЛЬ СЕВЕРА", "edit_profile": ["action", "epic", "drama", "tension"]},
    "брандон старк": {"house": "СТАРК · СЕВЕР · ВИНТЕРФЕЛЛ", "edit_profile": ["dark", "epic", "tension"]},
    "брэн старк": {"house": "СТАРК · СЕВЕР · ВИНТЕРФЕЛЛ", "edit_profile": ["dark", "epic", "tension"]},
    "брэндан старк": {"house": "СТАРК · СЕВЕР · ВИНТЕРФЕЛЛ", "edit_profile": ["dark", "epic", "tension"]},
    "бранд старк": {"house": "СТАРК · СЕВЕР · ВИНТЕРФЕЛЛ", "edit_profile": ["dark", "epic", "tension"]},
    "бриенна тарт": {"house": "ТАРТ · ШТОРМОВЫЕ ЗЕМЛИ", "edit_profile": ["action", "drama", "epic", "tension"]},
    "сандор клиган": {"house": "КЛИГАН · КОРОЛЕВСТВО", "edit_profile": ["action", "dark", "tension"]},
    "пёс": {"house": "КЛИГАН · КОРОЛЕВСТВО", "edit_profile": ["action", "dark", "tension"]},
    "мелисандра": {"house": "ПЕСТЕРЫ / СВЕТЛЫЙ ВЛАДЫКА", "edit_profile": ["dark", "epic", "tension", "emotional"]},
    "петир бейлиш": {"house": "БЕЙЛИШ · ДОЛИНА", "edit_profile": ["dark", "drama", "tension"]},
    "мизинец": {"house": "БЕЙЛИШ · ДОЛИНА", "edit_profile": ["dark", "drama", "tension"]},
    "варис": {"house": "КРАСНЫЙ ЗАМОК · МАСТЕР ШЕПОТОВ", "edit_profile": ["drama", "dark", "tension"]},
    "джорах мормонт": {"house": "МОРМОНТ · МЕДВЕЖИЙ ОСТРОВ", "edit_profile": ["drama", "action", "emotional", "epic"]},
    "теон грейджой": {"house": "ГРЕЙДЖОЙ · ЖЕЛЕЗНЫЕ ОСТРОВА", "edit_profile": ["dark", "drama", "action", "emotional"]},
    "йгритт": {"house": "ВОЛЬНЫЙ НАРОД", "edit_profile": ["action", "romance", "emotional", "tension"]},
    "кхал дрого": {"house": "ДОТРАКИЙЦЫ", "edit_profile": ["action", "epic", "dark"]},
    "тайвин ланнистер": {"house": "ЛАННИСТЕР · ЗАПАД · УТЁС КАСТЕРЛИ", "edit_profile": ["drama", "dark", "tension", "epic"]},
    "стэннис баратеон": {"house": "БАРАТЕОН · ШТОРМОВЫЕ ЗЕМЛИ", "edit_profile": ["dark", "drama", "tension", "epic"]},
    "роберт баратеон": {"house": "БАРАТЕОН · ШТОРМОВЫЕ ЗЕМЛИ", "edit_profile": ["drama", "action", "epic"]},
    "самвелл тарли": {"house": "ТАРЛИ · ЦИТАДЕЛЬ / НОЧНОЙ ДОЗОР", "edit_profile": ["drama", "emotional", "dark"]},
    "ходор": {"house": "СТАРК · СЕВЕР", "edit_profile": ["emotional", "drama", "dark"]},
    "миссандея": {"house": "ТАРГАРИЕН · МЕЭРИН", "edit_profile": ["emotional", "drama", "romance"]},
}

ALIASES = {
    "sansa": "санса старк",
    "sansa stark": "санса старк",
    "ned stark": "эддард старк",
    "eddard stark": "эддард старк",
    "rob stark": "робб старк",
    "rob stark": "робб старк",
    "robb stark": "робб старк",
    "brienne": "бриенна тарт",
    "brienne of tarth": "бриенна тарт",
    "the hound": "сандор клиган",
    "hound": "сандор клиган",
    "littlefinger": "мизинец",
    "petyr baelish": "петир бейлиш",
    "varys": "варис",
    "jorah": "джорах мормонт",
    "theon": "теон грейджой",
    "ygritte": "йгритт",
    "drogo": "кхал дрого",
    "tywin": "тайвин ланнистер",
    "stannis": "стэннис баратеон",
    "robert": "роберт баратеон",
    "samwell tarly": "самвелл тарли",
    "sam tarly": "самвелл тарли",
    "hodor": "ходор",
    "missandei": "миссандея",
}


def normalize_name(value: str) -> str:
    value = " ".join(str(value or "").strip().split())
    return value.casefold()


def canonical_name(value: str) -> str:
    normalized = normalize_name(value)
    return ALIASES.get(normalized, normalized)


def slugify(value: str) -> str:
    text = normalize_name(value)
    translit = str.maketrans({
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh", "з": "z", "и": "i",
        "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
        "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "",
        "э": "e", "ю": "yu", "я": "ya",
    })
    text = text.translate(translit)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:80] or "character"


def _hints_for(name: str) -> dict[str, Any]:
    canonical = canonical_name(name)
    hints = KNOWN_CHARACTER_HINTS.get(canonical, {})
    if hints:
        return dict(hints)
    return {
        "house": "ПРОФИЛЬ НЕ УКАЗАН · ОПРЕДЕЛЯЕТСЯ ПО ЗАПРОСУ",
        "edit_profile": ["drama"],
    }


def _summary_for(name: str, hints: dict[str, Any]) -> str:
    house = str(hints.get("house") or "").strip()
    if house and not house.startswith("ПРОФИЛЬ НЕ УКАЗАН"):
        return f"Автоматически добавленный профиль персонажа {name}. Принадлежность: {house}. Портрет получен через настроенный источник ClipFender и сохранён локально для следующих запросов."
    return f"Автоматически добавленный профиль персонажа {name}. Портрет получен через настроенный источник ClipFender и сохранён локально для следующих запросов."


def _build_profile(name: str, image_path: str, source_type: str, source_url: str = "") -> dict[str, Any]:
    hints = _hints_for(name)
    clean_name = " ".join(str(name).strip().split())
    slug = slugify(clean_name)
    return {
        "slug": slug,
        "name": clean_name,
        "short_name": clean_name.upper(),
        "house": hints.get("house", "ПРОФИЛЬ НЕ УКАЗАН"),
        "query": clean_name,
        "image": image_path,
        "summary": _summary_for(clean_name, hints),
        "lore": [
            "Профиль создан автоматически после явного запроса пользователя.",
            "Материал для портрета и данные профиля не выдаются как готовые, пока asset не прошёл проверку.",
        ],
        "edit_profile": list(hints.get("edit_profile", ["drama"])),
        "auto_generated": True,
        "portrait_source_type": source_type,
        "portrait_source_url": source_url,
    }


def character_media_public_path(slug: str) -> str:
    return f"/media/characters/{slug}-hq.webp"


def resolve_character_image_path(image_url: str) -> Path | None:
    """Resolve a character portrait URL to a file without allowing path traversal."""
    value = str(image_url or "").strip()
    if value.startswith("/static/"):
        candidate = (FRONTEND_DIR / value.removeprefix("/static/")).resolve()
        root = FRONTEND_DIR.resolve()
    elif value.startswith("/media/characters/"):
        filename = Path(value.removeprefix("/media/characters/")).name
        if filename != value.removeprefix("/media/characters/") or not filename.endswith("-hq.webp"):
            return None
        candidate = (GENERATED_DIR / filename).resolve()
        root = GENERATED_DIR.resolve()
    else:
        return None
    if root not in candidate.parents:
        return None
    return candidate


def migrate_legacy_generated_portraits() -> int:
    """Copy legacy generated portraits into local storage when not using remote DB."""
    if REMOTE_DATABASE_ENABLED:
        return 0

    old_dir = FRONTEND_DIR / "assets" / "reference" / "generated"
    if not old_dir.is_dir() or old_dir.resolve() == GENERATED_DIR.resolve():
        return 0
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    connection = get_connection()
    migrated = 0
    try:
        rows = connection.execute("SELECT slug, image FROM character_catalog WHERE status = 'ready'").fetchall()
        for row in rows:
            image = str(row["image"] or "")
            if not image.startswith("/static/assets/reference/generated/"):
                continue
            filename = Path(image).name
            source = (old_dir / filename).resolve()
            target = (GENERATED_DIR / filename).resolve()
            if old_dir.resolve() not in source.parents or not source.is_file():
                continue
            if not target.exists():
                target.write_bytes(source.read_bytes())
            connection.execute(
                "UPDATE character_catalog SET image = ?, updated_at = CURRENT_TIMESTAMP WHERE slug = ?",
                (character_media_public_path(str(row["slug"])), str(row["slug"])),
            )
            migrated += 1
        connection.commit()
    finally:
        connection.close()
    return migrated


def get_dynamic_character(slug: str) -> dict[str, Any] | None:
    clean_slug = slugify(slug)
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT * FROM character_catalog WHERE slug = ? AND status = 'ready' LIMIT 1",
            (clean_slug,),
        ).fetchone()
        if not row:
            return None
        profile = _row_to_profile(row)
        image_url = str(profile.get("image") or "")
        if REMOTE_DATABASE_ENABLED and image_url.startswith("/media/characters/"):
            return profile
        asset_path = resolve_character_image_path(image_url)
        if asset_path is None or not asset_path.is_file():
            return None
        return profile
    finally:
        connection.close()


def list_dynamic_characters() -> list[dict[str, Any]]:
    connection = get_connection()
    try:
        rows = connection.execute(
            "SELECT * FROM character_catalog WHERE status = 'ready' ORDER BY created_at DESC, name COLLATE NOCASE ASC"
        ).fetchall()
        return [_row_to_profile(row) for row in rows]
    finally:
        connection.close()


def merged_catalog() -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for slug, profile in CHARACTER_PROFILES.items():
        merged[slug] = profile
    for profile in list_dynamic_characters():
        merged.setdefault(profile["slug"], profile)
    return list(merged.values())


def _row_to_profile(row) -> dict[str, Any]:
    profile = dict(row)
    for field in ("lore_json", "edit_profile_json"):
        try:
            profile[field] = json.loads(profile.get(field) or "[]")
        except (TypeError, ValueError, json.JSONDecodeError):
            profile[field] = []
    return {
        "slug": profile["slug"],
        "name": profile["name"],
        "short_name": profile.get("short_name") or profile["name"].upper(),
        "house": profile.get("house") or "ПРОФИЛЬ НЕ УКАЗАН",
        "query": profile.get("query") or profile["name"],
        "image": profile["image"],
        "summary": profile.get("summary") or "",
        "lore": profile.get("lore_json") or [],
        "edit_profile": profile.get("edit_profile_json") or ["drama"],
        "auto_generated": True,
        "portrait_source_type": profile.get("portrait_source_type") or "unknown",
        "portrait_source_url": profile.get("portrait_source_url") or "",
    }


def _allowed_image_host(url: str) -> bool:
    if not IMAGE_SEARCH_ALLOWED_HOSTS:
        return False
    host = (urlparse(url).hostname or "").lower().rstrip(".")
    if not host:
        return False
    return any(host == allowed or host.endswith("." + allowed) for allowed in IMAGE_SEARCH_ALLOWED_HOSTS)


def _edge_score(image: Image.Image) -> float:
    gray = image.convert("L").resize((256, 256))
    edges = gray.filter(ImageFilter.FIND_EDGES)
    return float(ImageStat.Stat(edges).mean[0])


def _normalize_image(raw: bytes) -> tuple[bytes, dict[str, Any]]:
    if len(raw) > MAX_DOWNLOAD_BYTES:
        raise ValueError("image-too-large")
    image = Image.open(io.BytesIO(raw))
    image.load()
    if image.width < MIN_SHORT_SIDE or image.height < MIN_SHORT_SIDE:
        raise ValueError("image-too-small")
    edge_score = _edge_score(image)
    if edge_score < MIN_EDGE_SCORE:
        raise ValueError("image-too-soft")
    image = image.convert("RGB")
    image.thumbnail((1400, 1800), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, format="WEBP", quality=94, method=6)
    return buffer.getvalue(), {
        "width": image.width,
        "height": image.height,
        "edge_score": round(edge_score, 2),
    }


def _search_bing(name: str) -> list[dict[str, Any]]:
    if not IMAGE_SEARCH_ENABLED or not IMAGE_SEARCH_API_KEY:
        return []
    query = f"{name} Game of Thrones official portrait"
    headers = {"Ocp-Apim-Subscription-Key": IMAGE_SEARCH_API_KEY}
    params = {
        "q": query,
        "count": str(IMAGE_SEARCH_COUNT),
        "safeSearch": "Strict",
        "imageType": "Photo",
        "size": "Large",
        "mkt": "ru-RU",
    }
    try:
        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            response = client.get(IMAGE_SEARCH_ENDPOINT, headers=headers, params=params)
            response.raise_for_status()
            payload = response.json()
    except Exception:
        logger.exception("Character image search failed for %r", name)
        return []

    candidates = []
    for item in payload.get("value", []) or []:
        content_url = str(item.get("contentUrl") or "").strip()
        if not content_url or not _allowed_image_host(content_url):
            continue
        candidates.append({
            "url": content_url,
            "host_page": str(item.get("hostPageUrl") or "").strip(),
            "width": int(item.get("width") or 0),
            "height": int(item.get("height") or 0),
            "name": str(item.get("name") or "").strip(),
        })
    candidates.sort(key=lambda item: item["width"] * item["height"], reverse=True)
    return candidates


def _download_image(url: str) -> tuple[bytes, dict[str, Any]] | None:
    if not _allowed_image_host(url):
        return None
    try:
        with httpx.Client(timeout=25.0, follow_redirects=True, headers={"User-Agent": "ClipFender/16.0"}) as client:
            response = client.get(url)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
            if not content_type.startswith("image/"):
                return None
            return _normalize_image(response.content)
    except Exception as exc:
        logger.info("Rejected portrait download %s: %s", url, exc)
        return None


def _generation_prompt(name: str) -> str:
    hints = _hints_for(name)
    return (
        "Create a single premium cinematic medieval-fantasy character portrait for the ClipFender website. "
        f"Character: {name}. House or affiliation context: {hints.get('house', 'unknown')}. "
        "Show a recognizable fictional character interpretation from the Game of Thrones universe, chest-up / waist-up, vertical portrait, "
        "sharp facial detail, realistic skin and costume texture, dramatic cool shadows with restrained warm bronze firelight, dark stone or atmospheric background, "
        "subtle depth of field but the face itself must remain crisp. No text, no captions, no logos, no border, no watermark, no UI, no circular frame. "
        "Keep the composition centered and suitable for a 620x350 responsive card crop while preserving face clarity."
    )


def _generate_openai(name: str) -> tuple[bytes, dict[str, Any]] | None:
    if not IMAGE_GENERATION_ENABLED or not OPENAI_API_KEY:
        return None
    payload = {
        "model": OPENAI_IMAGE_MODEL,
        "prompt": _generation_prompt(name),
        "size": OPENAI_IMAGE_SIZE,
        "n": 1,
    }
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    try:
        with httpx.Client(timeout=90.0, follow_redirects=True) as client:
            response = client.post(OPENAI_IMAGE_ENDPOINT, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json().get("data") or []
            if not data:
                return None
            item = data[0]
            raw: bytes | None = None
            b64 = str(item.get("b64_json") or "").strip()
            if b64:
                raw = base64.b64decode(b64)
            else:
                image_url = str(item.get("url") or "").strip()
                if image_url:
                    with httpx.Client(timeout=45.0, follow_redirects=True) as downloader:
                        download = downloader.get(image_url)
                        download.raise_for_status()
                        raw = download.content
            if not raw:
                return None
            return _normalize_image(raw)
    except Exception:
        logger.exception("OpenAI character portrait generation failed for %r", name)
        return None


def _generation_bucket() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _reserve_generation_quota() -> bool:
    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        day = _generation_bucket()
        row = connection.execute(
            "SELECT generated_count FROM character_generation_guard WHERE bucket_date = ?",
            (day,),
        ).fetchone()
        used = int(row["generated_count"] or 0) if row else 0
        if used >= GENERATION_DAILY_GUARD:
            connection.commit()
            return False
        connection.execute(
            """
            INSERT INTO character_generation_guard (bucket_date, generated_count)
            VALUES (?, 1)
            ON CONFLICT(bucket_date) DO UPDATE SET generated_count = generated_count + 1
            """,
            (day,),
        )
        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _claim_discovery(slug: str, name: str, image_path: str) -> str:
    """Atomically reserve a missing character so concurrent requests do not double-generate."""
    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT status, updated_at FROM character_catalog WHERE slug = ? LIMIT 1",
            (slug,),
        ).fetchone()
        if row:
            status = str(row["status"] or "")
            updated_raw = str(row["updated_at"] or "")
            if status == "ready":
                connection.commit()
                return "ready"
            try:
                updated = datetime.fromisoformat(updated_raw.replace("Z", "+00:00"))
                if updated.tzinfo is None:
                    updated = updated.replace(tzinfo=timezone.utc)
            except ValueError:
                updated = datetime.now(timezone.utc) - timedelta(hours=1)
            if status == "pending" and datetime.now(timezone.utc) - updated < timedelta(minutes=15):
                connection.commit()
                return "pending"
            connection.execute(
                """
                UPDATE character_catalog
                SET name = ?, short_name = ?, query = ?, image = ?, status = 'pending', updated_at = CURRENT_TIMESTAMP
                WHERE slug = ?
                """,
                (name, name.upper(), name, image_path, slug),
            )
            connection.commit()
            return "claimed"

        connection.execute(
            """
            INSERT INTO character_catalog (
                slug, name, short_name, house, query, image, summary,
                lore_json, edit_profile_json, status, portrait_source_type,
                portrait_source_url, created_at, updated_at
            )
            VALUES (?, ?, ?, '', ?, ?, '', '[]', '["drama"]', 'pending', 'pending', '', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (slug, name, name.upper(), name, image_path),
        )
        connection.commit()
        return "claimed"
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _mark_discovery_error(slug: str, message: str = "") -> None:
    connection = get_connection()
    try:
        connection.execute(
            "UPDATE character_catalog SET status = 'error', summary = ?, updated_at = CURRENT_TIMESTAMP WHERE slug = ?",
            (message[:500], slug),
        )
        connection.commit()
    finally:
        connection.close()


def _write_profile(
    profile: dict[str, Any],
    source_url: str,
    image_bytes: bytes | None = None,
) -> None:
    import hashlib

    connection = get_connection()
    try:
        connection.execute(
            """
            INSERT INTO character_catalog (
                slug, name, short_name, house, query, image, summary,
                lore_json, edit_profile_json, status, portrait_source_type,
                portrait_source_url, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'ready', ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(slug) DO UPDATE SET
                name=excluded.name,
                short_name=excluded.short_name,
                house=excluded.house,
                query=excluded.query,
                image=excluded.image,
                summary=excluded.summary,
                lore_json=excluded.lore_json,
                edit_profile_json=excluded.edit_profile_json,
                status='ready',
                portrait_source_type=excluded.portrait_source_type,
                portrait_source_url=excluded.portrait_source_url,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                profile["slug"], profile["name"], profile["short_name"], profile["house"], profile["query"], profile["image"],
                profile["summary"], json.dumps(profile["lore"], ensure_ascii=False), json.dumps(profile["edit_profile"], ensure_ascii=False),
                profile["portrait_source_type"], source_url,
            ),
        )

        if REMOTE_DATABASE_ENABLED:
            if not image_bytes:
                raise ValueError("portrait-bytes-missing")

            digest = hashlib.sha256(image_bytes).hexdigest()

            connection.execute(
                """
                INSERT INTO character_portrait_assets (
                    slug, mime_type, image_data, source_type,
                    source_url, sha256, created_at, updated_at
                )
                VALUES (
                    ?, 'image/webp', ?, ?, ?, ?,
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                ON CONFLICT(slug) DO UPDATE SET
                    mime_type=excluded.mime_type,
                    image_data=excluded.image_data,
                    source_type=excluded.source_type,
                    source_url=excluded.source_url,
                    sha256=excluded.sha256,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    profile["slug"],
                    bytes(image_bytes),
                    profile["portrait_source_type"],
                    source_url,
                    digest,
                ),
            )

        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def existing_character(name: str) -> dict[str, Any] | None:
    requested = canonical_name(name)
    for profile in CHARACTER_PROFILES.values():
        if canonical_name(profile.get("name", "")) == requested or normalize_name(profile.get("slug", "")) == normalize_name(name):
            return profile
    slug = slugify(requested)
    dynamic = get_dynamic_character(slug)
    if dynamic:
        return dynamic
    return None


def ensure_character(name: str) -> dict[str, Any]:
    clean_name = " ".join(str(name or "").strip().split())
    if len(clean_name) < 3 or len(clean_name) > 80:
        raise ValueError("Имя персонажа должно содержать от 3 до 80 символов")

    existing = existing_character(clean_name)
    if existing:
        return {"status": "ready", "created": False, "character": existing}

    slug = slugify(clean_name)
    generated_path = GENERATED_DIR / f"{slug}-hq.webp"
    public_path = character_media_public_path(slug)

    if not REMOTE_DATABASE_ENABLED:
        GENERATED_DIR.mkdir(parents=True, exist_ok=True)

    claim = _claim_discovery(slug, clean_name, public_path)
    if claim == "ready":
        existing = get_dynamic_character(slug)
        if existing:
            return {"status": "ready", "created": False, "character": existing}
    if claim == "pending":
        return {
            "status": "pending",
            "created": False,
            "message": "Портрет этого персонажа уже готовится другим запросом. Повтори через несколько секунд.",
        }

    # Web search is intentionally disabled because the legacy Bing Image Search API was retired.
    search_candidates: list[dict[str, Any]] = []
    for candidate in search_candidates:
        normalized = _download_image(candidate["url"])
        if not normalized:
            continue
        raw, meta = normalized
        if not REMOTE_DATABASE_ENABLED:
            generated_path.write_bytes(raw)
        profile = _build_profile(clean_name, public_path, "web_search", candidate.get("host_page") or candidate["url"])
        _write_profile(profile, candidate.get("host_page") or candidate["url"], raw)
        return {"status": "ready", "created": True, "source": "web_search", "image_meta": meta, "character": profile}

    if IMAGE_GENERATION_ENABLED and OPENAI_API_KEY:
        if not _reserve_generation_quota():
            _mark_discovery_error(slug, "Дневной лимит автоматической генерации портретов исчерпан.")
            return {
                "status": "unavailable",
                "created": False,
                "message": "Дневной лимит автоматической генерации портретов исчерпан. Персонаж не добавлен в каталог.",
            }
        normalized = _generate_openai(clean_name)
        if normalized:
            raw, meta = normalized
            if not REMOTE_DATABASE_ENABLED:
                generated_path.write_bytes(raw)
            profile = _build_profile(clean_name, public_path, "ai_generation", "")
            _write_profile(profile, "", raw)
            return {"status": "ready", "created": True, "source": "ai_generation", "image_meta": meta, "character": profile}

    _mark_discovery_error(slug, "Не удалось получить качественный портрет.")
    return {
        "status": "unavailable",
        "created": False,
        "message": "Не удалось получить качественный портрет. Персонаж не добавлен в публичный каталог.",
    }
