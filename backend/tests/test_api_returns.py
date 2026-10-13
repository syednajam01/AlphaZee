"""
test_api_returns.py — Integration and API tests for customer returns, size exchanges, bank refunds, and restocks.
"""

from __future__ import annotations

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.catalog import AvailabilityStatus, Collection, Product, Variant
from app.models.inventory import InventoryBalance, StockEvent, SupplierVariant
from app.models.orders import Order, OrderLine
from app.models.suppliers import Supplier
from app.services.orders import CreateOrderDTO, OrderItemDTO, place_order, confirm_supplier_acceptance, deliver_order
from app.services.shipments import create_shipment
from app.services.returns import (
    approve_return_request,
    complete_return_and_restock,
    create_return_request,
    reject_return_request,
    receive_return_items,
    inspect_return_items,
)


@pytest.fixture
def setup_order_with_stock(db_session: Session):
    col_id = f"ret-col-{uuid.uuid4().hex[:6]}"
    col = Collection(id=col_id, name="Returns Collection", slug=col_id)
    db_session.add(col)
    db_session.flush()

    prod = Product(id=f"prod-ret-{uuid.uuid4().hex[:6]}", title="Exchange Hoodie", slug=f"exchange-hoodie-{uuid.uuid4().hex[:6]}", collection_id=col.id)
    db_session.add(prod)
    db_session.flush()

    var_m = Variant(product_id=prod.id, sku=f"SKU-HOODIE-M-{uuid.uuid4().hex[:6]}", size="M", color="Black", price_minor=300000, availability=AvailabilityStatus.AVAILABLE, is_active=True)
    var_l = Variant(product_id=prod.id, sku=f"SKU-HOODIE-L-{uuid.uuid4().hex[:6]}", size="L", color="Black", price_minor=300000, availability=AvailabilityStatus.AVAILABLE, is_active=True)
    db_session.add_all([var_m, var_l])
    db_session.flush()

    supp = Supplier(name=f"Return Vendor {uuid.uuid4().hex[:6]}", slug=f"ret-vendor-{uuid.uuid4().hex[:6]}", status="active")
    db_session.add(supp)
    db_session.flush()

    sv_m = SupplierVariant(supplier_id=supp.id, variant_id=var_m.id, supplier_cost_minor=150000, active=True)
    sv_l = SupplierVariant(supplier_id=supp.id, variant_id=var_l.id, supplier_cost_minor=150000, active=True)
    db_session.add_all([sv_m, sv_l])
    db_session.flush()

    bal_m = InventoryBalance(supplier_variant_id=sv_m.id, on_hand=10, version=1)
    bal_l = InventoryBalance(supplier_variant_id=sv_l.id, on_hand=10, version=1)
    db_session.add_all([bal_m, bal_l])
    db_session.flush()

    order = place_order(
        db_session,
        CreateOrderDTO(
            customer_name="Hamza Khan",
            customer_phone="03001234567",
            shipping_address_line1="Gulberg III",
            shipping_city="Lahore",
            shipping_province="Punjab",
            payment_method="cod",
            items=[OrderItemDTO(variant_id=var_m.id, quantity=2)],
        ),
    )
    db_session.flush()

    confirm_supplier_acceptance(db_session, order_id=order.id)
    create_shipment(db_session, order_id=order.id, courier_code='manual',
                    tracking_number=f'RET-{uuid.uuid4().hex[:8]}')
    deliver_order(db_session, order_id=order.id)

    return {
        "order": order,
        "line": order.lines[0],
        "variant_m": var_m,
        "variant_l": var_l,
        "supplier_variant_m": sv_m,
        "balance_m": bal_m,
    }


def test_return_lifecycle_and_restock(db_session: Session, setup_order_with_stock):
    data = setup_order_with_stock
    order = data["order"]
    line = data["line"]
    sv_m = data["supplier_variant_m"]
    bal_m = data["balance_m"]

    # 1. Customer creates a return request for delivered goods.
    ret = create_return_request(
        db_session,
        order_id=order.id,
        order_line_id=line.id,
        customer_phone=order.customer_phone,
        return_type="refund_bank_transfer",
        reason="size_too_small",
        customer_notes="Please exchange with size L",
        exchange_variant_id=data["variant_l"].id,
        quantity=2,
    )
    db_session.flush()
    assert ret.status == "requested"
    assert ret.return_type == "refund_bank_transfer"

    # 2. Admin approves return
    app_ret = approve_return_request(db_session, return_id=ret.id)
    assert app_ret.status == "approved"

    # Initial on hand before restock
    initial_on_hand = bal_m.on_hand

    # 3. Receipt is quarantined; only inspection restores sellable units.
    receive_return_items(db_session, return_id=ret.id, received_quantity=2)
    inspect_return_items(db_session, return_id=ret.id, sellable_quantity=2, damaged_quantity=0)
    comp_ret = complete_return_and_restock(
        db_session,
        return_id=ret.id,
        refund_reference="EXCHANGE-SENT-01",
        should_restock=True,
    )
    assert comp_ret.status == "completed"
    assert comp_ret.refund_reference == "EXCHANGE-SENT-01"
    assert comp_ret.restocked_at is not None

    # Check inventory balance updated
    db_session.refresh(bal_m)
    assert bal_m.on_hand == initial_on_hand + line.quantity


def test_returns_api_endpoints(admin_client: TestClient, db_session: Session, setup_order_with_stock):
    data = setup_order_with_stock
    order = data["order"]
    line = data["line"]

    # 1. Storefront submits return
    sub_res = admin_client.post(
        "/api/v1/returns/request",
        json={
            "order_id": str(order.id),
            "order_line_id": str(line.id),
            "customer_phone": order.customer_phone,
            "return_type": "refund_bank_transfer",
            "reason": "damaged_defective",
            "customer_notes": "Stitching unraveled at collar",
            "quantity": 2,
        },
    )
    assert sub_res.status_code == 201
    ret_id = sub_res.json()["id"]

    # 2. Admin views return list
    list_res = admin_client.get("/api/v1/admin/returns")
    assert list_res.status_code == 200
    assert any(r["id"] == ret_id for r in list_res.json())

    # 3. Admin approves return
    app_res = admin_client.post(f"/api/v1/admin/returns/{ret_id}/approve", json={"refund_amount_minor": 600000})
    assert app_res.status_code == 200
    assert app_res.json()["status"] == "approved"

    # 4. Admin records receipt and inspection, then completes return.
    assert admin_client.post(f"/api/v1/admin/returns/{ret_id}/receive",
                             json={"received_quantity": 2}).status_code == 200
    assert admin_client.post(f"/api/v1/admin/returns/{ret_id}/inspect",
                             json={"sellable_quantity": 2, "damaged_quantity": 0}).status_code == 200
    comp_res = admin_client.post(
        f"/api/v1/admin/returns/{ret_id}/complete",
        json={"refund_reference": "MEZN-REF-9988", "should_restock": True},
    )
    assert comp_res.status_code == 200
    assert comp_res.json()["status"] == "completed"
    assert comp_res.json()["refund_reference"] == "MEZN-REF-9988"
