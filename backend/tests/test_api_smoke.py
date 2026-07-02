"""Smoke tests exercising a few real HTTP endpoints end-to-end."""


def test_phrases_endpoint_returns_list(client):
    response = client.get("/api/phrases")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)


def test_chat_rejects_empty_query(client):
    """The query validator should make an empty query fail validation (422)."""
    response = client.post(
        "/api/chat",
        json={"query": "   ", "user_id": "test-user"},
    )
    assert response.status_code == 422


def test_openapi_schema_available(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"]
