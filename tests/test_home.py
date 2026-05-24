"""Tests for Issue 1: Chat index page."""
from fastapi.testclient import TestClient
from proxy.server import app

client = TestClient(app)


def test_home_returns_html():
    """GET / should return HTML page for chat UI."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_home_contains_chat_ui():
    """The index page should contain chat interface elements."""
    response = client.get("/")
    assert "provider" in response.text.lower() or "select" in response.text.lower()
    assert "send" in response.text.lower() or "input" in response.text.lower()
