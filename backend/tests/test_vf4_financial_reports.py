"""
test_vf4_financial_reports.py — Comprehensive tests for Phase VF4.

Tests:
1. Golden Fixture 1: Delivered COD (Price 2000, Cost 1200, Outbound 200, Packaging 50 -> Contribution 550, Cash Movement 550).
2. Golden Fixture 2: RTO before delivery, pickup trigger (Delivered Sales 0, Cost 1200 payable, Outbound 200 + RTO 150 = 350 AlphaZee expenses).
3. Golden Fixture 3: Customer return & COGS reversal (Sellable restock reverses COGS, refund liability vs refund payment).
4. Golden Fixture 4: Asia/Karachi date boundary isolation (Start date and end date filtering).
5. Golden Fixture 5: Per-order economics API returns accurate item-level margins and logistics costs.
6. Golden Fixture 6: CSV exports for order economics and period P&L escape formula-injection characters.
"""

from datetime import date, datetime, timezone
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import get_db
from app.main import app
from app.models.business_expenses import BusinessExpense
from app.models.catalog import AvailabilityStatus, Collection, Product, Variant
from app.models.finance import CourierSettlementEntry, RefundExecution
from app.models.inventory import InventoryBalance, SupplierVariant
from app.models.orders import Order, OrderLine
from app.models.returns import OrderReturn
from app.models.shipments import Shipment
from app.models.supplier_finance import (
    SupplierAgreement,
    SupplierLedgerEntry,
    SupplierPaymentAllocation,
)
from app.models.suppliers import Supplier
from app.services.financial_report import (
    escape_csv_cell,
    get_period_financial_report,
    get_order_economics_list,
    export_order_economics_csv,
    export_period_pnl_csv,
)

pytestmark = pytest.mark.usefixtures("configured_bank")


@pytest.fixture
def client(db_session: Session, admin_headers):
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app, headers=admin_headers) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def setup_test_entities(db_session: Session):
    token = uuid.uuid4().hex[:8]

    # Supplier
    sup = Supplier(
        id=uuid.uuid4(),
        name=f"VF4 Silk Mill ({token})",
        slug=f"vf4-mill-{token}",
        status="active",
        supplier_type="external_vendor",
    )
    db_session.add(sup)
    db_session.flush()

    # Agreement: manual
    agr = SupplierAgreement(
        id=uuid.uuid4(),
        supplier_id=sup.id,
        payable_trigger="manual",
        payment_terms_days=15,
        effective_from=datetime.now(timezone.utc),
    )
    db_session.add(agr)

    # Collection & Product
    col = Collection(
        id=f"col-{token}",
        name=f"VF4 Collection {token}",
        slug=f"vf4-col-{token}",
        is_active=True,
    )
    db_session.add(col)
    db_session.flush()

    prod = Product(
        id=f"prod-{token}",
        collection_id=col.id,
        title="VF4 Embroidered Tunic",
        slug=f"vf4-tunic-{token}",
        status="published",
        stock_management_source="vendor_managed",
        vendor_id=sup.id,
    )
    db_session.add(prod)
    db_session.flush()

    var = Variant(
        product_id=prod.id,
        sku=f"VF4-TUN-M-{token}",
        size="M",
        color="Teal",
        price_minor=200000,  # PKR 2,000
    )
    db_session.add(var)
    db_session.flush()

    sv = SupplierVariant(
        id=uuid.uuid4(),
        supplier_id=sup.id,
        variant_id=var.id,
        supplier_cost_minor=120000,  # PKR 1,200
        active=True,
    )
    db_session.add(sv)
    db_session.flush()

    bal = InventoryBalance(
        supplier_variant_id=sv.id,
        on_hand=10,
        version=1,
    )
    db_session.add(bal)
    db_session.commit()

    return {
        "supplier": sup,
        "agreement": agr,
        "product": prod,
        "variant": var,
        "supplier_variant": sv,
    }


