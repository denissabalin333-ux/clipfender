from __future__ import annotations

from fastapi.testclient import TestClient

from backend.character_profiles import CHARACTER_PROFILES
from backend.main import app, PUBLIC_SITEMAP_PATHS


def test_all_character_profiles_have_required_fields():
    assert len(CHARACTER_PROFILES) == 7
    for slug, profile in CHARACTER_PROFILES.items():
        assert profile["slug"] == slug
        assert profile["name"]
        assert profile["query"]
        assert profile["image"].startswith("/static/")
        assert len(profile["lore"]) >= 2
        assert len(profile["edit_profile"]) >= 3


def test_character_routes_render_for_all_profiles():
    with TestClient(app) as client:
        for slug, profile in CHARACTER_PROFILES.items():
            response = client.get(f"/characters/{slug}")
            assert response.status_code == 200
            body = response.text
            assert profile["name"] in body
            assert profile["query"] in body
            assert f"/characters/{slug}" in body


def test_unknown_character_is_404():
    with TestClient(app) as client:
        response = client.get("/characters/not-a-real-character")
        assert response.status_code == 404


def test_character_pages_are_in_sitemap():
    for slug in CHARACTER_PROFILES:
        assert f"/characters/{slug}" in PUBLIC_SITEMAP_PATHS


def test_edit_ideas_page_contains_stage10_workbench_assets():
    with TestClient(app) as client:
        response = client.get("/edit-ideas")
        assert response.status_code == 200
        assert "/static/css/stage10-workbench.css" in response.text
        assert "/static/js/stage10-workbench.js" in response.text


def test_character_index_contains_profile_links():
    with TestClient(app) as client:
        response = client.get("/characters")
        assert response.status_code == 200
        for slug in CHARACTER_PROFILES:
            assert f"/characters/{slug}" in response.text



def test_search_page_has_stage10_idea_controls():
    with TestClient(app) as client:
        response = client.get('/search?mode=idea')
        assert response.status_code == 200
        body = response.text
        assert 'id="cf8Genre"' in body
        assert 'id="cf8Character"' in body
        assert 'id="cf8RandomIdea"' in body
        assert 'СКАЧАТЬ РАСКАДРОВКУ' not in body


def test_edit_idea_accepts_genre_and_character_without_live_call(monkeypatch):
    import backend.api.edit_idea as edit_idea_module

    def fake_load_candidates(query, film, genre='', character='', limit=180):
        return [
            {
                'id': f'v{i}',
                'title': f'Jon Snow battle scene {i}',
                'channel': 'Test Channel',
                'url': f'https://www.youtube.com/watch?v=v{i}',
                'thumbnail': '',
                'duration': '0:30',
                'edit_score': 50,
                'edit_suitability_score': 80,
                'score_estimated': False,
                'score_version': 'test',
                'is_action': True,
                'is_dynamic': True,
                'is_cinematic': True,
                'is_clean': True,
                'has_dialogue': False,
                'is_raw_footage': False,
                'is_4k': False,
                'is_hd': True,
                'has_music': False,
                'has_voice': True,
                'has_dialogue': False,
                'description': '',
            }
            for i in range(16)
        ]

    monkeypatch.setattr(edit_idea_module, '_load_candidates', fake_load_candidates)
    monkeypatch.setattr(edit_idea_module, '_check_public_rate_limit', lambda request: None)
    with TestClient(app) as client:
        response = client.get('/api/edit-idea?film=Game%20of%20Thrones&character=Jon%20Snow&genre=action&query=battle')
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'
    assert data['genre'] == 'action'
    assert data['character'] == 'Jon Snow'
    assert any('жанр' in item['why'] or 'персонаж' in item['why'] for stage in data['stages'] for item in stage['items'])


