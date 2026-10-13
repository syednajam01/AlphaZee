"""
test_delivery_transitions.py — Defect reproduction and integration tests for Blocker 4:
Delivery, cancellation, sequential stock reservation transitions, and two-step RTO lifecycle.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from app.models.catalog import AvailabilityStatus, Collection, Product, Variant
from app.models.inventory import InventoryBalance, StockReservation, SupplierVariant
from app.models.orders import Order
from app.models.shipments import Shipment
from app.models.suppliers import Supplier
from app.queries.reservations import get_inventory_summary
from app.services.orders import (
    CreateOrderDTO,
    OrderItemDTO,
    OrderNotCancellableError,
    cancel_order,
    confirm_supplier_acceptance,
    deliver_order,
    place_order,
)
from app.services.shipments import (
    create_shipment,
    initiate_rto_order,
    receive_rto_parcel,
)


def _setup_catalog(db: Session, on_hand: int = 10):
    uid = uuid.uuid4().hex[:6]
    col = Collection(
        id=f"col-{uid}",
        slug=f"col-{uid}",
        name="Delivery Test Collection",
        is_active=True,
        display_order=0,
    )
    db.add(col)
    db.flush()

    prod = Product(
        id=f"prod-{uid}",
        slug=f"prod-{uid}",
        title="Delivery Test Item",
        collection_id=col.id,
        is_active=True,
    )
    db.add(prod)
    db.flush()

    var = Variant(
        sku=f"SKU-DELIV-{uid}",
        product_id=prod.id,
        size="L",
        color="Black",
        price_minor=350000,
        is_active=True,
        availability=AvailabilityStatus.AVAILABLE,
    )
    db.add(var)
    db.flush()

    sup = Supplier(
        name="Vendor Karachi",
        slug=f"vendor-karachi-{uid}",
        status="active",
    )
    db.add(sup)
    db.flush()

    sv = SupplierVariant(
        supplier_id=sup.id,
        variant_id=var.id,
        active=True,
        supplier_cost_minor=200000,
    )
    db.add(sv)
    db.flush()

    ib = InventoryBalance(
        supplier_variant_id=sv.id,
        on_hand=on_hand,
        version=0,
    )
    db.add(ib)
    db.flush()

    return {"collection": col, "product": prod, "variant": var, "supplier": sup, "supplier_variant": sv, "balance": ib}


def _create_confirmed_order(db: Session, fixture_data: dict, qty: int = 2) -> Order:
    var = fixture_data["variant"]
    dto = CreateOrderDTO(
        customer_name="Ahmed Khan",
        customer_phone="03001234567",
        customer_email="ahmed@example.com",
        shipping_address_line1="House 12, Street 4, F-8/1",
        shipping_city="Islamabad",
        shipping_province="Islamabad Capital Territory",
        payment_method="cod",
        items=[
            OrderItemDTO(
                variant_id=var.id,
                quantity=qty,
            )
        ],
    )
    order = place_order(db, order_data=dto)
    confirm_supplier_acceptance(db, order_id=order.id, supplier_notes="Accepted for courier dispatch")
    db.flush()
    return order


class TestDeliveryAndCancellationTransitions:
    """Blocker 4 reproduction and verification test suite."""

    def test_cancelling_dispatched_order_rejected_with_422(self, db_session: Session, admin_client: TestClient):
        """
        Defect reproduction: Cancelling a dispatched order was previously allowed,
        releasing held stock while the parcel was physically with the courier.
        Must raise OrderNotCancellableError at service level and return 422 via admin API.
        """
        cat = _setup_catalog(db_session, on_hand=10)
        order = _create_confirmed_order(db_session, cat, qty=2)

        # Dispatch the order
        shipment = create_shipment(
            db_session,
            order_id=order.id,
            courier_code="trax",
            tracking_number="TRX-123456",
            shipping_cost_minor=25000,
        )
        assert order.order_status == "dispatched"

        # 1. Service layer must raise OrderNotCancellableError
        with pytest.raises(OrderNotCancellableError) as exc_info:
            cancel_order(db_session, order_id=order.id, reason="Customer called to cancel")
        assert "dispatched" in str(exc_info.value).lower()

        db_session.commit()

        # 2. Admin API endpoint must return HTTP 422 Unprocessable Entity
        resp = admin_client.post(
            f"/api/v1/admin/orders/{order.id}/cancel",
        )
        assert resp.status_code == 422
        assert "dispatched" in resp.json()["detail"].lower()

    def test_deliver_order_transitions_reservations_sequentially(self, db_session: Session):
        """
        Reservation lifecycle must advance through held -> confirmed -> dispatched -> fulfilled
        without skipping stages.
        """
        cat = _setup_catalog(db_session, on_hand=10)
        sv = cat["supplier_variant"]
        order = _create_confirmed_order(db_session, cat, qty=2)

        # Check reservation is confirmed
        res = db_session.scalars(
            select(StockReservation).where(StockReservation.order_line_id == order.lines[0].id)
        ).first()
        assert res is not None
        assert res.stage == "confirmed"

        # Dispatch order via create_shipment
        shipment = create_shipment(
            db_session,
            order_id=order.id,
            courier_code="postex",
            tracking_number="PST-998877",
            shipping_cost_minor=20000,
        )
        db_session.refresh(res)
        # In Blocker 4, create_shipment must transition reservation to 'dispatched'
        assert res.stage == "dispatched"

        # Deliver order
        deliver_order(db_session, order_id=order.id)
        db_session.refresh(res)
        assert res.stage == "fulfilled"

        # Physical on_hand decremented from 10 to 8
        summary = get_inventory_summary(db_session, sv.id)
        assert summary.physical == 8
        assert summary.held == 0
        assert summary.available == 8

    def test_rto_in_transit_does_not_release_stock(self, db_session: Session, admin_client: TestClient):
        """
        A parcel in transit remains outside physical sellable stock.
        """
        cat = _setup_catalog(db_session, on_hand=10)
        sv = cat["supplier_variant"]
        order = _create_confirmed_order(db_session, cat, qty=3)

        shipment = create_shipment(
            db_session,
            order_id=order.id,
            courier_code="trax",
            tracking_number="TRX-RTO-111",
            shipping_cost_minor=25000,
        )
        db_session.commit()

        # Dispatch consumed the hold and deducted physical stock.
        summary_before = get_inventory_summary(db_session, sv.id)
        assert summary_before.held == 0
        assert summary_before.physical == 7
        assert summary_before.available == 7

        # Call initiate RTO via API
        resp = admin_client.post(
            f"/api/v1/admin/orders/{order.id}/rto",
            json={"reason": "Customer refused delivery at doorstep", "rto_courier_cost_minor": 15000},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["order_status"] == "rto"

        db_session.refresh(shipment)
        assert shipment.status == "rto_initiated"
        assert shipment.rto_reason == "Customer refused delivery at doorstep"
        assert shipment.rto_courier_cost_minor == 15000

        # RTO initiation does not restock the in-transit parcel.
        summary_after_rto = get_inventory_summary(db_session, sv.id)
        assert summary_after_rto.held == 0
        assert summary_after_rto.physical == 7
        assert summary_after_rto.available == 7

    def test_rto_received_releases_stock_back_to_available(self, db_session: Session, admin_client: TestClient):
        """
        Physical receipt quarantines stock; inspection restores only accepted units.
        """
        cat = _setup_catalog(db_session, on_hand=10)
        sv = cat["supplier_variant"]
        order = _create_confirmed_order(db_session, cat, qty=3)

        shipment = create_shipment(
            db_session,
            order_id=order.id,
            courier_code="leopards",
            tracking_number="LEO-RTO-222",
            shipping_cost_minor=30000,
        )
        db_session.commit()

        # 1. Initiate RTO
        admin_client.post(
            f"/api/v1/admin/orders/{order.id}/rto",
            json={"reason": "Customer address unlocatable", "rto_courier_cost_minor": 20000},
        )

        # 2. Confirm RTO physical receipt
        resp = admin_client.post(
            f"/api/v1/admin/orders/{order.id}/rto-received",
            json={"lines": [{"order_line_id": str(order.lines[0].id), "received_quantity": 3}]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["order_status"] == "rto"

        db_session.refresh(shipment)
        assert shipment.status == "rto_delivered"

        # 3. Inspect condition & restock
        insp_resp = admin_client.post(
            f"/api/v1/admin/orders/{order.id}/rto-inspect",
            json={"lines": [{"order_line_id": str(order.lines[0].id),
                              "sellable_quantity": 3, "damaged_quantity": 0}],
                  "notes": "Packaging sealed and pristine"},
        )
        assert insp_resp.status_code == 200

        db_session.refresh(shipment)
        assert shipment.rto_restocked_at is not None

        # Reservations are cancelled, held stock released back to available
        summary_final = get_inventory_summary(db_session, sv.id)
        assert summary_final.held == 0
        assert summary_final.physical == 10
        assert summary_final.available == 10
