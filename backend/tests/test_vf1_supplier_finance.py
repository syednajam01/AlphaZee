"""Tests for Phase VF1: Supplier Agreements, Immutable Ledger Entries,
Manual Charges/Credit Notes, Opening Balance Preview/Apply, and Idempotent Event Posting.
"""
from datetime import date
import uuid
import pytest
from fastapi import HTTPException
from app.models.orders import Order, OrderLine
from app.models.suppliers import Supplier
from app.models.supplier_finance import SupplierAgreement, SupplierLedgerEntry
from app.services.supplier_finance import (
    get_or_create_supplier_agreement,
    update_supplier_agreement,
    post_manual_charge,
    post_manual_credit_note,
    reverse_ledger_entry,
    preview_opening_balance,
    apply_opening_balance,
    post_event_liability_if_applicable,
    get_supplier_ledger_summary,
    list_supplier_ledger_entries,
)
from app.schemas.supplier_finance import (
    SupplierAgreementUpdateRequest,
    ManualChargeRequest,
    ManualCreditNoteRequest,
    ReverseLedgerEntryRequest,
    OpeningBalanceRequest,
)


@pytest.fixture
def test_supplier(db_session):
    supplier = Supplier(
        name="Test Textile Mills",
        slug=f"test-textile-mills-{uuid.uuid4().hex[:6]}",
        status="active",
        notes="Contact: Vendor Rep, Phone: 03001234567",
    )
    db_session.add(supplier)
    db_session.flush()
    return supplier


def test_default_agreement_creation_defaults_to_manual(db_session, test_supplier):
    agreement = get_or_create_supplier_agreement(db_session, test_supplier.id)
    assert agreement is not None
    assert agreement.payable_trigger == "manual"
    assert agreement.payment_terms_days == 0
    assert agreement.is_active is True


def test_update_agreement_triggers(db_session, test_supplier):
    get_or_create_supplier_agreement(db_session, test_supplier.id)
    payload = SupplierAgreementUpdateRequest(
        payable_trigger="dispatch",
        payment_terms_days=14,
        notes="Net 14 payment terms on dispatch",
    )
    updated = update_supplier_agreement(db_session, test_supplier.id, payload)
    assert updated.payable_trigger == "dispatch"
    assert updated.payment_terms_days == 14
    assert updated.notes == "Net 14 payment terms on dispatch"


def test_manual_charge_and_credit_note_ledger_flow(db_session, test_supplier):
    get_or_create_supplier_agreement(db_session, test_supplier.id)

    # 1. Post manual charge (liability to supplier, direction=credit, PKR 5,000)
    charge_payload = ManualChargeRequest(
        amount_minor=500000,
        reference="BILL-001",
        effective_date=date.today(),
        notes="Batch of 10 shirts delivered directly to hub",
    )
    charge_entry = post_manual_charge(db_session, test_supplier.id, charge_payload)
    assert charge_entry.amount_minor == 500000
    assert charge_entry.direction == "credit"
    assert charge_entry.entry_type == "charge"
    assert charge_entry.status == "posted"

    # Verify summary
    summary = get_supplier_ledger_summary(db_session, test_supplier.id)
    assert summary["total_charges_minor"] == 500000
    assert summary["total_credits_minor"] == 0
    assert summary["outstanding_payable_minor"] == 500000

    # 2. Post manual credit note (e.g. vendor rebate / fabric flaw discount, PKR 1,000)
    cn_payload = ManualCreditNoteRequest(
        amount_minor=100000,
        reference="CN-001",
        effective_date=date.today(),
        notes="Fabric stain allowance on item 4",
    )
    cn_entry = post_manual_credit_note(db_session, test_supplier.id, cn_payload)
    assert cn_entry.amount_minor == 100000
    assert cn_entry.direction == "debit"
    assert cn_entry.entry_type == "credit_note"
    assert cn_entry.status == "posted"

    # Verify summary after credit note: 500,000 - 100,000 = 400,000
    summary2 = get_supplier_ledger_summary(db_session, test_supplier.id)
    assert summary2["total_charges_minor"] == 500000
    assert summary2["total_credits_minor"] == 100000
    assert summary2["outstanding_payable_minor"] == 400000