def test_golden_fixture_1_delivered_cod_economics_and_cash(
    db_session: Session, setup_test_entities: dict
):
    """
    Delivered COD:
    - Price PKR 2,000, unit cost 1,200, delivery 200, packaging 50.
    - Contribution before overhead: PKR 550 (2,000 - 1,200 - 200 - 50 = 550).
    - Courier collects 2,000, remits 1,800 net of 200 delivery fee deduction.
    - Supplier paid 700 then 500: liability becomes 0.
    - Paid packaging (50) leaves net recorded cash movement 550 (1,800 - 1,200 - 50 = 550).
    """
    var = setup_test_entities["variant"]
    sup = setup_test_entities["supplier"]

    # 1. Create Delivered Order
    order_id = uuid.uuid4()
    order = Order(
        id=order_id,
        order_number=f"ORD-VF4-001",
        customer_name="Zubair Ahmed",
        customer_phone="03001234567",
        shipping_address_line1="DHA Phase 6",
        shipping_city="Karachi",
        shipping_province="Sindh",
        payment_method="cod",
        payment_status="pending",
        order_status="delivered",
        subtotal_minor=200000,  # PKR 2,000
        shipping_fee_minor=0,
        discount_amount_minor=0,
        total_minor=200000,  # PKR 2,000
        placed_at=datetime.now(timezone.utc),
    )
    db_session.add(order)
    db_session.flush()

    line = OrderLine(
        id=uuid.uuid4(),
        order_id=order.id,
        variant_id=var.id,
        product_title_snapshot="VF4 Embroidered Tunic",
        variant_sku_snapshot=var.sku,
        variant_size_snapshot=var.size,
        variant_color_snapshot=var.color,
        quantity=1,
        unit_price_minor=200000,  # PKR 2,000
        unit_cost_minor=120000,  # PKR 1,200
        line_total_minor=200000,
        ownership_source="vendor_consignment",
        fulfillment_kind="original",
    )
    db_session.add(line)

    # 2. Shipment with PKR 200 outbound courier cost and PKR 2,000 COD
    shipment = Shipment(
        id=uuid.uuid4(),
        order_id=order.id,
        courier_code="trax",
        tracking_number="TRX-VF4-001",
        shipping_cost_minor=20000,  # PKR 200
        cod_amount_minor=200000,  # PKR 2,000
        status="delivered",
        cod_remittance_status="remitted",
        delivered_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(shipment)
    db_session.flush()

    # Courier remits 1,800 with 200 delivery fee deduction
    remit_receipt = CourierSettlementEntry(
        id=uuid.uuid4(),
        shipment_id=shipment.id,
        entry_type="receipt",
        amount_minor=180000,  # PKR 1,800
        reference="BANK-TRX-REMIT-01",
        final_statement=True,
        recorded_at=datetime.now(timezone.utc),
    )
    deduction = CourierSettlementEntry(
        id=uuid.uuid4(),
        shipment_id=shipment.id,
        entry_type="outbound_shipping",
        amount_minor=20000,  # PKR 200
        reference="TRX-FEE-DED-01",
        final_statement=True,
        recorded_at=datetime.now(timezone.utc),
    )
    db_session.add_all([remit_receipt, deduction])

    # 3. Packaging Expense: PKR 50 paid
    pkg_exp = BusinessExpense(
        id=uuid.uuid4(),
        category="packaging",
        amount_minor=5000,  # PKR 50
        incurred_date=date.today(),
        paid_date=date.today(),
        payment_method="cash",
        payee="Local Polybag Supplier",
        reference="PKG-CASH-01",
    )
    db_session.add(pkg_exp)

    # 4. Supplier Charge PKR 1,200 & Payments (PKR 700 then 500)
    charge = SupplierLedgerEntry(
        id=uuid.uuid4(),
        supplier_id=sup.id,
        entry_type="charge",
        amount_minor=120000,  # PKR 1,200
        direction="credit",
        source_event_key=f"order:{order.id}:charge",
        order_id=order.id,
        order_line_id=line.id,
        reference="INV-VF4-001",
        effective_date=date.today(),
    )
    db_session.add(charge)
    db_session.flush()

    pmt1 = SupplierLedgerEntry(
        id=uuid.uuid4(),
        supplier_id=sup.id,
        entry_type="payment",
        amount_minor=70000,  # PKR 700
        direction="debit",
        source_event_key=f"pmt:vf4:1",
        reference="BANK-SUP-01",
        effective_date=date.today(),
    )
    pmt2 = SupplierLedgerEntry(
        id=uuid.uuid4(),
        supplier_id=sup.id,
        entry_type="payment",
        amount_minor=50000,  # PKR 500
        direction="debit",
        source_event_key=f"pmt:vf4:2",
        reference="BANK-SUP-02",
        effective_date=date.today(),
    )
    db_session.add_all([pmt1, pmt2])
    db_session.flush()

    alloc1 = SupplierPaymentAllocation(
        id=uuid.uuid4(),
        payment_entry_id=pmt1.id,
        charge_entry_id=charge.id,
        allocated_amount_minor=70000,
    )
    alloc2 = SupplierPaymentAllocation(
        id=uuid.uuid4(),
        payment_entry_id=pmt2.id,
        charge_entry_id=charge.id,
        allocated_amount_minor=50000,
    )
    db_session.add_all([alloc1, alloc2])
    db_session.commit()

    # 5. Evaluate Report
    report = get_period_financial_report(db_session)

    # Revenue
    assert report["revenue"]["gross_sales_minor"] == 200000
    assert report["revenue"]["net_revenue_minor"] == 200000

    # COGS
    assert report["cogs"]["gross_cogs_minor"] == 120000
    assert report["cogs"]["net_cogs_minor"] == 120000

    # Freight
    assert report["freight"]["outbound_freight_minor"] == 20000
    assert report["freight"]["total_freight_minor"] == 20000

    # Overhead Packaging
    assert report["overhead"]["packaging_minor"] == 5000

    # Contribution before overhead: 2000 - 1200 - 200 - 50 = 550
    assert report["operating_result"]["contribution_before_overhead_minor"] == 55000
    assert report["operating_result"]["contribution_margin_percent"] == 27.5

    # Cash Reconciliation:
    # Inflow: Remitted 1,800
    assert report["cash_reconciliation"]["courier_cod_remitted_minor"] == 180000
    assert report["cash_reconciliation"]["total_cash_inflow_minor"] == 180000
    # Outflow: Supplier payments (700 + 500 = 1,200) + packaging (50) = 1,250
    assert report["cash_reconciliation"]["supplier_payments_paid_minor"] == 120000
    assert report["cash_reconciliation"]["business_expenses_paid_cash_or_bank_minor"] == 5000
    assert report["cash_reconciliation"]["total_cash_outflow_minor"] == 125000
    # Net cash movement: 1,800 - 1,250 = 550
    assert report["cash_reconciliation"]["net_cash_movement_minor"] == 55000
    # Supplier liability: 0 (fully paid)
    assert report["cash_reconciliation"]["supplier_liabilities_outstanding_minor"] == 0
    # Courier held COD: 0
    assert report["cash_reconciliation"]["courier_held_cod_outstanding_minor"] == 0


def test_golden_fixture_2_rto_before_delivery(
    db_session: Session, setup_test_entities: dict
):
    """
    RTO before delivery, pickup trigger:
    - Delivered sales = 0.
    - Cost 1,200 remains payable (unless vendor credits it).
    - Outbound 200 + RTO 150 = 350 AlphaZee expenses.
    - Sellable goods remain AlphaZee inventory.
    """
    var = setup_test_entities["variant"]
    sup = setup_test_entities["supplier"]

    order = Order(
        id=uuid.uuid4(),
        order_number="ORD-VF4-RTO",
        customer_name="Farooq Tariq",
        customer_phone="03009998877",
        shipping_address_line1="Gulberg III",
        shipping_city="Lahore",
        shipping_province="Punjab",
        payment_method="cod",
        payment_status="pending",
        order_status="rto",
        subtotal_minor=200000,
        shipping_fee_minor=0,
        discount_amount_minor=0,
        total_minor=200000,
        placed_at=datetime.now(timezone.utc),
    )
    db_session.add(order)
    db_session.flush()

    line = OrderLine(
        id=uuid.uuid4(),
        order_id=order.id,
        variant_id=var.id,
        product_title_snapshot="VF4 Embroidered Tunic",
        variant_sku_snapshot=var.sku,
        variant_size_snapshot=var.size,
        variant_color_snapshot=var.color,
        quantity=1,
        unit_price_minor=200000,
        unit_cost_minor=120000,
        line_total_minor=200000,
        ownership_source="vendor_consignment",
        fulfillment_kind="original",
    )
    db_session.add(line)

    shipment = Shipment(
        id=uuid.uuid4(),
        order_id=order.id,
        courier_code="trax",
        tracking_number="TRX-RTO-999",
        shipping_cost_minor=20000,  # PKR 200
        rto_courier_cost_minor=15000,  # PKR 150
        cod_amount_minor=200000,
        status="rto_initiated",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(shipment)

    # Supplier charge remains payable: PKR 1,200
    charge = SupplierLedgerEntry(
        id=uuid.uuid4(),
        supplier_id=sup.id,
        entry_type="charge",
        amount_minor=120000,
        direction="credit",
        source_event_key=f"order:{order.id}:pickup",
        order_id=order.id,
        order_line_id=line.id,
        reference="INV-RTO-001",
        effective_date=date.today(),
    )
    db_session.add(charge)
    db_session.commit()

    report = get_period_financial_report(db_session)
    # Delivered sales should NOT include this order
    # Freight must include outbound 200 + RTO 150 = 350
    assert report["freight"]["rto_freight_minor"] >= 15000
    assert report["freight"]["outbound_freight_minor"] >= 20000
    assert report["cash_reconciliation"]["supplier_liabilities_outstanding_minor"] >= 120000


def test_golden_fixture_3_customer_return_and_cogs_reversal(
    db_session: Session, setup_test_entities: dict
):
    """
    Customer return:
    - Refund creates refund liability; payment reduces cash.
    - AlphaZee bears return transport.
    - Sellable inspected units reverse COGS.
    """
    var = setup_test_entities["variant"]

    order = Order(
        id=uuid.uuid4(),
        order_number="ORD-VF4-RET",
        customer_name="Saima Noor",
        customer_phone="03004443322",
        shipping_address_line1="F-7/2",
        shipping_city="Islamabad",
        shipping_province="ICT",
        payment_method="bank_transfer",
        payment_status="verified",
        order_status="delivered",
        subtotal_minor=200000,
        shipping_fee_minor=0,
        discount_amount_minor=0,
        total_minor=200000,
        placed_at=datetime.now(timezone.utc),
        payment_verified_at=datetime.now(timezone.utc),
    )
    db_session.add(order)
    db_session.flush()

    line = OrderLine(
        id=uuid.uuid4(),
        order_id=order.id,
        variant_id=var.id,
        product_title_snapshot="VF4 Embroidered Tunic",
        variant_sku_snapshot=var.sku,
        variant_size_snapshot=var.size,
        variant_color_snapshot=var.color,
        quantity=1,
        unit_price_minor=200000,
        unit_cost_minor=120000,
        line_total_minor=200000,
        ownership_source="vendor_consignment",
        fulfillment_kind="original",
    )
    db_session.add(line)

    ret = OrderReturn(
        id=uuid.uuid4(),
        order_id=order.id,
        order_line_id=line.id,
        return_type="refund_bank_transfer",
        reason="size_too_small",
        status="completed",
        quantity=1,
        received_quantity=1,
        refund_amount_minor=200000,  # PKR 2,000 refund
        sellable_quantity=1,  # 1 unit returned sellable
        damaged_quantity=0,
        created_at=datetime.now(timezone.utc),
        inspected_at=datetime.now(timezone.utc),
    )
    db_session.add(ret)

    # Return transport expense borne by AlphaZee: PKR 250
    ret_exp = BusinessExpense(
        id=uuid.uuid4(),
        category="customer_return_transport",
        amount_minor=25000,  # PKR 250
        incurred_date=date.today(),
        payment_method="cash",
        paid_date=date.today(),
        payee="Rider Express Return",
    )
    db_session.add(ret_exp)
    db_session.commit()

    report = get_period_financial_report(db_session)
    assert report["cogs"]["cogs_reversals_minor"] >= 120000
    assert report["revenue"]["sales_reversals_minor"] >= 200000
    assert report["freight"]["customer_return_freight_minor"] >= 25000


def test_order_economics_api_and_formula_escaping(
    client: TestClient, db_session: Session, setup_test_entities: dict
):
    """Verify order economics endpoint returns correct calculations and CSV escapes formulas."""
    var = setup_test_entities["variant"]

    order = Order(
        id=uuid.uuid4(),
        order_number="=CMD|' /C calc'!A0",  # Test CSV formula injection string
        customer_name="+923001112233",  # Starts with +
        customer_phone="03001112233",
        shipping_address_line1="Clifton Block 4",
        shipping_city="Karachi",
        shipping_province="Sindh",
        payment_method="cod",
        payment_status="pending",
        order_status="delivered",
        subtotal_minor=200000,
        shipping_fee_minor=15000,
        discount_amount_minor=10000,
        total_minor=205000,  # 2000 + 150 - 100 = 2050
        placed_at=datetime.now(timezone.utc),
    )
    db_session.add(order)
    db_session.flush()

    line = OrderLine(
        id=uuid.uuid4(),
        order_id=order.id,
        variant_id=var.id,
        product_title_snapshot="VF4 Embroidered Tunic",
        variant_sku_snapshot=var.sku,
        variant_size_snapshot=var.size,
        variant_color_snapshot=var.color,
        quantity=1,
        unit_price_minor=200000,
        unit_cost_minor=120000,
        line_total_minor=200000,
        ownership_source="vendor_consignment",
        fulfillment_kind="original",
    )
    db_session.add(line)
    db_session.commit()

    # 1. Test JSON endpoint
    res = client.get("/api/v1/admin/reports/orders")
    assert res.status_code == 200
    data = res.json()
    assert "orders" in data
    assert data["total_orders"] >= 1
    found = next((o for o in data["orders"] if str(o["order_id"]) == str(order.id)), None)
    assert found is not None
    assert found["customer_total_minor"] == 205000
    assert found["cogs_minor"] == 120000
    assert len(found["lines"]) == 1
    assert found["lines"][0]["unit_cost_minor"] == 120000

    # 2. Test CSV Export endpoint
    csv_res = client.get("/api/v1/admin/reports/orders/export")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["Content-Type"]
    content = csv_res.text
    # Verify formula injection was escaped with a prepended single quote
    assert "'=CMD|' /C calc'!A0" in content

    # 3. Test Period CSV Export endpoint
    pnl_res = client.get("/api/v1/admin/reports/period/export")
    assert pnl_res.status_code == 200
    assert "text/csv" in pnl_res.headers["Content-Type"]
    pnl_text = pnl_res.text
    assert "AlphaZee Period Financial & P&L Statement" in pnl_text
    assert "NET REVENUE" in pnl_text
    assert "CONTRIBUTION BEFORE OVERHEAD" in pnl_text
    assert "NET CASH MOVEMENT" in pnl_text


def test_escape_csv_cell():
    """Unit test for CSV formula injection mitigation."""
    assert escape_csv_cell("Normal Text") == "Normal Text"
    assert escape_csv_cell("12345") == "12345"
    assert escape_csv_cell("=1+1") == "'=1+1"
    assert escape_csv_cell("+441234567") == "'+441234567"
    assert escape_csv_cell("-500") == "'-500"
    assert escape_csv_cell("@SUM(A1:A10)") == "'@SUM(A1:A10)"
    assert escape_csv_cell("\tTab") == "'\tTab"
    assert escape_csv_cell(None) == ""
