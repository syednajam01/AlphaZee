"""
test_inventory_unit.py — Unit tests for inventory models, validators, and table constraints.

Connection-free tests verifying ORM structure, reason validation, and table args.
"""

import uuid
import pytest

from app.models.inventory import InventoryBalance, StockEvent, SupplierVariant


def test_supplier_variant_instantiation():
    sv_id = uuid.uuid4()
    s_id = uuid.uuid4()
    sv = SupplierVariant(
        id=sv_id,
        supplier_id=s_id,
        variant_id=1,
        active=True,
        supplier_cost_minor=250000,
    )
    assert sv.id == sv_id
    assert sv.supplier_id == s_id
    assert sv.variant_id == 1
    assert sv.active is True
    assert sv.supplier_cost_minor == 250000
    assert repr(sv).startswith("<SupplierVariant")


def test_inventory_balance_instantiation():
    sv_id = uuid.uuid4()
    ib = InventoryBalance(
        supplier_variant_id=sv_id,
        on_hand=15,
        version=0,
    )
    assert ib.supplier_variant_id == sv_id
    assert ib.on_hand == 15
    assert ib.version == 0
    assert "on_hand=15" in repr(ib)


def test_stock_event_reason_validates_approved_codes():
    sv_id = uuid.uuid4()
    approved_reasons = [
        "manual_count",
        "supplier_receipt",
        "reservation_fulfilled",
        "reservation_cancelled",
        "rto_return",
        "adjustment_correction",
    ]
    for reason in approved_reasons:
        event = StockEvent(
            supplier_variant_id=sv_id,
            previous_on_hand=10,
            new_on_hand=12,
            delta=2,
            reason=reason,
        )
        assert event.reason == reason


def test_stock_event_reason_rejects_invalid_values():
    sv_id = uuid.uuid4()
    with pytest.raises(ValueError, match="Invalid stock event reason"):
        StockEvent(
            supplier_variant_id=sv_id,
            previous_on_hand=10,
            new_on_hand=12,
            delta=2,
            reason="theft_or_loss",
        )

    with pytest.raises(ValueError, match="Invalid stock event reason"):
        StockEvent(
            supplier_variant_id=sv_id,
            previous_on_hand=10,
            new_on_hand=12,
            delta=2,
            reason="MANUAL_COUNT",
        )
