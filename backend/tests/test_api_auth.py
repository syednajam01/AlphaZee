"""
test_api_auth.py — Authentication gate tests for Admin API endpoints.

Reproduces Blocker 1:
- Admin API endpoints must reject anonymous requests with 401 Unauthorized.
- Admin API endpoints must reject invalid credentials with 401 Unauthorized.
- Legacy X-Admin-Key and Authorization credentials must not bypass owner sessions.
- Public storefront catalog & health endpoints must remain accessible without auth.
"""

from __future__ import annotations

import pytest
from app.config import settings


def test_anonymous_admin_requests_rejected(client):
    """
    Reproduces Blocker 1: Privileged admin endpoints must refuse anonymous requests.
    """
    # 1. Overview metrics
    res = client.get("/api/v1/admin/overview")
    assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"

    # 2. Inventory summary
    res = client.get("/api/v1/admin/inventory/summary")
    assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"

    # 3. Physical stock adjustment
    res = client.post("/api/v1/admin/inventory/adjust", json={"supplier_variant_id": "none", "quantity_delta": 1, "expected_version": 1, "reason": "manual_count"})
    assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"

    # 4. Orders listing
    res = client.get("/api/v1/admin/orders")
    assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"

    # 5. Suppliers listing
    res = client.get("/api/v1/admin/suppliers")
    assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"

    # 6. Analytics profit-loss
    res = client.get("/api/v1/admin/analytics/profit-loss")
    assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"

    # 7. Coupons listing
    res = client.get("/api/v1/admin/coupons")
    assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"

    # 8. Returns listing
    res = client.get("/api/v1/admin/returns")
    assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"


def test_invalid_admin_key_rejected(client):
    """
    Submitting an invalid secret via X-Admin-Key or Bearer must return 401.
    """
    # Bad X-Admin-Key
    res = client.get("/api/v1/admin/overview", headers={"X-Admin-Key": "wrong-secret-token"})
    assert res.status_code == 401
    assert "Invalid or missing" in res.json().get("detail", "")

    # Bad Bearer token
    res = client.get("/api/v1/admin/overview", headers={"Authorization": "Bearer wrong-token"})
    assert res.status_code == 401
    assert "Invalid or missing" in res.json().get("detail", "")


def test_legacy_admin_key_rejected(client):
    """
    Valid key passed via X-Admin-Key or Authorization Bearer header must be rejected.
    """
    expected_key = getattr(settings, "admin_api_key", "alphazee-dev-admin-key-change-in-prod")

    # Valid via X-Admin-Key
    res = client.get("/api/v1/admin/overview", headers={"X-Admin-Key": expected_key})
    assert res.status_code == 401

    # Valid via Authorization: Bearer
    res = client.get("/api/v1/admin/overview", headers={"Authorization": f"Bearer {expected_key}"})
    assert res.status_code == 401


def test_public_storefront_endpoints_remain_accessible(client):
    """
    Public catalog and health routes must not be locked by admin authentication.
    """
    res = client.get("/api/v1/health")
    assert res.status_code == 200

    res = client.get("/api/v1/products")
    assert res.status_code == 200
