import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from backend.config import APP_ENV, BASE_DIR

from backend.api.search import router as search_router
from backend.api.video import router as video_router
from backend.api.auth import router as auth_router
from backend.api.contact import router as contact_router
from backend.api.library import router as library_router
from backend.api.edit_idea import router as edit_idea_router
from backend.api.reports import router as reports_router
from backend.api.admin import router as admin_router
from backend.api.characters import router as characters_api_router
from backend.character_profiles import CHARACTER_PROFILES, get_character
from backend.services.character_catalog import (
    GENERATED_DIR,
    get_dynamic_character,
    list_dynamic_characters,
    merged_catalog,
    migrate_legacy_generated_portraits,
    resolve_character_image_path,
)
from backend.security import ensure_bootstrap_admin, require_admin
from backend.database.database import get_connection, init_database, migrate_database, cleanup_cache
from frontend.page_shell import render_page

FRONTEND_DIR = BASE_DIR / "frontend"

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("clipfender")

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
PLAUSIBLE_DOMAIN = os.getenv("PLAUSIBLE_DOMAIN", "").strip()
PLAUSIBLE_SCRIPT_URL = os.getenv("PLAUSIBLE_SCRIPT_URL", "https://plausible.io/js/script.js").strip()
raw_origins = os.getenv("ALLOWED_ORIGINS", "").strip()
if raw_origins == "*" and APP_ENV == "production":
    raise RuntimeError("ALLOWED_ORIGINS='*' запрещён в production")

allowed_origins = [
    item.strip().rstrip("/")
    for item in raw_origins.split(",")
    if item.strip() and item.strip() != "*"
]

if not allowed_origins and APP_ENV != "production":
    allowed_origins = [
        "http://127.0.0.1:8080",
        "http://localhost:8080",
    ]


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ClipFinder startup: initializing database")
    init_database()
    migrate_database()
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    migrate_legacy_generated_portraits()
    ensure_bootstrap_admin()
    cleanup_cache(24)
    try:
        yield
    finally:
        logger.info("ClipFinder shutdown")


