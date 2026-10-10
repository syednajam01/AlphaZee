"""
test_reservation_unit.py — Unit tests for StockReservation model validation and constraint definitions.
"""

import uuid
import pytest

from app.models.inventory import StockReservation


def test_stock_reservation_instantiation():
    sv_id = uuid.uuid4()
    ol_id = uuid.uuid4()
    res = StockReservation(
        supplier_variant_id=sv_id,
        order_line_id=ol_id,
        quantity=3,
        stage="held",
    )
    assert res.supplier_variant_id == sv_id
    assert res.order_line_id == ol_id
    assert res.quantity == 3
    assert res.stage == "held"
    assert "qty=3" in repr(res)


def test_stock_reservation_stage_validation():
    sv_id = uuid.uuid4()
    ol_id = uuid.uuid4()
    allowed_stages = ["held", "confirmed", "dispatched", "fulfilled", "cancelled", "returned"]
    for stage in allowed_stages:
        r = StockReservation(
            supplier_variant_id=sv_id,
            order_line_id=ol_id,
            quantity=1,
            stage=stage,
        )
        assert r.stage == stage


def test_stock_reservation_stage_rejects_invalid():
    sv_id = uuid.uuid4()
    ol_id = uuid.uuid4()
    with pytest.raises(ValueError, match="Invalid reservation stage"):
        StockReservation(
            supplier_variant_id=sv_id,
            order_line_id=ol_id,
            quantity=1,
            stage="pending_payment",
        )

    with pytest.raises(ValueError, match="Invalid reservation stage"):
        StockReservation(
            supplier_variant_id=sv_id,
            order_line_id=ol_id,
            quantity=1,
            stage="HELD",
        )


def test_stock_reservation_quantity_rejects_non_positive():
    sv_id = uuid.uuid4()
    ol_id = uuid.uuid4()
    with pytest.raises(ValueError, match="Reservation quantity must be strictly positive"):
        StockReservation(
            supplier_variant_id=sv_id,
            order_line_id=ol_id,
            quantity=0,
            stage="held",
        )

    with pytest.raises(ValueError, match="Reservation quantity must be strictly positive"):
        StockReservation(
            supplier_variant_id=sv_id,
            order_line_id=ol_id,
            quantity=-2,
            stage="held",
        )
