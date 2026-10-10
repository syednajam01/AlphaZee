"""
test_api_coupons.py — Integration and API tests for promotional discount vouchers and coupon validation.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.promotions import Coupon
from app.services.promotions import create_coupon, validate_coupon


def test_create_and_validate_percentage_coupon(db_session: Session):
    coupon = create_coupon(
        db_session,
        code="SAVE10",
        discount_type="percentage",
        discount_value=10,
        min_subtotal_minor=100000,  # Min PKR 1,000
        max_discount_minor=50000,   # Max PKR 500
    )
    db_session.flush()

    assert coupon.code == "SAVE10"
    assert coupon.discount_type == "percentage"

    # Below min subtotal -> should fail
    with pytest.raises(ValueError, match="Minimum order subtotal"):
        validate_coupon(db_session, code="save10", subtotal_minor=80000)

    # Valid: PKR 2,000 subtotal (200,000 paisas) -> 10% is 20,000 paisas
    res = validate_coupon(db_session, code="SAVE10", subtotal_minor=200000)
    assert res.valid is True
    assert res.discount_amount_minor == 20000

    # Capped: PKR 10,000 subtotal (1,000,000 paisas) -> 10% is 100,000, but capped at 50,000 paisas
    res_capped = validate_coupon(db_session, code="SAVE10", subtotal_minor=1000000)
    assert res_capped.discount_amount_minor == 50000


def test_fixed_and_free_shipping_coupons(db_session: Session):
    create_coupon(
        db_session,
        code="FLAT200",
        discount_type="fixed_amount",
        discount_value=20000,  # PKR 200
        min_subtotal_minor=50000,
    )
    create_coupon(
        db_session,
        code="FREESHIP",
        discount_type="free_shipping",
        discount_value=0,
    )
    db_session.flush()

    res_fixed = validate_coupon(db_session, code="flat200", subtotal_minor=100000)
    assert res_fixed.discount_amount_minor == 20000

    res_ship = validate_coupon(db_session, code="FREESHIP", subtotal_minor=50000, shipping_fee_minor=25000)
    assert res_ship.is_free_shipping is True
    assert res_ship.discount_amount_minor == 25000


def test_coupon_api_endpoints(client: TestClient, db_session: Session):
    # 1. Admin creates coupon
    create_res = client.post(
        "/api/v1/admin/coupons",
        json={
            "code": "LAUNCH20",
            "discount_type": "percentage",
            "discount_value": 20,
            "min_subtotal_minor": 100000,
        },
    )
    assert create_res.status_code == 201
    created_id = create_res.json()["id"]

    # 2. Storefront validates coupon
    val_res = client.post(
        "/api/v1/coupons/validate",
        json={
            "code": "LAUNCH20",
            "subtotal_minor": 200000,
            "shipping_fee_minor": 20000,
        },
    )
    assert val_res.status_code == 200
    data = val_res.json()
    assert data["valid"] is True
    assert data["discount_amount"]["minor"] == 40000  # 20% of 200,000

    # 3. Invalid coupon validation
    val_bad = client.post(
        "/api/v1/coupons/validate",
        json={
            "code": "NONEXISTENT",
            "subtotal_minor": 200000,
        },
    )
    assert val_bad.status_code == 400

    # 4. Admin lists coupons
    list_res = client.get("/api/v1/admin/coupons")
    assert list_res.status_code == 200
    assert any(c["code"] == "LAUNCH20" for c in list_res.json())

    # 5. Admin deletes coupon
    del_res = client.delete(f"/api/v1/admin/coupons/{created_id}")
    assert del_res.status_code == 204
