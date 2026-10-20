"""Real independent PostgreSQL transactions; never the application database."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy import delete, select, func
from sqlalchemy.orm import Session
from app.models.suppliers import Supplier
from app.models.supplier_finance import SupplierLedgerEntry, SupplierPaymentAllocation
from app.schemas.supplier_finance import AllocatePaymentRequest, SupplierPaymentRequest
from app.services.supplier_finance import allocate_payment_advance, post_supplier_payment


@pytest.fixture
def ledger(test_engine):
    with Session(test_engine, autoflush=False) as db:
        supplier = Supplier(name='SAMPLE concurrency', slug=f'concurrency-{uuid.uuid4().hex}', status='active')
        db.add(supplier); db.flush()
        supplier_id = supplier.id
        charge = SupplierLedgerEntry(supplier_id=supplier_id, entry_type='charge', direction='credit',
            amount_minor=10000, reference='SAMPLE charge', effective_date=date.today(), status='posted')
        payments = [SupplierLedgerEntry(supplier_id=supplier_id, entry_type='advance', direction='debit',
            amount_minor=10000, reference=f'SAMPLE advance {i}', effective_date=date.today(), status='posted') for i in range(2)]
        db.add_all([charge, *payments]); db.commit()
        ids = (charge.id, [p.id for p in payments])
    try:
        yield supplier_id, *ids
    finally:
        with Session(test_engine) as db:
            entry_ids = select(SupplierLedgerEntry.id).where(SupplierLedgerEntry.supplier_id == supplier_id)
            db.execute(delete(SupplierPaymentAllocation).where(SupplierPaymentAllocation.payment_entry_id.in_(entry_ids)))
            db.execute(delete(SupplierLedgerEntry).where(SupplierLedgerEntry.supplier_id == supplier_id))
            db.execute(delete(Supplier).where(Supplier.id == supplier_id)); db.commit()


def test_two_allocations_cannot_overpay_one_charge(test_engine, ledger):
    supplier, charge, payments = ledger
    barrier = Barrier(2)
    def allocate(payment):
        with Session(test_engine, autoflush=False) as db:
            barrier.wait(timeout=10)
            try:
                allocate_payment_advance(db, supplier, payment, AllocatePaymentRequest(
                    charge_entry_id=charge, amount_minor=7000))
                return 'allocated'
            except HTTPException:
                db.rollback(); return 'rejected'
    with ThreadPoolExecutor(max_workers=2) as workers:
        outcomes = list(workers.map(allocate, payments))
    assert sorted(outcomes) == ['allocated', 'rejected']
    with Session(test_engine) as db:
        assert db.scalar(select(func.sum(SupplierPaymentAllocation.allocated_amount_minor)).where(
            SupplierPaymentAllocation.charge_entry_id == charge)) == 7000


def test_concurrent_same_payment_key_posts_once(test_engine, ledger):
    supplier = ledger[0]
    barrier = Barrier(2)
    key = f'pay_{uuid.uuid4().hex}'
    def pay(_):
        with Session(test_engine, autoflush=False) as db:
            barrier.wait(timeout=10)
            entry, _ = post_supplier_payment(db, supplier, SupplierPaymentRequest(
                amount_minor=5000, reference='SAMPLE repeated payment', effective_date=date.today(),
                payment_method='bank_transfer', idempotency_key=key))
            return entry.id
    with ThreadPoolExecutor(max_workers=2) as workers:
        ids = list(workers.map(pay, range(2)))
    assert ids[0] == ids[1]
    with Session(test_engine) as db:
        assert db.scalar(select(func.count(SupplierLedgerEntry.id)).where(
            SupplierLedgerEntry.supplier_id == supplier, SupplierLedgerEntry.entry_type == 'payment')) == 1