def test_immutable_reversal(db_session, test_supplier):
    get_or_create_supplier_agreement(db_session, test_supplier.id)

    charge_payload = ManualChargeRequest(
        amount_minor=200000,
        reference="ERR-001",
        effective_date=date.today(),
        notes="Erroneous charge to reverse",
    )
    entry = post_manual_charge(db_session, test_supplier.id, charge_payload)

    # Reverse entry
    reversal_adj = reverse_ledger_entry(
        db_session,
        entry.id,
        reason="Entered in error by operator; correct vendor is ABC",
    )

    # Reversal adjustment entry should be direction=debit, amount_minor=200,000, type=adjustment
    assert reversal_adj.direction == "debit"
    assert reversal_adj.amount_minor == 200000
    assert reversal_adj.entry_type == "adjustment"
    assert reversal_adj.reversal_entry_id == entry.id

    # Original entry should be marked reversed
    db_session.refresh(entry)
    assert entry.status == "reversed"

    # Balance should now be 0
    summary = get_supplier_ledger_summary(db_session, test_supplier.id)
    assert summary["outstanding_payable_minor"] == 0

    # Attempting to reverse again should raise HTTPException 400
    with pytest.raises(HTTPException) as exc_info:
        reverse_ledger_entry(
            db_session,
            entry.id,
            reason="Second reversal attempt",
        )
    assert exc_info.value.status_code == 400
    assert "already reversed" in exc_info.value.detail


def test_opening_balance_preview_and_apply(db_session, test_supplier):
    get_or_create_supplier_agreement(db_session, test_supplier.id)

    req = OpeningBalanceRequest(
        amount_minor=750000,
        direction="credit",
        as_of_date=date(2026, 10, 1),
        reference="AUDIT-2026-10",
        notes="Historical unpaid supplier invoices prior to AlphaZee launch",
    )
    preview = preview_opening_balance(db_session, test_supplier.id, req)
    assert preview["current_outstanding_minor"] == 0
    assert preview["amount_minor"] == 750000
    assert preview["projected_outstanding_minor"] == 750000

    # Apply
    entry = apply_opening_balance(db_session, test_supplier.id, req)
    assert entry.entry_type == "opening_balance"
    assert entry.amount_minor == 750000
    assert entry.direction == "credit"

    summary = get_supplier_ledger_summary(db_session, test_supplier.id)
    assert summary["outstanding_payable_minor"] == 750000

    # Cannot apply opening balance with duplicate date/supplier
    with pytest.raises(HTTPException) as exc_info:
        apply_opening_balance(db_session, test_supplier.id, req)
    assert exc_info.value.status_code == 409


from app.models.catalog import Collection, Product, Variant, AvailabilityStatus
from app.models.inventory import SupplierVariant


