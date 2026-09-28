from __future__ import annotations

import json
from fastapi.testclient import TestClient

from backend.main import app


def _csrf(client: TestClient) -> str:
    response = client.get('/api/auth/csrf')
    assert response.status_code == 200
    return client.cookies.get('cf_csrf') or ''


def _register(client: TestClient, email: str = 'stage6@example.com'):
    token = _csrf(client)
    response = client.post(
        '/api/auth/register',
        json={'name': 'Stage Six', 'email': email, 'password': 'StrongPassword123!'},
        headers={'X-CSRF-Token': token},
    )
    assert response.status_code == 200, response.text
    return client.cookies.get('cf_csrf') or ''


def test_library_requires_authentication():
    with TestClient(app) as client:
        assert client.get('/api/library/favorites').status_code == 401
        assert client.get('/api/library/collections').status_code == 401
        assert client.get('/api/library/history').status_code == 401
        assert client.get('/library').status_code == 200


def test_favorites_collections_history_filters_and_exports():
    with TestClient(app) as client:
        token = _register(client, 'stage6-library@example.com')
        video = {
            'id': 'abcDEF12345',
            'title': 'Stage Six Clip',
            'channel': 'ClipFender',
            'url': 'https://www.youtube.com/watch?v=abcDEF12345',
            'duration': '00:21',
            'edit_score': 87,
            'score': 91,
            'views': 1234,
        }

        fav = client.post('/api/library/favorites', json={'video_id': video['id'], 'video': video}, headers={'X-CSRF-Token': token})
        assert fav.status_code == 200, fav.text
        assert client.get('/api/library/favorites').json()['items'][0]['video']['title'] == 'Stage Six Clip'

        create = client.post('/api/library/collections', json={'name': 'Final Battle', 'description': 'Reference pack'}, headers={'X-CSRF-Token': token})
        assert create.status_code == 200, create.text
        collection_id = create.json()['id']

        add = client.post(f'/api/library/collections/{collection_id}/items', json={'video_id': video['id'], 'video': video}, headers={'X-CSRF-Token': token})
        assert add.status_code == 200, add.text
        detail = client.get(f'/api/library/collections/{collection_id}').json()
        assert detail['items'][0]['video']['id'] == video['id']

        history = client.post('/api/library/history', json={'query': 'Jon Snow', 'params': {'q': 'Jon Snow', 'sort': 'score'}}, headers={'X-CSRF-Token': token})
        assert history.status_code == 200, history.text
        assert client.get('/api/library/history').json()['items'][0]['query'] == 'Jon Snow'

        saved = client.post('/api/library/filters', json={'name': 'Battle 75+', 'query': 'battle', 'filters': {'editMinScore': '75', 'sort': 'score'}}, headers={'X-CSRF-Token': token})
        assert saved.status_code == 200, saved.text
        filters = client.get('/api/library/filters').json()['items']
        assert filters[0]['filters']['editMinScore'] == '75'

        for export_format, content_type in [('json', 'application/json'), ('csv', 'text/csv'), ('markdown', 'text/markdown')]:
            response = client.get(f'/api/library/export?format={export_format}')
            assert response.status_code == 200, response.text
            assert response.headers['content-type'].startswith(content_type)
            assert 'attachment' in response.headers['content-disposition']

        # Deleting a favorite does not delete an independent collection item.
        delete = client.delete(f"/api/library/favorites/{video['id']}", headers={'X-CSRF-Token': token})
        assert delete.status_code == 200
        assert client.get('/api/library/favorites').json()['items'] == []
        assert client.get(f'/api/library/collections/{collection_id}').json()['items'][0]['video']['id'] == video['id']


def test_library_csrf_and_invalid_export_format():
    with TestClient(app) as client:
        token = _register(client, 'stage6-security@example.com')
        response = client.post('/api/library/history', json={'query': 'bad'}, headers={'X-CSRF-Token': 'wrong'})
        assert response.status_code == 403
        response = client.get('/api/library/export?format=xml')
        assert response.status_code == 422


def test_stage6_public_pages_and_assets_render():
    routes = [
        '/', '/archive', '/character-search', '/guides', '/edit-ideas', '/video',
        '/portfolio', '/services', '/about', '/contacts', '/characters', '/help',
        '/faq', '/project', '/login', '/library',
    ]
    with TestClient(app) as client:
        for route in routes:
            response = client.get(route)
            assert response.status_code == 200, (route, response.text[:200])
            assert '<html' in response.text.lower()
        for asset in ['/static/css/pages/library.css', '/static/js/stage6-library.js']:
            response = client.get(asset)
            assert response.status_code == 200, asset

