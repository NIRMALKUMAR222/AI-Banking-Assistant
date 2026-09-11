"""
tests/conftest.py - Shared pytest fixtures for SecureBank tests.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import get_settings

settings = get_settings()
API_KEY  = settings.api_key
HEADERS  = {"X-API-Key": API_KEY}


@pytest.fixture(scope="session")
def client():
    """HTTP test client shared across all test modules."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def auth_headers(client):
    """Log in as alice and return JWT Authorization headers."""
    resp = client.post("/auth/login", json={"username": "alice", "password": "alice123"})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def api_key_headers():
    return HEADERS