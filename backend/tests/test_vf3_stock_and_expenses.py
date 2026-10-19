"""
test_vf3_stock_and_expenses.py — Unit test suite for Phase VF3 / VS0–VS1:
- Stock ownership source (vendor_consignment vs alphazee_owned).
- Secondary resale invariant: resale of AlphaZee-owned returned units generates zero vendor liability.
- Product-level stock management responsibility (alphazee_managed vs vendor_managed).
- Reassignment guards blocking vendor changes while reservations/holds exist.
- Internal AlphaZee inventory source (no vendor credentials, zero supplier payables).
- Categorized business expenses service and courier deduction linkage.
"""

import uuid
from datetime import date, datetime, timezone
import pytest
from sqlalchemy import select

from app.models.catalog import Collection, Product, Variant, AvailabilityStatus
from app.models.inventory import InventoryBalance, StockReservation, SupplierVariant
from app.models.orders import Order, OrderLine
from app.models.suppliers import Supplier, get_or_create_internal_supplier
from app.models.supplier_finance import SupplierAgreement, SupplierLedgerEntry
from app.models.business_expenses import BusinessExpense
from app.schemas.business_expenses import BusinessExpenseCreate
from app.schemas.owner_catalog import ProductCreate, ProductUpdate, VariantEdit
from app.services.business_expenses import (
    create_business_expense,
    get_business_expenses,
    get_expense_summary,
)
from app.services.owner_catalog import CatalogError, create_product, edit_product
from app.services.supplier_finance import (
    get_or_create_supplier_agreement,
    post_event_liability_if_applicable,
    update_supplier_agreement,
)
from app.schemas.supplier_finance import SupplierAgreementUpdateRequest


@pytest.fixture
def test_collection(db_session):
    col = db_session.get(Collection, "essentials")
    if not col:
        col = Collection(
            id="essentials",
            slug="essentials",
            name="Essentials",
            is_active=True,
            display_order=1,
        )
        db_session.add(col)
        db_session.flush()
    return col


@pytest.fixture
def vendor_a(db_session):
    sup = Supplier(
        name="Vendor Denim Craft",
        slug=f"vendor-denim-{uuid.uuid4().hex[:6]}",
        status="active",
        supplier_type="external_vendor",
        notes="Primary supplier for jeans",
    )
    db_session.add(sup)
    db_session.flush()
    return sup


@pytest.fixture
def vendor_b(db_session):
    sup = Supplier(
        name="Vendor Cotton Mills",
        slug=f"vendor-cotton-{uuid.uuid4().hex[:6]}",
        status="active",
        supplier_type="external_vendor",
        notes="Alternative supplier",
    )
    db_session.add(sup)
    db_session.flush()
    return sup


def test_product_stock_management_source_alphazee(db_session, test_collection):
    """AlphaZee-managed product creation maps variants to internal supplier source."""
    prod_cmd = ProductCreate(
        title="Alpha Core Tee",
        slug=f"alpha-core-tee-{uuid.uuid4().hex[:6]}",
        collection_id=test_collection.id,
        stock_management_source="alphazee_managed",
        variants=[
            VariantEdit(sku=f"CORE-TEE-M-{uuid.uuid4().hex[:4]}", size="M", color="Black", price_minor=250000, is_active=True)
        ],
    )
    product = create_product(db_session, prod_cmd)
    db_session.flush()

    assert product.stock_management_source == "alphazee_managed"
    assert product.vendor_id is None

    # Check variant mapping auto-synchronized to internal supplier
    internal_sup = get_or_create_internal_supplier(db_session)
    variant = product.variants[0]
    sv = db_session.scalar(
        select(SupplierVariant).where(
            SupplierVariant.variant_id == variant.id,
            SupplierVariant.active.is_(True),
        )
    )
    assert sv is not None
    assert sv.supplier_id == internal_sup.id
    assert sv.balance is not None


