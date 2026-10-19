"""
test_vf2_supplier_finance.py — Unit and integration tests for VF2 supplier payments,
allocations, advances, supplier refunds, and period statement reconciliation.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.suppliers import Supplier
from app.models.supplier_finance import (
    LedgerDirection,
    LedgerEntryType,
    SupplierLedgerEntry,
    SupplierPaymentAllocation,
)
from app.schemas.supplier_finance import (
    AllocatePaymentRequest,
    ManualChargeRequest,
    ManualCreditNoteRequest,
    SupplierAdvanceRequest,
    SupplierPaymentAllocationItem,
    SupplierPaymentRequest,
    SupplierRefundRequest,
)
from app.services import supplier_finance as service


@pytest.fixture
def test_supplier(db_session: Session) -> Supplier:
    supplier = Supplier(
        name=f"VF2 Mill {uuid.uuid4().hex[:6]}",
        slug=f"vf2-mill-{uuid.uuid4().hex[:6]}",
        status="active",
    )
    db_session.add(supplier)
    db_session.commit()
    db_session.refresh(supplier)
    return supplier


@pytest.fixture
def other_supplier(db_session: Session) -> Supplier:
    supplier = Supplier(
        name=f"Other Supplier {uuid.uuid4().hex[:6]}",
        slug=f"other-supplier-{uuid.uuid4().hex[:6]}",
        status="active",
    )
    db_session.add(supplier)
    db_session.commit()
    db_session.refresh(supplier)
    return supplier


def test_post_supplier_payment_fifo(db_session: Session, test_supplier: Supplier):
    """Test payment automatically allocates against oldest unpaid charges in FIFO order."""
    today = date.today()

    # Charge A: 10,000 paisas (yesterday)
    c1 = service.post_manual_charge(
        db_session,
        supplier_id=test_supplier.id,
        payload=ManualChargeRequest(
            amount_minor=10000,
            reference="INV-A",
            effective_date=today - timedelta(days=2),
        ),
    )
    # Charge B: 15,000 paisas (today)
    c2 = service.post_manual_charge(
        db_session,
        supplier_id=test_supplier.id,
        payload=ManualChargeRequest(
            amount_minor=15000,
            reference="INV-B",
            effective_date=today,
        ),
    )

    summary_before = service.get_supplier_ledger_summary(db_session, test_supplier.id)
    assert summary_before["outstanding_payable_minor"] == 25000

    # Pay 12,000 with FIFO auto-allocation
    payment, allocs = service.post_supplier_payment(
        db_session,
        supplier_id=test_supplier.id,
        payload=SupplierPaymentRequest(
            amount_minor=12000,
            payment_method="bank_transfer",
            reference="TRX-101",
            effective_date=today,
            auto_allocate_fifo=True,
        ),
    )

    assert payment.entry_type == "payment"
    assert payment.direction == "debit"
    assert payment.amount_minor == 12000
    assert len(allocs) == 2

    # Allocations: 10,000 to INV-A, 2,000 to INV-B
    alloc_map = {a.charge_entry_id: a.allocated_amount_minor for a in allocs}
    assert alloc_map[c1.id] == 10000
    assert alloc_map[c2.id] == 2000

    summary_after = service.get_supplier_ledger_summary(db_session, test_supplier.id)
    # Outstanding payable: 25,000 - 12,000 = 13,000
    assert summary_after["outstanding_payable_minor"] == 13000
    assert summary_after["total_payments_minor"] == 12000
    assert summary_after["unallocated_advances_minor"] == 0


def test_post_supplier_payment_explicit_allocation(db_session: Session, test_supplier: Supplier):
    """Test paying with specific explicit charge allocations."""
    today = date.today()

    c1 = service.post_manual_charge(
        db_session,
        supplier_id=test_supplier.id,
        payload=ManualChargeRequest(amount_minor=20000, reference="INV-1", effective_date=today),
    )
    c2 = service.post_manual_charge(
        db_session,
        supplier_id=test_supplier.id,
        payload=ManualChargeRequest(amount_minor=30000, reference="INV-2", effective_date=today),
    )

    # Pay 25,000 allocating 15,000 to c2 and 10,000 to c1
    payment, allocs = service.post_supplier_payment(
        db_session,
        supplier_id=test_supplier.id,
        payload=SupplierPaymentRequest(
            amount_minor=25000,
            payment_method="bank_transfer",
            reference="TRX-EXPLICIT",
            effective_date=today,
            auto_allocate_fifo=False,
            allocations=[
                SupplierPaymentAllocationItem(charge_entry_id=c2.id, allocated_amount_minor=15000),
                SupplierPaymentAllocationItem(charge_entry_id=c1.id, allocated_amount_minor=10000),
            ],
        ),
    )

    assert len(allocs) == 2
    alloc_map = {a.charge_entry_id: a.allocated_amount_minor for a in allocs}
    assert alloc_map[c2.id] == 15000
    assert alloc_map[c1.id] == 10000

    summary = service.get_supplier_ledger_summary(db_session, test_supplier.id)
    assert summary["outstanding_payable_minor"] == 25000


def test_payment_allocation_exceeding_charge_rejected(db_session: Session, test_supplier: Supplier):
    """Test that allocating more than a charge's unpaid balance is rejected with HTTP 400."""
    today = date.today()
    c1 = service.post_manual_charge(
        db_session,
        supplier_id=test_supplier.id,
        payload=ManualChargeRequest(amount_minor=10000, reference="INV-LIMITED", effective_date=today),
    )

    with pytest.raises(HTTPException) as exc_info:
        service.post_supplier_payment(
            db_session,
            supplier_id=test_supplier.id,
            payload=SupplierPaymentRequest(
                amount_minor=15000,
                reference="TRX-OVERPAY",
                effective_date=today,
                allocations=[
                    SupplierPaymentAllocationItem(charge_entry_id=c1.id, allocated_amount_minor=15000)
                ],
            ),
        )
    assert exc_info.value.status_code == 400
    assert "exceeds unpaid balance" in exc_info.value.detail