def test_edit_idea_live_fallback_searches_and_caches(monkeypatch):
    import backend.api.edit_idea as edit_idea_module

    state = {'calls': 0, 'saved': None}

    monkeypatch.setattr(edit_idea_module, '_check_public_rate_limit', lambda request: None)
    monkeypatch.setattr(edit_idea_module, '_load_candidates', lambda *args, **kwargs: [] if state['calls'] == 0 else [
        {
            'id': 'live1', 'title': 'Jon Snow battle', 'channel': 'YouTube', 'url': 'https://youtube.com/watch?v=live1',
            'thumbnail': '', 'duration': '0:40', 'edit_score': 60, 'edit_suitability_score': 82,
            'score_estimated': False, 'score_version': 'test', 'is_action': True, 'is_dynamic': True,
            'is_cinematic': True, 'is_clean': True, 'has_dialogue': False, 'is_raw_footage': False,
            'is_4k': False, 'is_hd': True,
        }
        for _ in range(12)
    ])
    state['calls'] = 0

    monkeypatch.setattr(edit_idea_module, '_reserve_search_quota', lambda: {'allowed': True, 'remaining': 68})
    monkeypatch.setattr(edit_idea_module, 'search_youtube', lambda *args, **kwargs: ([
        {'id': 'live1', 'title': 'Jon Snow battle', 'channel': 'YouTube', 'url': 'https://youtube.com/watch?v=live1',
         'thumbnail': '', 'views': 10, 'duration': '0:40', 'description': '', 'is_action': True, 'is_dynamic': True,
         'is_cinematic': True, 'is_clean': True, 'has_dialogue': False, 'is_raw_footage': False,
         'is_4k': False, 'is_hd': True}
    ], 1, 'next'))
    monkeypatch.setattr(edit_idea_module, 'save_videos', lambda videos, key: state.update(saved=(videos, key)))
    monkeypatch.setattr(edit_idea_module, 'save_search_state', lambda *args: None)
    monkeypatch.setattr(edit_idea_module, '_soft_edit_pool', lambda videos: videos)
    monkeypatch.setattr(edit_idea_module, 'remove_duplicates', lambda videos: videos)
    monkeypatch.setattr(edit_idea_module, 'sort_videos', lambda videos, *args, **kwargs: videos)
    monkeypatch.setattr(edit_idea_module, 'calculate_score', lambda **kwargs: 10)
    monkeypatch.setattr(edit_idea_module, 'calculate_edit_score', lambda video, query: 60)
    import backend.api.edit_idea as module
    original = module._load_candidates
    def staged_loader(*args, **kwargs):
        if state['calls'] == 0:
            state['calls'] = 1
            return []
        return [
            {
                'id': 'live1', 'title': 'Jon Snow battle', 'channel': 'YouTube', 'url': 'https://youtube.com/watch?v=live1',
                'thumbnail': '', 'duration': '0:40', 'edit_score': 60, 'edit_suitability_score': 82,
                'score_estimated': False, 'score_version': 'test', 'is_action': True, 'is_dynamic': True,
                'is_cinematic': True, 'is_clean': True, 'has_dialogue': False, 'is_raw_footage': False,
                'is_4k': False, 'is_hd': True, 'description': '',
            }
            for _ in range(12)
        ]
    monkeypatch.setattr(module, '_load_candidates', staged_loader)

    with TestClient(app) as client:
        response = client.get('/api/edit-idea?film=Game%20of%20Thrones&character=Jon%20Snow&genre=action')
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'
    assert data['material_search']['performed'] is True
    assert data['material_search']['source'] == 'youtube'
    assert state['saved'] and state['saved'][1].startswith('clipfinder_shared:')



def test_edit_idea_ignores_unrelated_recent_rows():
    import backend.api.edit_idea as module

    recent = [{
        'id': 'unrelated', 'title': 'Completely unrelated material', 'channel': 'Test',
        'url': 'https://youtube.com/watch?v=unrelated', 'thumbnail': '', 'duration': '0:30',
        'query': 'Some Other Character', 'description': '', 'is_action': False, 'is_dynamic': False,
        'is_cinematic': False, 'is_clean': True, 'is_hd': True, 'is_4k': False,
    }]
    monkeypatch = None

    class FakeCursor:
        def execute(self, *args, **kwargs): return self
        def fetchall(self): return recent
    class FakeConnection:
        def cursor(self): return FakeCursor()
        def close(self): pass

    original_get_cached = module.get_cached_videos
    original_connect = module.sqlite3.connect
    try:
        module.get_cached_videos = lambda key: []
        module.sqlite3.connect = lambda *args, **kwargs: FakeConnection()
        candidates = module._load_candidates('', 'Game of Thrones', 'action', 'Jon Snow')
    finally:
        module.get_cached_videos = original_get_cached
        module.sqlite3.connect = original_connect

    assert candidates == []
