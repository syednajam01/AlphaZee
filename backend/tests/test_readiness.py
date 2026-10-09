"""
Tests for liveness and readiness diagnostic endpoints under various conditions.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.database import get_db
from app.main import app


def test_health_probe_always_ok():
    """Verify liveness probe returns 200 without database interaction."""
    with TestClient(app) as client:
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
        assert "postgresql" not in resp.text
        assert "password" not in resp.text


def test_ready_probe_success():
    """Verify readiness probe returns 200 when database executes SELECT 1 successfully."""
    mock_db = MagicMock()
    mock_db.execute.return_value = None

    def override_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            resp = client.get("/api/v1/ready")
            assert resp.status_code == 200
            assert resp.json() == {"status": "ready", "database": "connected"}
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_ready_probe_database_unavailable_returns_503_without_leaks():
    """Verify readiness probe returns 503 and hides credentials when database fails."""
    mock_db = MagicMock()
    mock_db.execute.side_effect = OperationalError(
        "could not connect to server: Connection refused",
        params=None,
        orig=Exception("internal connection failed with user alphazee and password secret"),
    )

    def override_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            resp = client.get("/api/v1/ready")
            assert resp.status_code == 503
            assert resp.json() == {"detail": "Database unavailable"}
            # Ensure no credentials or raw exception messages leak
            assert "secret" not in resp.text
            assert "alphazee" not in resp.text
            assert "OperationalError" not in resp.text
    finally:
        app.dependency_overrides.pop(get_db, None)
