"""Tests for the health and status endpoints."""


def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "features" in body


def test_status_endpoint_available(client):
    response = client.get("/api/status")
    assert response.status_code == 200
    body = response.json()
    # The status payload should expose the overall system state.
    assert isinstance(body, dict)
    assert "status" in body
