from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_returns_standard_envelope():
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers

    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"
    assert body["error"] is None
    assert body["meta"]["request_id"] == response.headers["X-Request-ID"]


def test_correlation_id_is_echoed_when_provided():
    response = client.get("/api/v1/health", headers={"X-Request-ID": "test-correlation-id"})

    assert response.headers["X-Request-ID"] == "test-correlation-id"
    assert response.json()["meta"]["request_id"] == "test-correlation-id"


def test_not_found_returns_standard_error_model():
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"]["code"] == "NOT_FOUND"
