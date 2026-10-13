"""
test_rto_restock.py — Defect reproduction and verification tests for Blocker 5:
Safe RTO restocking (decoupled from parcel arrival, requiring physical condition inspection),
audit delta guarantee, and customer returns restocking fulfilling supplier instead of active supplier.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from app.models.catalog import AvailabilityStatus, Collection, Product, Variant
from app.models.inventory import InventoryBalance, StockEvent, StockReservation, SupplierVariant
from app.models.orders import Order, OrderLine
from app.models.returns import OrderReturn
from app.models.shipments import Shipment
from app.models.suppliers import Supplier
from app.queries.reservations import get_inventory_summary
from app.services.orders import (
    CreateOrderDTO,
    OrderItemDTO,
    confirm_supplier_acceptance,
    deliver_order,
    place_order,
)
from app.services.returns import (
    approve_return_request,
    complete_return_and_restock,
    create_return_request,
)
from app.services.shipments import (
    create_shipment,
    initiate_rto_order,
    inspect_and_restock_order,
    receive_rto_parcel,
)


def _setup_catalog(db: Session, on_hand: int = 10):
    uid = uuid.uuid4().hex[:6]
    col = Collection(
        id=f"col-{uid}",
        slug=f"col-{uid}",
        name="RTO Test Collection",
        is_active=True,
        display_order=0,
    )
    db.add(col)
    db.flush()

    prod = Product(
        id=f"prod-{uid}",
        slug=f"prod-{uid}",
        title="RTO Restock Test Item",
        collection_id=col.id,
        is_active=True,
    )
    db.add(prod)
    db.flush()

    var = Variant(
        sku=f"SKU-RTO-{uid}",
        product_id=prod.id,
        size="XL",
        color="Navy",
        price_minor=500000,
        is_active=True,
        availability=AvailabilityStatus.AVAILABLE,
    )
    db.add(var)
    db.flush()

    sup_a = Supplier(
        name="Vendor Original",
        slug=f"vendor-orig-{uid}",
        status="active",
    )
    db.add(sup_a)
    db.flush()

    sv_a = SupplierVariant(
        supplier_id=sup_a.id,
        variant_id=var.id,
        active=True,
        supplier_cost_minor=300000,
    )
    db.add(sv_a)
    db.flush()

    ib_a = InventoryBalance(
        supplier_variant_id=sv_a.id,
        on_hand=on_hand,
        version=0,
    )
    db.add(ib_a)
    db.flush()

    return {
        "collection": col,
        "product": prod,
        "variant": var,
        "supplier_a": sup_a,
        "sv_a": sv_a,
        "balance_a": ib_a,
    }


def _create_dispatched_order(db: Session, cat: dict, qty: int = 2) -> tuple[Order, Shipment]:
    var = cat["variant"]
    dto = CreateOrderDTO(
        customer_name="Babar Azam",
        customer_phone="03009876543",
        customer_email="babar@example.com",
        shipping_address_line1="Gulberg III, Main Blvd",
        shipping_city="Lahore",
        shipping_province="Punjab",
        payment_method="cod",
        items=[
            OrderItemDTO(
                variant_id=var.id,
                quantity=qty,
            )
        ],
    )
    order = place_order(db, order_data=dto)
    confirm_supplier_acceptance(db, order_id=order.id, supplier_notes="Accepted")
    shipment = create_shipment(
        db,
        order_id=order.id,
        courier_code="trax",
        tracking_number=f"TRX-{uuid.uuid4().hex[:8]}",
        shipping_cost_minor=25000,
    )
    db.flush()
    return order, shipment


class TestSafeRtoRestockingAndReturnSupplier:
    """Blocker 5 reproduction and verification test suite."""

    def test_rto_received_does_not_automatically_restock(self, db_session: Session, admin_client: TestClient):
        """
        Defect 1: Auto-restock on rto-received was unsafe.
        When a returned parcel arrives back at the warehouse (rto_received),
        physical on_hand must NOT automatically increment until the items are inspected.
        """
        cat = _setup_catalog(db_session, on_hand=10)
        sv_a = cat["sv_a"]
        order, shipment = _create_dispatched_order(db_session, cat, qty=2)
        db_session.commit()

        # Initiate RTO
        initiate_rto_order(db_session, order_id=order.id, rto_reason="Customer unreachable")
        db_session.commit()

        # Parcel arrives at shop
        resp = admin_client.post(f"/api/v1/admin/orders/{order.id}/rto-received",
            json={"lines": [{"order_line_id": str(order.lines[0].id), "received_quantity": 2}]})
        assert resp.status_code == 200

        db_session.refresh(shipment)
        assert shipment.status == "rto_delivered"
        # In Blocker 5, physical restocking has NOT occurred yet:
        assert shipment.rto_restocked_at is None

        # Dispatch already deducted stock; receipt adds none.
        bal = db_session.get(InventoryBalance, sv_a.id)
        assert bal.on_hand == 8

        # No rto_return StockEvent should exist yet
        events = db_session.scalars(
            select(StockEvent).where(
                StockEvent.supplier_variant_id == sv_a.id,
                StockEvent.reason == "rto_return",
            )
        ).all()
        assert len(events) == 0

    def test_inspect_and_restock_condition_ok_increases_stock_with_audit(
        self, db_session: Session, admin_client: TestClient
    ):
        """
        Inspection Pass: When the owner confirms the item is in good, resalable condition,
        physical stock increases and a StockEvent with positive delta is recorded.
        """
        cat = _setup_catalog(db_session, on_hand=10)
        sv_a = cat["sv_a"]
        order, shipment = _create_dispatched_order(db_session, cat, qty=2)
        db_session.commit()

        # Deliver order first so physical stock decrements from 10 to 8
        deliver_order(db_session, order_id=order.id)
        bal_after_deliv = db_session.get(InventoryBalance, sv_a.id)
        assert bal_after_deliv.on_hand == 8

        # Parcel returned via RTO
        initiate_rto_order(db_session, order_id=order.id, rto_reason="Doorstep return")
        receive_rto_parcel(db_session, order_id=order.id,
                           received_quantities={order.lines[0].id: 2})
        db_session.commit()

        # Physical on_hand is still 8 before inspection
        db_session.refresh(bal_after_deliv)
        assert bal_after_deliv.on_hand == 8

        # Owner inspects: condition is OK
        resp = admin_client.post(
            f"/api/v1/admin/orders/{order.id}/rto-inspect",
            json={"lines": [{"order_line_id": str(order.lines[0].id),
                              "sellable_quantity": 2, "damaged_quantity": 0}],
                  "notes": "Packaging sealed and pristine"},
        )
        assert resp.status_code == 200

        db_session.refresh(shipment)
        assert shipment.rto_restocked_at is not None

        # Physical on_hand restored to 10
        db_session.refresh(bal_after_deliv)
        assert bal_after_deliv.on_hand == 10

        # Audit event appended with positive delta = +2 and reason='rto_return'
        event = db_session.scalars(
            select(StockEvent)
            .where(
                StockEvent.supplier_variant_id == sv_a.id,
                StockEvent.reason == "rto_return",
            )
            .order_by(StockEvent.occurred_at.desc())
        ).first()
        assert event is not None
        assert event.delta == 2
        assert event.previous_on_hand == 8
        assert event.new_on_hand == 10

    def test_inspect_and_restock_damaged_condition_does_not_restock(
        self, db_session: Session, admin_client: TestClient
    ):
        """
        Inspection Fail: When item is damaged, soiled, or unsellable, physical stock is NOT restocked.
        Rejection note is saved.
        """
        cat = _setup_catalog(db_session, on_hand=10)
        sv_a = cat["sv_a"]
        order, shipment = _create_dispatched_order(db_session, cat, qty=2)
        deliver_order(db_session, order_id=order.id)
        bal = db_session.get(InventoryBalance, sv_a.id)
        assert bal.on_hand == 8

        initiate_rto_order(db_session, order_id=order.id, rto_reason="Doorstep refusal")
        receive_rto_parcel(db_session, order_id=order.id,
                           received_quantities={order.lines[0].id: 2})
        db_session.commit()

        # Owner inspects: condition failed
        resp = admin_client.post(
            f"/api/v1/admin/orders/{order.id}/rto-inspect",
            json={"lines": [{"order_line_id": str(order.lines[0].id),
                              "sellable_quantity": 0, "damaged_quantity": 2}],
                  "notes": "Item torn by courier during transit"},
        )
        assert resp.status_code == 200

        db_session.refresh(shipment)
        # Inspection closed the disposition without restocking damaged units.
        assert shipment.rto_restocked_at is not None

        # Physical on_hand remains 8
        db_session.refresh(bal)
        assert bal.on_hand == 8

        # No rto_return StockEvent appended
        events = db_session.scalars(
            select(StockEvent).where(
                StockEvent.supplier_variant_id == sv_a.id,
                StockEvent.reason == "rto_return",
            )
        ).all()
        assert len(events) == 0

    def test_customer_return_restocks_fulfilling_supplier_not_new_active_supplier(
        self, db_session: Session
    ):
        """
        Defect 2: Customer returns restock active supplier instead of fulfilling supplier.
        Order was fulfilled by Supplier A. Store subsequently changes active vendor to Supplier B.
        When customer return is completed, Supplier A must be credited, NOT Supplier B.
        """
        cat = _setup_catalog(db_session, on_hand=10)
        var = cat["variant"]
        sv_a = cat["sv_a"]

        order, _ = _create_dispatched_order(db_session, cat, qty=3)
        deliver_order(db_session, order_id=order.id)

        bal_a = db_session.get(InventoryBalance, sv_a.id)
        assert bal_a.on_hand == 7

        # Now configure Supplier B as the new active supplier for this variant
        uid = uuid.uuid4().hex[:6]
        sup_b = Supplier(
            name="Vendor Replacement",
            slug=f"vendor-repl-{uid}",
            status="active",
        )
        db_session.add(sup_b)
        db_session.flush()

        sv_a.active = False
        sv_b = SupplierVariant(
            supplier_id=sup_b.id,
            variant_id=var.id,
            active=True,
            supplier_cost_minor=280000,
        )
        db_session.add(sv_b)
        db_session.flush()

        bal_b = InventoryBalance(
            supplier_variant_id=sv_b.id,
            on_hand=5,
            version=0,
        )
        db_session.add(bal_b)
        db_session.flush()

        # Customer requests return on order line
        line = order.lines[0]
        return_obj = create_return_request(
            db_session,
            order_id=order.id,
            order_line_id=line.id,
            return_type="refund_bank_transfer",
            reason="damaged_defective",
            customer_notes="Wrong size received",
            quantity=3,
        )
        approve_return_request(db_session, return_id=return_obj.id)

        # Receipt is quarantined; inspection restores only accepted units.
        from app.services.returns import receive_return_items, inspect_return_items
        receive_return_items(db_session, return_id=return_obj.id, received_quantity=3)
        inspect_return_items(db_session, return_id=return_obj.id,
                             sellable_quantity=3, damaged_quantity=0)
        complete_return_and_restock(
            db_session,
            return_id=return_obj.id,
            refund_reference="REFUND-TXN-12345",
            should_restock=True,
        )

        db_session.refresh(bal_a)
        db_session.refresh(bal_b)

        # Supplier A (the fulfilling supplier) must be restocked (+3 units -> 10)
        assert bal_a.on_hand == 10

        # Supplier B (the new active supplier) must remain completely untouched (5 units)
        assert bal_b.on_hand == 5
