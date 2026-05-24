"""Tests for Settings page, Export endpoint."""
from fastapi.testclient import TestClient
from proxy.server import app

client = TestClient(app)


def test_settings_page_returns_html():
    response = client.get("/settings")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_settings_contains_providers():
    response = client.get("/settings")
    assert "DeepSeek" in response.text or "OpenAI" in response.text or "Claude" in response.text


def test_export_returns_zip():
    response = client.get("/v1/export")
    assert response.status_code == 200
    assert "application/zip" in response.headers["content-type"] or "octet-stream" in response.headers["content-type"]
