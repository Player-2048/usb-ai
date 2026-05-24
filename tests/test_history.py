"""Tests for Issue 2: History search API."""
from fastapi.testclient import TestClient
from proxy.server import app

client = TestClient(app)


def test_history_recent_returns_list():
    """GET /v1/history/recent should return a results list."""
    response = client.get("/v1/history/recent?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert isinstance(data["results"], list)


def test_history_search_accepts_query():
    """GET /v1/history?query=... should not crash."""
    response = client.get("/v1/history?query=test&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data


def test_history_no_query_returns_recent():
    """GET /v1/history without query should fallback to recent."""
    response = client.get("/v1/history")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