def test_product_stock_management_source_vendor(db_session, test_collection, vendor_a):
    """Vendor-managed product links to external supplier and synchronizes variant mapping."""
    prod_cmd = ProductCreate(
        title="Vendor Denim Jeans",
        slug=f"vendor-jeans-{uuid.uuid4().hex[:6]}",
        collection_id=test_collection.id,
        stock_management_source="vendor_managed",
        vendor_id=vendor_a.id,
        variants=[
            VariantEdit(sku=f"JEANS-32-{uuid.uuid4().hex[:4]}", size="32", color="Indigo", price_minor=450000, is_active=True)
        ],
    )
    product = create_product(db_session, prod_cmd)
    db_session.flush()

    assert product.stock_management_source == "vendor_managed"
    assert product.vendor_id == vendor_a.id

    # Check variant mapping links to vendor_a
    variant = product.variants[0]
    sv = db_session.scalar(
        select(SupplierVariant).where(
            SupplierVariant.variant_id == variant.id,
            SupplierVariant.active.is_(True),
        )
    )
    assert sv is not None
    assert sv.supplier_id == vendor_a.id


def test_vendor_managed_requires_active_vendor(db_session, test_collection):
    """Creating a vendor_managed product without vendor_id or with inactive vendor is rejected."""
    # Missing vendor_id
    cmd_no_vendor = ProductCreate(
        title="Missing Vendor Tee",
        slug=f"missing-vendor-{uuid.uuid4().hex[:6]}",
        collection_id=test_collection.id,
        stock_management_source="vendor_managed",
        vendor_id=None,
    )
    with pytest.raises(CatalogError) as exc_info:
        create_product(db_session, cmd_no_vendor)
    assert exc_info.value.detail["code"] == "vendor_required"

    # Inactive vendor
    inactive_vendor = Supplier(
        name="Suspended Vendor",
        slug=f"suspended-vendor-{uuid.uuid4().hex[:6]}",
        status="suspended",
    )
    db_session.add(inactive_vendor)
    db_session.flush()

    cmd_inactive = ProductCreate(
        title="Suspended Vendor Item",
        slug=f"suspended-item-{uuid.uuid4().hex[:6]}",
        collection_id=test_collection.id,
        stock_management_source="vendor_managed",
        vendor_id=inactive_vendor.id,
    )
    with pytest.raises(CatalogError) as exc_info2:
        create_product(db_session, cmd_inactive)
    assert exc_info2.value.detail["code"] == "invalid_vendor"


def test_product_reassignment_blocked_while_held(db_session, test_collection, vendor_a, vendor_b):
    """Product reassignment to another vendor is strictly blocked while open holds exist."""
    prod_cmd = ProductCreate(
        title="Held Vendor Jacket",
        slug=f"held-jacket-{uuid.uuid4().hex[:6]}",
        collection_id=test_collection.id,
        stock_management_source="vendor_managed",
        vendor_id=vendor_a.id,
        variants=[
            VariantEdit(sku=f"JACKET-M-{uuid.uuid4().hex[:4]}", size="M", price_minor=800000, is_active=True)
        ],
    )
    product = create_product(db_session, prod_cmd)
    db_session.flush()
    variant = product.variants[0]

    sv = db_session.scalar(select(SupplierVariant).where(SupplierVariant.variant_id == variant.id))
    order = Order(
        order_number=f"ORD-HELD-{uuid.uuid4().hex[:6]}",
        customer_name="Hold Customer",
        customer_phone="03001234567",
        shipping_address_line1="House 789",
        shipping_city="Islamabad",
        shipping_province="ICT",
        payment_method="cod",
        subtotal_minor=800000,
        total_minor=800000,
    )
    db_session.add(order)
    db_session.flush()

    line = OrderLine(
        order_id=order.id,
        variant_id=variant.id,
        product_title_snapshot="Held Vendor Jacket",
        variant_sku_snapshot=variant.sku,
        unit_price_minor=800000,
        quantity=1,
        line_total_minor=800000,
    )
    order.lines.append(line)
    db_session.flush()

    # Create active hold reservation
    hold = StockReservation(
        order_line_id=line.id,
        supplier_variant_id=sv.id,
        quantity=1,
        stage="held",
        legacy_stock_hold=False,
    )
    db_session.add(hold)
    db_session.flush()

    # Attempt to reassign product to vendor_b
    update_cmd = ProductUpdate(
        expected_version=product.edit_version,
        stock_management_source="vendor_managed",
        vendor_id=vendor_b.id,
    )
    with pytest.raises(CatalogError) as exc_info:
        edit_product(db_session, product.id, update_cmd)
    assert exc_info.value.detail["code"] == "reassignment_blocked"


