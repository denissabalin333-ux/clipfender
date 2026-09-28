from __future__ import annotations

from pathlib import Path

from backend.character_profiles import CHARACTER_PROFILES
from backend.main import FRONTEND_DIR, _available_character_catalog


ROOT = Path(__file__).resolve().parents[1]


def test_stage14_character_catalog_uses_existing_local_portraits_only():
    catalog = _available_character_catalog()
    assert len(catalog) == 7
    assert {item['slug'] for item in catalog} == {
        'jon-snow',
        'jaime-lannister',
        'daenerys-targaryen',
        'tyrion-lannister',
        'arya-stark',
        'barristan-selmy',
        'cersei-lannister',
    }
    for character in catalog:
        path = FRONTEND_DIR / character['image'].removeprefix('/static/')
        assert path.is_file(), (character['slug'], path)
        assert path.stat().st_size > 0


def test_stage14_character_page_has_busted_real_image_and_no_lazy_loading():
    html = (ROOT / 'frontend/pages/characters.html').read_text(encoding='utf-8')
    assert 'src="{{ character.image }}?v=1520"' in html
    assert 'loading="eager"' in html
    assert 'data-portrait-source="{{ character.image }}?v=1520"' in html
    assert 'stage14-portraits.js?v=141.1' in html
    assert 'stage14-portraits.css?v=141.1' in html


def test_stage14_barristan_detail_route_is_live():
    from fastapi.testclient import TestClient
    from backend.main import app

    client = TestClient(app)
    response = client.get('/characters/barristan-selmy')
    assert response.status_code == 200
    assert 'Барристан Селми' in response.text


def test_stage14_detail_page_uses_same_portrait_contract():
    html = (ROOT / 'frontend/pages/character.html').read_text(encoding='utf-8')
    assert 'stage10-workbench.css?v=141.0' in html
    assert 'src="{{ character.image }}?v=1520"' in html
    assert 'loading="eager"' in html
    assert 'data-portrait-source="{{ character.image }}?v=1520"' in html
    assert 'stage14-portraits.js?v=141.1' in html
    assert 'stage10-workbench.css?v=141.0' in html


def test_stage14_portrait_runtime_never_creates_circular_placeholder():
    js = (ROOT / 'frontend/js/stage14-portraits.js').read_text(encoding='utf-8')
    css = (ROOT / 'frontend/css/stage14-portraits.css').read_text(encoding='utf-8')
    assert 'border-radius: 50%' not in css
    assert 'ПОРТРЕТ НЕДОСТУПЕН' in js
    assert '.is-error' in css


def test_stage14_service_worker_uses_new_cache_namespace():
    sw = (ROOT / 'frontend/sw.js').read_text(encoding='utf-8')
    assert "const CACHE = 'clipfender-shell-v3';" in sw
    assert "clipfender-shell-v1" not in sw