def test_idempotent_event_posting(db_session, test_supplier):
    # Set trigger to 'dispatch'
    update_supplier_agreement(
        db_session,
        test_supplier.id,
        SupplierAgreementUpdateRequest(payable_trigger="dispatch"),
    )

    uid = uuid.uuid4().hex[:8]
    col = Collection(id=f"col-{uid}", name="Test Col", slug=f"col-{uid}", display_order=0)
    db_session.add(col)
    db_session.flush()

    prod = Product(id=f"prod-{uid}", slug=f"prod-{uid}", title="Test Product", collection_id=col.id, is_active=True)
    db_session.add(prod)
    db_session.flush()

    var = Variant(sku=f"SKU-{uid}", product_id=prod.id, size="M", color="Black", price_minor=250000, is_active=True, availability=AvailabilityStatus.AVAILABLE)
    db_session.add(var)
    db_session.flush()

    sv = SupplierVariant(supplier_id=test_supplier.id, variant_id=var.id, active=True, supplier_cost_minor=150000)
    db_session.add(sv)
    db_session.flush()

    order = Order(
        order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
        order_status="placed",
        payment_status="pending",
        payment_method="cod",
        customer_name="Test Buyer",
        customer_phone="03001234567",
        shipping_address_line1="123 Mall Road",
        shipping_city="Lahore",
        shipping_province="Punjab",
        subtotal_minor=500000,
        total_minor=500000,
    )
    db_session.add(order)
    db_session.flush()

    line = OrderLine(
        order_id=order.id,
        variant_id=var.id,
        product_title_snapshot="Test Shirt",
        variant_sku_snapshot=var.sku,
        quantity=2,
        unit_price_minor=250000,
        unit_cost_minor=150000,
        line_total_minor=500000,
    )
    db_session.add(line)
    db_session.flush()
    db_session.refresh(order)
    # Capture the acquisition when stock is reserved, as real checkout does.
    from app.models.inventory import InventoryBalance
    from app.queries.reservations import create_stock_reservation
    db_session.add(InventoryBalance(supplier_variant_id=sv.id, on_hand=2))
    db_session.flush()
    create_stock_reservation(db_session, supplier_variant_id=sv.id, order_line_id=line.id, quantity=2)

    # 1. Trigger event 'dispatch'
    entries1 = post_event_liability_if_applicable(
        db_session,
        order=order,
        trigger_type="dispatch",
    )
    assert len(entries1) == 1
    assert entries1[0].amount_minor == 300000  # 150000 * 2
    assert entries1[0].direction == "credit"
    assert entries1[0].entry_type == "charge"

    # 2. Trigger the exact same event again -> Idempotency check returns empty, no duplicate entry
    entries2 = post_event_liability_if_applicable(
        db_session,
        order=order,
        trigger_type="dispatch",
    )
    assert len(entries2) == 0

    # Verify only 1 entry exists in ledger
    entries, total, summary = list_supplier_ledger_entries(db_session, test_supplier.id)
    assert total == 1
    assert entries[0]["id"] == entries1[0].id
    assert summary["outstanding_payable_minor"] == 300000

    # 3. Non-matching event (e.g. delivery when trigger is dispatch) -> returns empty
    entries3 = post_event_liability_if_applicable(
        db_session,
        order=order,
        trigger_type="delivery",
    )
    assert len(entries3) == 0


def test_api_endpoints_owner_authenticated(admin_client, test_supplier):
    # Test GET agreement
    res = admin_client.get(f"/api/v1/admin/suppliers/{test_supplier.id}/agreement")
    assert res.status_code == 200
    data = res.json()
    assert data["payable_trigger"] == "manual"

    # Test PUT agreement
    put_res = admin_client.put(
        f"/api/v1/admin/suppliers/{test_supplier.id}/agreement",
        json={"payable_trigger": "confirmed_pickup", "payment_terms_days": 7, "notes": "Pickup agreement"},
    )
    assert put_res.status_code == 200
    assert put_res.json()["payable_trigger"] == "confirmed_pickup"

    # Test POST manual charge
    charge_res = admin_client.post(
        f"/api/v1/admin/suppliers/{test_supplier.id}/ledger/charge",
        json={
            "amount_minor": 125000,
            "reference": "API-CHG-1",
            "effective_date": date.today().isoformat(),
            "notes": "Via Admin API",
        },
    )
    assert charge_res.status_code == 201
    charge_data = charge_res.json()
    assert charge_data["amount_minor"] == 125000
    charge_id = charge_data["id"]

    # Test GET ledger summary
    sum_res = admin_client.get(f"/api/v1/admin/suppliers/{test_supplier.id}/ledger/summary")
    assert sum_res.status_code == 200
    assert sum_res.json()["outstanding_payable_minor"] == 125000

    # Test POST reverse charge
    rev_res = admin_client.post(
        f"/api/v1/admin/suppliers/{test_supplier.id}/ledger/{charge_id}/reverse",
        json={"reason": "Testing reversal endpoint"},
    )
    assert rev_res.status_code == 201
    assert rev_res.json()["entry_type"] == "adjustment"

    # Test GET ledger entries
    list_res = admin_client.get(f"/api/v1/admin/suppliers/{test_supplier.id}/ledger")
    assert list_res.status_code == 200
    assert len(list_res.json()["entries"]) == 2  # Original charge + reversal adjustment
