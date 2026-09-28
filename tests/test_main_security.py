from fastapi.testclient import TestClient

from backend.main import app


def test_health_checks_database_and_keeps_public_shape():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "ClipFinder"}
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "content-security-policy" in response.headers
    assert response.headers["x-frame-options"] == "SAMEORIGIN"


def test_missing_search_query_keeps_fastapi_error_shape():
    with TestClient(app) as client:
        response = client.get("/api/search")
    assert response.status_code == 422
    assert isinstance(response.json().get("detail"), list)


def test_preflight_uses_explicit_origin_and_credentials():
    with TestClient(app) as client:
        response = client.options(
            "/api/auth/login",
            headers={
                "Origin": "http://testserver",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,x-csrf-token",
            },
        )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://testserver"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_rate_limit_state_is_shared_via_sqlite():
    from backend.security import consume_rate_limit

    key = "test:shared-worker-limit"
    allowed1, retry1 = consume_rate_limit(key, 1, 60)
    allowed2, retry2 = consume_rate_limit(key, 1, 60)

    assert allowed1 is True
    assert retry1 == 0
    assert allowed2 is False
    assert retry2 >= 1
