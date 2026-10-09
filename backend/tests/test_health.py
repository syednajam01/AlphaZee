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


def test_ready_returns_200_when_db_available(client):
    resp = client.get("/api/v1/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"