def test_product_reassignment_permitted_when_no_holds(db_session, test_collection, vendor_a, vendor_b):
    """Product reassignment succeeds when no holds exist, cleanly switching variant supplier mappings."""
    prod_cmd = ProductCreate(
        title="Transferable Hoodie",
        slug=f"transferable-hoodie-{uuid.uuid4().hex[:6]}",
        collection_id=test_collection.id,
        stock_management_source="vendor_managed",
        vendor_id=vendor_a.id,
        variants=[
            VariantEdit(sku=f"HOODIE-L-{uuid.uuid4().hex[:4]}", size="L", price_minor=550000, is_active=True)
        ],
    )
    product = create_product(db_session, prod_cmd)
    db_session.flush()
    variant = product.variants[0]

    # Reassign to vendor_b
    update_cmd = ProductUpdate(
        expected_version=product.edit_version,
        stock_management_source="vendor_managed",
        vendor_id=vendor_b.id,
    )
    updated = edit_product(db_session, product.id, update_cmd)
    db_session.flush()

    assert updated.vendor_id == vendor_b.id

    # Verify active supplier mapping is now vendor_b
    active_sv = db_session.scalar(
        select(SupplierVariant).where(
            SupplierVariant.variant_id == variant.id,
            SupplierVariant.active.is_(True),
        )
    )
    assert active_sv is not None
    assert active_sv.supplier_id == vendor_b.id


def test_alphazee_owned_stock_resale_skips_supplier_liability(db_session, test_collection, vendor_a):
    """Order line tagged as alphazee_owned never triggers vendor liability upon fulfillment."""
    # Configure vendor agreement to trigger on dispatch
    update_supplier_agreement(
        db_session,
        vendor_a.id,
        SupplierAgreementUpdateRequest(payable_trigger="dispatch", payment_terms_days=0),
    )

    prod = create_product(
        db_session,
        ProductCreate(
            title="Returned Resale Tee",
            slug=f"resale-tee-{uuid.uuid4().hex[:6]}",
            collection_id=test_collection.id,
            variants=[
                VariantEdit(sku=f"RESOLD-M-{uuid.uuid4().hex[:4]}", size="M", price_minor=300000, is_active=True)
            ],
        ),
    )
    db_session.flush()
    var = prod.variants[0]

    order = Order(
        order_number=f"ORD-OWNED-{uuid.uuid4().hex[:6]}",
        customer_name="Resale Buyer",
        customer_phone="03001234567",
        shipping_address_line1="House 123",
        shipping_city="Lahore",
        shipping_province="Punjab",
        payment_method="cod",
        subtotal_minor=300000,
        total_minor=300000,
    )
    db_session.add(order)
    db_session.flush()

    # Order line fulfilled from returned/AlphaZee-owned inventory
    line = OrderLine(
        order_id=order.id,
        variant_id=var.id,
        product_title_snapshot="Resold Returned Tee",
        variant_sku_snapshot=var.sku,
        unit_price_minor=300000,
        unit_cost_minor=180000,
        quantity=1,
        line_total_minor=300000,
        ownership_source="alphazee_owned",
    )
    line.supplier_id = vendor_a.id
    order.lines.append(line)
    db_session.flush()

    # Trigger event liability on dispatch
    entries = post_event_liability_if_applicable(db_session, order, "dispatch")
    assert len(entries) == 0, "alphazee_owned line must NOT generate supplier liability"