app = FastAPI(
    title="ClipFinder",
    version="7.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Content-Type", "X-CSRF-Token"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    analytics_hosts = []
    for candidate in (PLAUSIBLE_DOMAIN, PLAUSIBLE_SCRIPT_URL):
        if not candidate:
            continue
        parsed = urlparse(candidate if "://" in candidate else f"https://{candidate}")
        if parsed.netloc:
            analytics_hosts.append(f"https://{parsed.netloc}")
    analytics_hosts = sorted(set(analytics_hosts))
    analytics_script_src = " ".join(analytics_hosts)
    analytics_connect_src = " ".join(analytics_hosts)
    csp = (
        "default-src 'self'; "
        "base-uri 'self'; "
        "frame-ancestors 'self'; "
        "form-action 'self'; "
        "object-src 'none'; "
        "script-src 'self' 'unsafe-inline' https://www.youtube.com https://www.youtube-nocookie.com " + analytics_script_src + "; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data: blob: https:; "
        "media-src 'self' blob: https:; "
        "frame-src 'self' https://www.youtube.com https://www.youtube-nocookie.com; "
        "connect-src 'self' " + analytics_connect_src + ";"
    )
    response.headers.setdefault("Content-Security-Policy", csp)
    if request.url.scheme == "https":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response

app.include_router(search_router, prefix="/api")
app.include_router(video_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(contact_router, prefix="/api")
app.include_router(library_router, prefix="/api")
app.include_router(edit_idea_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(characters_api_router, prefix="/api")

# Static assets are intentionally served through an explicit fallback route
# before the StaticFiles mount. This protects the public pages from hosting
# layers that incorrectly rewrite /static/* requests to the SPA/404 page.
# The existing StaticFiles mount is preserved as the normal path.
if FRONTEND_DIR.exists():
    @app.get("/static/{asset_path:path}", include_in_schema=False)
    def static_asset_fallback(asset_path: str):
        candidate = (FRONTEND_DIR / asset_path).resolve()
        frontend_root = FRONTEND_DIR.resolve()
        if frontend_root not in candidate.parents or not candidate.is_file():
            raise StarletteHTTPException(status_code=404, detail="Static asset not found")
        return FileResponse(candidate)

    app.mount(
        "/static",
        StaticFiles(directory=FRONTEND_DIR),
        name="frontend",
    )

    # Compatibility aliases: old cached pages may still request /css/* or /js/*.
    @app.get("/css/{asset_path:path}", include_in_schema=False)
    def css_compat(asset_path: str):
        candidate = (FRONTEND_DIR / "css" / asset_path).resolve()
        css_root = (FRONTEND_DIR / "css").resolve()
        if css_root not in candidate.parents or not candidate.is_file():
            raise StarletteHTTPException(status_code=404, detail="CSS asset not found")
        return FileResponse(candidate)

    @app.get("/js/{asset_path:path}", include_in_schema=False)
    def js_compat(asset_path: str):
        candidate = (FRONTEND_DIR / "js" / asset_path).resolve()
        js_root = (FRONTEND_DIR / "js").resolve()
        if js_root not in candidate.parents or not candidate.is_file():
            raise StarletteHTTPException(status_code=404, detail="JS asset not found")
        return FileResponse(candidate)


@app.get("/media/characters/{filename}", include_in_schema=False)
def dynamic_character_media(filename: str):
    # Only serve validated portrait filenames from the persistent character store.
    if not filename.endswith("-hq.webp") or len(filename) > 120:
        raise StarletteHTTPException(status_code=404, detail="Character portrait not found")
    candidate = (GENERATED_DIR / filename).resolve()
    storage_root = GENERATED_DIR.resolve()
    if storage_root not in candidate.parents or not candidate.is_file():
        raise StarletteHTTPException(status_code=404, detail="Character portrait not found")
    return FileResponse(
        candidate,
        media_type="image/webp",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.get("/", include_in_schema=False)
def home(request: Request):
    return render_page(request, "index.html")


@app.get("/archive", include_in_schema=False)
def archive(request: Request):
    return render_page(request, "archive.html")


@app.get("/search", include_in_schema=False)
def search_page(request: Request):
    return render_page(request, "pages/search.html")


@app.get("/character-search", include_in_schema=False)
def character_search():
    """Permanent compatibility redirect for the retired legacy character-search page."""
    return RedirectResponse(url="/search", status_code=301)


@app.get("/guides", include_in_schema=False)
def guides(request: Request):
    return render_page(request, "pages/guides.html")


@app.get("/edit-ideas", include_in_schema=False)
def edit_ideas(request: Request):
    return render_page(request, "pages/edit-ideas.html")


@app.get("/video", include_in_schema=False)
def video_page(request: Request):
    return render_page(request, "pages/video.html")


@app.get("/portfolio", include_in_schema=False)
def portfolio(request: Request):
    return render_page(request, "pages/portfolio.html")


@app.get("/services", include_in_schema=False)
def services(request: Request):
    return render_page(request, "pages/services.html")


@app.get("/about", include_in_schema=False)
def about(request: Request):
    return render_page(request, "pages/about.html")


@app.get("/contacts", include_in_schema=False)
def contacts(request: Request):
    return render_page(request, "pages/contacts.html")


def _available_character_catalog() -> list[dict]:
    """Return static and dynamically discovered character profiles with valid local portraits."""
    catalog: list[dict] = []
    for profile in merged_catalog():
        image = str(profile.get("image") or "")
        asset_path = resolve_character_image_path(image)
        if asset_path is None or not asset_path.is_file():
            logger.warning("Skipping character %s: portrait missing at %s", profile.get("slug"), image)
            continue
        catalog.append(profile)
    return catalog


@app.get("/characters", include_in_schema=False)
def characters(request: Request):
    character_catalog = _available_character_catalog()
    character_houses = sorted(
        {str(character.get("house", "")).split(" · ", 1)[0] for character in character_catalog if character.get("house")},
        key=str.casefold,
    )
    character_edit_profiles = sorted(
        {str(tag).strip().lower() for character in character_catalog for tag in character.get("edit_profile", []) if str(tag).strip()},
        key=str.casefold,
    )
    return render_page(
        request,
        "pages/characters.html",
        characters=character_catalog,
        character_houses=character_houses,
        character_edit_profiles=character_edit_profiles,
    )


@app.get("/characters/{slug}", include_in_schema=False)
def character_profile(request: Request, slug: str):
    character = get_character(slug) or get_dynamic_character(slug)
    if not character:
        raise HTTPException(status_code=404, detail="Персонаж не найден")

    origin = PUBLIC_BASE_URL or str(request.base_url).rstrip("/")
    canonical = f"{origin}/characters/{character['slug']}"
    page_meta = {
        "title": f"{character['name']} — сцены и профиль | CLIPFENDER",
        "description": character["summary"],
        "path": f"/characters/{character['slug']}",
        "robots": "index,follow,max-image-preview:large",
    }
    schema = {
        "@context": "https://schema.org",
        "@type": "ProfilePage",
        "name": page_meta["title"],
        "description": page_meta["description"],
        "url": canonical,
        "image": (PUBLIC_BASE_URL or str(request.base_url).rstrip("/")) + character["image"],
        "mainEntity": {
            "@type": "Thing",
            "name": character["name"],
        },
    }
    return render_page(
        request,
        "pages/character.html",
        character=character,
        page_meta=page_meta,
        canonical_url=canonical,
        og_image=(PUBLIC_BASE_URL or str(request.base_url).rstrip("/")) + character["image"],
        seo_json=json.dumps(schema, ensure_ascii=False),
    )


@app.get("/help", include_in_schema=False)
def help_page(request: Request):
    return render_page(request, "pages/help.html")


@app.get("/faq", include_in_schema=False)
def faq_page(request: Request):
    return render_page(request, "pages/faq.html")


@app.get("/project", include_in_schema=False)
def project(request: Request):
    return render_page(request, "pages/project.html")


@app.get("/login", include_in_schema=False)
def login(request: Request):
    return render_page(request, "pages/login.html")


@app.get("/library", include_in_schema=False)
def library_page(request: Request):
    return render_page(request, "pages/library.html")


@app.get("/admin", include_in_schema=False)
def admin_page(request: Request):
    require_admin(request)
    return render_page(request, "pages/admin.html")


@app.get("/privacy", include_in_schema=False)
def privacy_page(request: Request):
    return render_page(request, "pages/privacy.html")


@app.get("/terms", include_in_schema=False)
def terms_page(request: Request):
    return render_page(request, "pages/terms.html")


@app.get("/copyright", include_in_schema=False)
def copyright_page(request: Request):
    return render_page(request, "pages/copyright.html")


@app.get("/favicon.svg", include_in_schema=False)
def favicon():
    return FileResponse(FRONTEND_DIR / "favicon.svg", media_type="image/svg+xml")


def _meta_file_response(filename: str, media_type: str):
    return FileResponse(FRONTEND_DIR / "assets" / "meta" / filename, media_type=media_type)


@app.get("/favicon.ico", include_in_schema=False)
def favicon_ico():
    return FileResponse(FRONTEND_DIR / "favicon.ico", media_type="image/x-icon")


@app.get("/favicon-32x32.png", include_in_schema=False)
def favicon_png():
    return _meta_file_response("favicon-32x32.png", "image/png")


@app.get("/apple-touch-icon.png", include_in_schema=False)
def apple_touch_icon():
    return _meta_file_response("apple-touch-icon.png", "image/png")


@app.get("/icon-192.png", include_in_schema=False)
def icon_192():
    return _meta_file_response("icon-192.png", "image/png")


@app.get("/icon-512.png", include_in_schema=False)
def icon_512():
    return _meta_file_response("icon-512.png", "image/png")


@app.get("/manifest.webmanifest", include_in_schema=False)
def manifest():
    return FileResponse(FRONTEND_DIR / "manifest.webmanifest", media_type="application/manifest+json")


@app.get("/sw.js", include_in_schema=False)
def service_worker():
    return FileResponse(FRONTEND_DIR / "sw.js", media_type="application/javascript")


@app.get("/offline.html", include_in_schema=False)
def offline_page():
    return FileResponse(FRONTEND_DIR / "offline.html", media_type="text/html")


PUBLIC_SITEMAP_STATIC_PATHS = [
    "/", "/archive", "/search", "/characters",
    "/guides", "/edit-ideas",
    "/portfolio", "/services", "/about", "/contacts", "/help", "/faq", "/project",
    "/privacy", "/terms", "/copyright",
]
# Backward-compatible snapshot constant for existing internal tests/tools.
# The actual sitemap response is built dynamically so newly discovered characters appear without restart.
PUBLIC_SITEMAP_PATHS = PUBLIC_SITEMAP_STATIC_PATHS + [
    f"/characters/{profile['slug']}" for profile in CHARACTER_PROFILES.values()
]


def _public_origin(request: Request) -> str:
    return PUBLIC_BASE_URL or str(request.base_url).rstrip("/")


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap(request: Request):
    origin = _public_origin(request)
    paths = list(PUBLIC_SITEMAP_STATIC_PATHS) + [
        f"/characters/{profile['slug']}" for profile in _available_character_catalog()
    ]
    urls = "\n".join(
        f"  <url><loc>{origin}{path}</loc></url>" for path in paths
    )
    xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}\n</urlset>\n'
    from fastapi.responses import Response
    return Response(content=xml, media_type="application/xml")


@app.get("/robots.txt", include_in_schema=False)
def robots(request: Request):
    origin = _public_origin(request)
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "Disallow: /_archive/\n"
        "Disallow: /admin\n"
        "Disallow: /login\n"
        "Disallow: /library\n"
        f"Sitemap: {origin}/sitemap.xml\n"
    )
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(body)


@app.get("/.well-known/security.txt", include_in_schema=False)
def security_txt(request: Request):
    origin = _public_origin(request)
    body = (
        f"Contact: {origin}/contacts\n"
        f"Policy: {origin}/privacy\n"
        "Expires: 2027-09-22T00:00:00Z\n"
    )
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(body, media_type="text/plain")


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404 and FRONTEND_DIR.exists() and not request.url.path.startswith("/api/"):
        return render_page(request, "pages/404.html", status_code=404)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled application error on %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse({"detail": "Внутренняя ошибка сервера."}, status_code=500)


def _production_config_errors() -> list[str]:
    if APP_ENV != "production":
        return []

    errors: list[str] = []
    required = {
        "YOUTUBE_API_KEY": os.getenv("YOUTUBE_API_KEY", "").strip(),
        "ADMIN_EMAILS": os.getenv("ADMIN_EMAILS", "").strip(),
        "PUBLIC_BASE_URL": os.getenv("PUBLIC_BASE_URL", "").strip(),
        "ALLOWED_ORIGINS": os.getenv("ALLOWED_ORIGINS", "").strip(),
    }
    for key, value in required.items():
        if not value:
            errors.append(f"{key} is not configured")

    public_url = required["PUBLIC_BASE_URL"]
    parsed_public = urlparse(public_url) if public_url else None
    if public_url and (not parsed_public or parsed_public.scheme != "https" or not parsed_public.netloc):
        errors.append("PUBLIC_BASE_URL must be an https URL in production")

    origins = [item.strip() for item in required["ALLOWED_ORIGINS"].split(",") if item.strip()]
    if not origins:
        errors.append("ALLOWED_ORIGINS must contain at least one origin in production")
    for origin in origins:
        parsed = urlparse(origin)
        if parsed.scheme != "https" or not parsed.netloc:
            errors.append(f"ALLOWED_ORIGINS contains a non-https origin: {origin}")

    generation_enabled = os.getenv("CHARACTER_IMAGE_GENERATION_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}
    if generation_enabled and not os.getenv("OPENAI_API_KEY", "").strip():
        errors.append("OPENAI_API_KEY is required while CHARACTER_IMAGE_GENERATION_ENABLED is enabled")

    if not os.getenv("CLIPFINDER_DB_PATH", "").strip():
        errors.append("CLIPFINDER_DB_PATH must be set for production persistent storage")

    # The owner must either already have an allowlisted account or provide the
    # startup bootstrap secret on first deployment. No public registration path
    # can claim an ADMIN_EMAILS address.
    if required["ADMIN_EMAILS"]:
        admin_list = [item.strip().lower() for item in required["ADMIN_EMAILS"].split(",") if item.strip()]
        connection = None
        try:
            connection = get_connection()
            if admin_list:
                placeholders = ",".join("?" for _ in admin_list)
                row = connection.execute(
                    f"SELECT 1 FROM users WHERE lower(email) IN ({placeholders}) LIMIT 1",
                    admin_list,
                ).fetchone()
                if not row and not os.getenv("ADMIN_BOOTSTRAP_PASSWORD", "").strip():
                    errors.append("No admin account exists for ADMIN_EMAILS and ADMIN_BOOTSTRAP_PASSWORD is not configured")
        except Exception:
            # Database health is checked separately below; avoid duplicating a
            # connection failure into the configuration section.
            pass
        finally:
            if connection is not None:
                connection.close()

    return errors


@app.get("/health")
def health():
    config_errors = _production_config_errors()
    if config_errors:
        return JSONResponse(
            {"status": "error", "service": "ClipFinder", "checks": config_errors},
            status_code=503,
        )
    try:
        connection = get_connection()
        try:
            connection.execute("SELECT 1").fetchone()
            connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='videos'").fetchone()
        finally:
            connection.close()
    except Exception:
        logger.exception("Health check database failure")
        return JSONResponse(
            {"status": "error", "service": "ClipFinder"},
            status_code=503,
        )
    return {"status": "ok", "service": "ClipFinder"}
