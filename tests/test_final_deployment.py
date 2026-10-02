from __future__ import annotations

from pathlib import Path


def test_render_free_uses_turso_without_persistent_disk():
    render = Path("render.yaml").read_text(encoding="utf-8")
    assert "plan: free" in render
    assert "disk:" not in render
    assert "mountPath:" not in render
    assert "TURSO_DATABASE_URL" in render
    assert "TURSO_AUTH_TOKEN" in render


def test_bing_image_search_is_disabled():
    source = Path("backend/services/character_catalog.py").read_text(encoding="utf-8")
    env = Path(".env.example").read_text(encoding="utf-8")
    assert "IMAGE_SEARCH_ENABLED = False" in source
    assert "CHARACTER_IMAGE_SEARCH_ENABLED=0" in env


def test_env_is_loaded_before_sensitive_modules():
    main = Path("backend/main.py").read_text(encoding="utf-8")
    assert "from backend.config import APP_ENV, BASE_DIR" in main
    assert "load_dotenv" not in main


def test_dynamic_portrait_media_route_is_present():
    main = Path("backend/main.py").read_text(encoding="utf-8")
    assert '@app.get("/media/characters/{filename}"' in main
    assert 'media_type="image/webp"' in main
    assert 'max-age=86400' in main
    assert 'PUBLIC_SITEMAP_STATIC_PATHS' in main


def test_render_bootstrap_secret_is_declared():
    render = Path("render.yaml").read_text(encoding="utf-8")
    assert "ADMIN_BOOTSTRAP_PASSWORD" in render
    assert "sync: false" in render


def test_character_discovery_endpoint_requires_csrf():
    source = Path("backend/api/characters.py").read_text(encoding="utf-8")
    assert "require_csrf(request)" in source


def test_dynamic_portrait_storage_is_not_inside_render_persistent_disk():
    source = Path("backend/services/character_catalog.py").read_text(encoding="utf-8")
    assert 'DEFAULT_CHARACTER_STORAGE = BASE_DIR / "data" / "characters"' in source
    assert 'Path("/var/lib/clipfender/characters")' not in source
    assert "REMOTE_DATABASE_ENABLED" in source


def test_dynamic_sitemap_is_built_per_request():
    main = Path("backend/main.py").read_text(encoding="utf-8")
    assert "paths = list(PUBLIC_SITEMAP_STATIC_PATHS)" in main


def test_proxy_ip_and_https_helpers_are_explicit():
    security = Path("backend/security.py").read_text(encoding="utf-8")
    assert "x-forwarded-for" in security
    assert "x-forwarded-proto" in security