def test_internal_supplier_skips_supplier_liability(db_session, test_collection):
    """Order line fulfilled from internal AlphaZee inventory never generates vendor liability."""
    internal_sup = get_or_create_internal_supplier(db_session)

    prod = create_product(
        db_session,
        ProductCreate(
            title="Alpha In-House Cap",
            slug=f"alpha-cap-{uuid.uuid4().hex[:6]}",
            collection_id=test_collection.id,
            stock_management_source="alphazee_managed",
            variants=[
                VariantEdit(sku=f"CAP-BLK-{uuid.uuid4().hex[:4]}", price_minor=200000, is_active=True)
            ],
        ),
    )
    db_session.flush()
    var = prod.variants[0]

    order = Order(
        order_number=f"ORD-INTERNAL-{uuid.uuid4().hex[:6]}",
        customer_name="Internal Buyer",
        customer_phone="03001234567",
        shipping_address_line1="House 456",
        shipping_city="Karachi",
        shipping_province="Sindh",
        payment_method="bank_transfer",
        subtotal_minor=200000,
        total_minor=200000,
    )
    db_session.add(order)
    db_session.flush()

    line = OrderLine(
        order_id=order.id,
        variant_id=var.id,
        product_title_snapshot="Alpha In-House Cap",
        variant_sku_snapshot=var.sku,
        unit_price_minor=200000,
        unit_cost_minor=80000,
        quantity=1,
        line_total_minor=200000,
        ownership_source="vendor_consignment",
    )
    line.supplier_id = internal_sup.id
    order.lines.append(line)
    db_session.flush()

    entries = post_event_liability_if_applicable(db_session, order, "dispatch")
    assert len(entries) == 0, "alphazee_internal supplier must NOT generate supplier liability"



def test_create_business_expense_and_validation(db_session):
    """Business expenses validate positive amounts, authorized categories, and payee non-empty."""
    # Valid expense
    payload = BusinessExpenseCreate(
        category="packaging",
        amount_minor=150000,  # PKR 1,500
        incurred_date=date(2026, 10, 20),
        paid_date=date(2026, 10, 20),
        payee="Premier Box Supplies",
        reference="INV-BX-902",
        payment_method="bank_transfer",
        notes="50 premium mailer boxes",
    )
    expense = create_business_expense(db_session, payload)
    db_session.flush()

    assert expense.id is not None
    assert expense.category == "packaging"
    assert expense.amount_minor == 150000
    assert expense.payee == "Premier Box Supplies"

    # Invalid category
    with pytest.raises(ValueError):
        BusinessExpenseCreate(
            category="luxuries",
            amount_minor=50000,
            incurred_date=date(2026, 10, 20),
            payee="Some Vendor",
        )

    # Invalid amount
    with pytest.raises(ValueError):
        BusinessExpenseCreate(
            category="advertising",
            amount_minor=0,
            incurred_date=date(2026, 10, 20),
            payee="Meta Ads",
        )


def test_business_expense_summary_and_filters(db_session):
    """Business expenses report summary by category and date filtering."""
    e1 = create_business_expense(
        db_session,
        BusinessExpenseCreate(
            category="advertising",
            amount_minor=500000,  # PKR 5,000
            incurred_date=date(2026, 10, 15),
            paid_date=date(2026, 10, 15),
            payee="Google Ads",
        ),
    )
    e2 = create_business_expense(
        db_session,
        BusinessExpenseCreate(
            category="rto_transport",
            amount_minor=35000,  # PKR 350
            incurred_date=date(2026, 10, 18),
            paid_date=None,  # Accrued / unpaid
            payee="Trax Logistics",
            notes="AlphaZee-borne RTO return freight",
        ),
    )
    e3 = create_business_expense(
        db_session,
        BusinessExpenseCreate(
            category="platform_hosting",
            amount_minor=120000,  # PKR 1,200
            incurred_date=date(2026, 10, 19),
            paid_date=date(2026, 10, 19),
            payee="Cloud VPS Provider",
        ),
    )
    db_session.flush()

    # Filter by category
    adv_rows, total_adv = get_business_expenses(db_session, category="advertising")
    assert total_adv >= 1
    assert all(r.category == "advertising" for r in adv_rows)

    # Filter by paid status
    unpaid_rows, total_unpaid = get_business_expenses(db_session, is_paid=False)
    assert any(r.id == e2.id for r in unpaid_rows)

    # Summary
    summary = get_expense_summary(db_session)
    assert summary.total_expenses_minor >= 655000
    assert summary.paid_expenses_minor >= 620000
    assert summary.unpaid_expenses_minor >= 35000
    assert "rto_transport" in summary.category_totals
    assert summary.category_totals["rto_transport"] >= 35000
