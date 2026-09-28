from fastapi.testclient import TestClient

from backend.main import app


def _register(client: TestClient, email: str) -> str:
    token = client.get('/api/auth/csrf').cookies.get('cf_csrf') or client.cookies.get('cf_csrf') or ''
    response = client.post(
        '/api/auth/register',
        json={'name': 'Stage Seven', 'email': email, 'password': 'StrongPassword123!'},
        headers={'X-CSRF-Token': token},
    )
    assert response.status_code == 200, response.text
    return client.cookies.get('cf_csrf') or ''


def test_public_documentation_and_seo_routes():
    with TestClient(app) as client:
        for route in ['/privacy', '/terms', '/copyright', '/robots.txt', '/sitemap.xml', '/manifest.webmanifest', '/favicon.svg', '/sw.js', '/offline.html', '/.well-known/security.txt']:
            response = client.get(route)
            assert response.status_code == 200, route
        home = client.get('/')
        assert '<link rel="canonical"' in home.text
        assert 'property="og:title"' in home.text
        assert 'application/ld+json' in home.text
        assert client.get('/login').text.find('noindex,nofollow') != -1
        sitemap = client.get('/sitemap.xml').text
        assert '/privacy</loc>' in sitemap
        assert '/api/' not in sitemap


def test_account_deletion_removes_private_library_data():
    with TestClient(app) as client:
        csrf = _register(client, 'stage7-delete@example.com')
        video = {'id': 'deleteABC12', 'title': 'Delete Me', 'url': 'https://www.youtube.com/watch?v=deleteABC12'}
        fav = client.post('/api/library/favorites', json={'video_id': video['id'], 'video': video}, headers={'X-CSRF-Token': csrf})
        assert fav.status_code == 200
        response = client.request('DELETE', '/api/auth/me', json={'password': 'StrongPassword123!'}, headers={'X-CSRF-Token': csrf})
        assert response.status_code == 200, response.text
        assert client.get('/api/auth/me').json()['authenticated'] is False
        assert client.get('/api/library/favorites').status_code == 401
