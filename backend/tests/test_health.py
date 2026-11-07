"""
Tests for health and readiness endpoints.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def standalone_client():
    """Client for liveness checks that requires no database connection."""
    with TestClient(app) as c:
        yield c


def test_health_returns_200(standalone_client):
    resp = standalone_client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_health_does_not_expose_credentials(standalone_client):
    body = standalone_client.get("/api/v1/health").text
    assert "postgresql" not in body
    assert "password" not in body
    assert "changeme" not in body


def test_release_returns_only_build_revision(standalone_client, monkeypatch):
    monkeypatch.setenv('RELEASE_SHA', 'a' * 40)
    response = standalone_client.get('/api/v1/release')
    assert response.json() == {'sha': 'a' * 40}
    assert response.headers['Cache-Control'] == 'no-store'
    monkeypatch.delenv('RELEASE_SHA')
    assert standalone_client.get('/api/v1/release').json() == {'sha': 'development'}


def test_ready_returns_200_when_db_available(client):
    resp = client.get("/api/v1/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"

