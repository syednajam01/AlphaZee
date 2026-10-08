"""
Tests for health and readiness endpoints.
"""

from __future__ import annotations


def test_health_returns_200(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_ready_returns_200_when_db_available(client):
    resp = client.get("/api/v1/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"


def test_health_does_not_expose_credentials(client):
    body = client.get("/api/v1/health").text
    assert "postgresql" not in body
    assert "password" not in body
    assert "changeme" not in body