def test_payment_cross_supplier_allocation_rejected(
    db_session: Session, test_supplier: Supplier, other_supplier: Supplier
):
    """Test that a payment cannot allocate to a charge belonging to another supplier."""
    today = date.today()
    other_charge = service.post_manual_charge(
        db_session,
        supplier_id=other_supplier.id,
        payload=ManualChargeRequest(amount_minor=10000, reference="INV-OTHER", effective_date=today),
    )

    with pytest.raises(HTTPException) as exc_info:
        service.post_supplier_payment(
            db_session,
            supplier_id=test_supplier.id,
            payload=SupplierPaymentRequest(
                amount_minor=10000,
                reference="TRX-CROSS",
                effective_date=today,
                allocations=[
                    SupplierPaymentAllocationItem(charge_entry_id=other_charge.id, allocated_amount_minor=10000)
                ],
            ),
        )
    assert exc_info.value.status_code == 400


def test_double_submit_payment_idempotency(db_session: Session, test_supplier: Supplier):
    """Test double-submitting a payment with the same idempotency key returns the existing payment."""
    today = date.today()
    c1 = service.post_manual_charge(
        db_session,
        supplier_id=test_supplier.id,
        payload=ManualChargeRequest(amount_minor=10000, reference="INV-IDEMP", effective_date=today),
    )

    p1, allocs1 = service.post_supplier_payment(
        db_session,
        supplier_id=test_supplier.id,
        payload=SupplierPaymentRequest(
            amount_minor=5000,
            reference="TRX-DOUBLE-SUBMIT",
            effective_date=today,
            idempotency_key="unique-token-999",
        ),
    )

    # Double submit same request
    p2, allocs2 = service.post_supplier_payment(
        db_session,
        supplier_id=test_supplier.id,
        payload=SupplierPaymentRequest(
            amount_minor=5000,
            reference="TRX-DOUBLE-SUBMIT",
            effective_date=today,
            idempotency_key="unique-token-999",
        ),
    )

    assert p1.id == p2.id
    # Only 1 payment entry exists in database
    count = db_session.query(SupplierLedgerEntry).filter_by(source_event_key=f"payment:{test_supplier.id}:unique-token-999").count()
    assert count == 1


def test_unallocated_payment_creates_advance(db_session: Session, test_supplier: Supplier):
    """Test payments exceeding charges store remainder as unallocated advance."""
    today = date.today()
    service.post_manual_charge(
        db_session,
        supplier_id=test_supplier.id,
        payload=ManualChargeRequest(amount_minor=5000, reference="INV-5K", effective_date=today),
    )

    # Pay 20,000 (5,000 allocated, 15,000 unallocated advance)
    payment, allocs = service.post_supplier_payment(
        db_session,
        supplier_id=test_supplier.id,
        payload=SupplierPaymentRequest(
            amount_minor=20000,
            reference="TRX-OVERPAY-ADVANCE",
            effective_date=today,
            auto_allocate_fifo=True,
        ),
    )

    assert len(allocs) == 1
    assert allocs[0].allocated_amount_minor == 5000

    summary = service.get_supplier_ledger_summary(db_session, test_supplier.id)
    assert summary["outstanding_payable_minor"] == 0
    assert summary["unallocated_advances_minor"] == 15000


def test_post_advance_and_manual_allocation(db_session: Session, test_supplier: Supplier):
    """Test posting an explicit advance and later allocating it to a new charge."""
    today = date.today()

    # 1. Post advance
    advance = service.post_supplier_advance(
        db_session,
        supplier_id=test_supplier.id,
        payload=SupplierAdvanceRequest(
            amount_minor=10000,
            reference="ADV-001",
            effective_date=today,
            notes="Upfront production advance",
        ),
    )
    assert advance.entry_type == "advance"
    assert advance.direction == "debit"

    # 2. Post new charge
    charge = service.post_manual_charge(
        db_session,
        supplier_id=test_supplier.id,
        payload=ManualChargeRequest(amount_minor=7000, reference="INV-LATER", effective_date=today),
    )

    # 3. Allocate 7,000 from advance to charge
    alloc = service.allocate_payment_advance(
        db_session,
        supplier_id=test_supplier.id,
        payment_entry_id=advance.id,
        payload=AllocatePaymentRequest(charge_entry_id=charge.id, amount_minor=7000),
    )
    assert alloc.allocated_amount_minor == 7000

    # 4. Check unpaid & unallocated helper
    unpaid_data = service.get_unpaid_charges_and_advances(db_session, test_supplier.id)
    assert len(unpaid_data["unpaid_charges"]) == 0
    assert len(unpaid_data["unallocated_payments"]) == 1
    assert unpaid_data["unallocated_payments"][0]["unallocated_amount_minor"] == 3000


def test_supplier_refund_received(db_session: Session, test_supplier: Supplier):
    """Test vendor returning cash to AlphaZee is recorded as refund_received (Credit direction)."""
    today = date.today()

    refund = service.post_supplier_refund(
        db_session,
        supplier_id=test_supplier.id,
        payload=SupplierRefundRequest(
            amount_minor=4000,
            refund_method="bank_transfer",
            reference="REF-VEND-01",
            effective_date=today,
            notes="Vendor cash refund for defective fabric batch",
        ),
    )

    assert refund.entry_type == "refund_received"
    assert refund.direction == "credit"
    assert refund.amount_minor == 4000


def test_period_statement_reconciliation(db_session: Session, test_supplier: Supplier):
    """
    Test exact period statement reconciliation:
    Opening Payable + Net Movement == Closing Payable, matching running balance down to the paisa.
    """
    base_date = date(2026, 10, 1)

    # Prior charge before statement start (Day 1)
    service.post_manual_charge(
        db_session,
        supplier_id=test_supplier.id,
        payload=ManualChargeRequest(amount_minor=10000, reference="INV-PRIOR", effective_date=base_date + timedelta(days=1)),
    )

    # Statement Period: Day 5 to Day 15
    start_date = base_date + timedelta(days=5)
    end_date = base_date + timedelta(days=15)

    # In period: Charge 20,000 (Day 6)
    c_period = service.post_manual_charge(
        db_session,
        supplier_id=test_supplier.id,
        payload=ManualChargeRequest(amount_minor=20000, reference="INV-IN-PERIOD", effective_date=base_date + timedelta(days=6)),
    )

    # In period: Payment 15,000 (Day 7)
    service.post_supplier_payment(
        db_session,
        supplier_id=test_supplier.id,
        payload=SupplierPaymentRequest(
            amount_minor=15000,
            reference="TRX-PERIOD",
            effective_date=base_date + timedelta(days=7),
            auto_allocate_fifo=True,
        ),
    )

    # In period: Credit Note 3,000 (Day 8)
    service.post_manual_credit_note(
        db_session,
        supplier_id=test_supplier.id,
        payload=ManualCreditNoteRequest(
            amount_minor=3000,
            reference="CN-PERIOD",
            effective_date=base_date + timedelta(days=8),
        ),
    )

    # In period: Refund Received 2,000 (Day 9)
    service.post_supplier_refund(
        db_session,
        supplier_id=test_supplier.id,
        payload=SupplierRefundRequest(
            amount_minor=2000,
            reference="REF-PERIOD",
            effective_date=base_date + timedelta(days=9),
        ),
    )

    # Outside period: Charge 5,000 (Day 20)
    service.post_manual_charge(
        db_session,
        supplier_id=test_supplier.id,
        payload=ManualChargeRequest(amount_minor=5000, reference="INV-AFTER", effective_date=base_date + timedelta(days=20)),
    )

    # Generate Statement for [Day 5, Day 15]
    stmt = service.get_supplier_statement(
        db_session,
        supplier_id=test_supplier.id,
        start_date=start_date,
        end_date=end_date,
    )

    assert stmt["opening_payable_minor"] == 10000
    assert stmt["charges_in_period_minor"] == 20000
    assert stmt["payments_in_period_minor"] == 15000
    assert stmt["credits_in_period_minor"] == 3000
    assert stmt["refunds_in_period_minor"] == 2000

    # Net movement = (20,000 charges + 2,000 refund) - (15,000 payment + 3,000 credit note) = +4,000
    assert stmt["net_movement_minor"] == 4000
    # Closing = Opening (10,000) + Net Movement (4,000) = 14,000
    assert stmt["closing_payable_minor"] == 14000

    # Entries in period = 4
    assert len(stmt["entries"]) == 4
    # The running balance on the last entry must strictly equal closing_payable_minor
    assert stmt["entries"][-1]["running_payable_minor"] == 14000
