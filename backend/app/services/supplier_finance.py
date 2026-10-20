"""
supplier_finance.py — Business logic and service functions for supplier agreements, liabilities, and ledger.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Sequence

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.inventory import SupplierVariant
from app.models.orders import Order, OrderLine
from app.models.suppliers import Supplier
from app.models.supplier_finance import (
    LedgerDirection,
    LedgerEntryType,
    PayableTrigger,
    SupplierAgreement,
    SupplierLedgerEntry,
    SupplierPaymentAllocation,
)
from app.schemas.supplier_finance import (
    AllocatePaymentRequest,
    ManualChargeRequest,
    ManualCreditNoteRequest,
    OpeningBalanceRequest,
    PayableTriggerType,
    SupplierAdvanceRequest,
    SupplierAgreementUpdateRequest,
    SupplierPaymentAllocationItem,
    SupplierPaymentRequest,
    SupplierRefundRequest,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_or_create_supplier_agreement(db: Session, supplier_id: uuid.UUID) -> SupplierAgreement:
    """Fetch active supplier agreement or create unconfigured manual-only default."""
    supplier = db.scalar(select(Supplier).where(Supplier.id == supplier_id).with_for_update())
    if not supplier:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Supplier {supplier_id} not found")

    agreement = db.scalars(
        select(SupplierAgreement)
        .where(SupplierAgreement.supplier_id == supplier_id, SupplierAgreement.is_active.is_(True))
        .order_by(SupplierAgreement.created_at.desc())
    ).first()

    if not agreement:
        agreement = SupplierAgreement(
            supplier_id=supplier_id,
            payable_trigger=PayableTrigger.MANUAL.value,
            payment_terms_days=0,
            is_active=True,
            effective_from=_utcnow(),
            notes="Default unconfigured manual-only agreement",
        )
        db.add(agreement)
        db.flush()
        db.refresh(agreement)

    return agreement


def update_supplier_agreement(
    db: Session,
    supplier_id: uuid.UUID,
    payload: SupplierAgreementUpdateRequest,
    actor_id: uuid.UUID | None = None,
) -> SupplierAgreement:
    """Update supplier settlement agreement terms (applies strictly to future transactions)."""
    supplier = db.scalar(select(Supplier).where(Supplier.id == supplier_id).with_for_update())
    if not supplier:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Supplier {supplier_id} not found")

    # Deactivate older agreements for clean versioning
    existing = db.scalars(
        select(SupplierAgreement).where(
            SupplierAgreement.supplier_id == supplier_id, SupplierAgreement.is_active.is_(True)
        )
    ).all()
    for ag in existing:
        ag.is_active = False

    new_agreement = SupplierAgreement(
        supplier_id=supplier_id,
        payable_trigger=payload.payable_trigger,
        payment_terms_days=payload.payment_terms_days,
        is_active=True,
        effective_from=_utcnow(),
        notes=payload.notes,
    )
    db.add(new_agreement)
    db.flush()
    db.commit()
    db.refresh(new_agreement)
    return new_agreement


def get_supplier_ledger_summary(db: Session, supplier_id: uuid.UUID) -> dict:
    """Calculate real-time supplier liability, payments, credits, and unallocated advances."""
    supplier = db.scalar(select(Supplier).where(Supplier.id == supplier_id).with_for_update())
    if not supplier:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Supplier {supplier_id} not found")

    agreement = get_or_create_supplier_agreement(db, supplier_id)

    rows = list(db.scalars(select(SupplierLedgerEntry).where(SupplierLedgerEntry.supplier_id == supplier_id)))
    by_id = {row.id: row for row in rows}
    charges_sum = credits_sum = payments_sum = refunds_sum = 0
    for row in rows:
        # A reversal is a new movement; retaining its original in totals preserves history.
        kind = by_id[row.reversal_entry_id].entry_type if row.reversal_entry_id in by_id else row.entry_type
        signed = row.amount_minor if row.direction == 'credit' else -row.amount_minor
        if kind in {'charge', 'opening_balance', 'adjustment'}:
            charges_sum += signed
        elif kind == 'credit_note':
            credits_sum -= signed
        elif kind in {'payment', 'advance'}:
            payments_sum -= signed
        elif kind == 'refund_received':
            refunds_sum += signed
    allocated_sum = db.scalar(select(func.coalesce(func.sum(SupplierPaymentAllocation.allocated_amount_minor), 0))
        .join(SupplierLedgerEntry, SupplierLedgerEntry.id == SupplierPaymentAllocation.payment_entry_id)
        .where(SupplierLedgerEntry.supplier_id == supplier_id)) or 0
    outstanding_payable = charges_sum - credits_sum - allocated_sum
    unallocated_advances = payments_sum - allocated_sum - refunds_sum

    return {
        "supplier_id": supplier_id,
        "supplier_name": supplier.name,
        "agreement_trigger": agreement.payable_trigger,
        "payment_terms_days": agreement.payment_terms_days,
        "total_charges_minor": charges_sum,
        "total_credits_minor": credits_sum,
        "total_payments_minor": payments_sum,
        "outstanding_payable_minor": outstanding_payable,
        "unallocated_advances_minor": unallocated_advances,
    }


def list_supplier_ledger_entries(
    db: Session,
    supplier_id: uuid.UUID,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[dict], int, dict]:
    """List reverse-chronological ledger entries with allocation breakdown and summary."""
    summary = get_supplier_ledger_summary(db, supplier_id)

    stmt = (
        select(SupplierLedgerEntry)
        .where(SupplierLedgerEntry.supplier_id == supplier_id)
        .order_by(
            SupplierLedgerEntry.effective_date.desc(),
            SupplierLedgerEntry.recorded_at.desc(),
        )
    )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()

    # Pre-fetch allocations for returned rows
    row_ids = [r.id for r in rows]
    allocs = db.execute(
        select(
            SupplierPaymentAllocation.payment_entry_id,
            SupplierPaymentAllocation.charge_entry_id,
            SupplierPaymentAllocation.allocated_amount_minor,
        ).where(
            or_(
                SupplierPaymentAllocation.payment_entry_id.in_(row_ids),
                SupplierPaymentAllocation.charge_entry_id.in_(row_ids),
            )
        )
    ).all()

    payment_alloc_map: dict[uuid.UUID, int] = {}
    charge_alloc_map: dict[uuid.UUID, int] = {}
    for p_id, c_id, amt in allocs:
        payment_alloc_map[p_id] = payment_alloc_map.get(p_id, 0) + amt
        charge_alloc_map[c_id] = charge_alloc_map.get(c_id, 0) + amt

    results = []
    for entry in rows:
        allocated = 0
        if entry.entry_type in ("payment", "advance"):
            allocated = payment_alloc_map.get(entry.id, 0)
        elif entry.entry_type in ("charge", "opening_balance"):
            allocated = charge_alloc_map.get(entry.id, 0)

        unallocated = max(0, entry.amount_minor - allocated) if entry.status == "posted" else 0

        d = {
            "id": entry.id,
            "supplier_id": entry.supplier_id,
            "entry_type": entry.entry_type,
            "amount_minor": entry.amount_minor,
            "direction": entry.direction,
            "source_event_key": entry.source_event_key,
            "order_id": entry.order_id,
            "order_line_id": entry.order_line_id,
            "shipment_id": entry.shipment_id,
            "reference": entry.reference,
            "effective_date": entry.effective_date,
            "status": entry.status,
            "reversal_entry_id": entry.reversal_entry_id,
            "notes": entry.notes,
            "recorded_by_user_id": entry.recorded_by_user_id,
            "recorded_at": entry.recorded_at,
            "allocated_amount_minor": allocated,
            "unallocated_amount_minor": unallocated,
        }
        results.append(d)

    return results, total, summary


def post_manual_charge(
    db: Session,
    supplier_id: uuid.UUID,
    payload: ManualChargeRequest,
    actor_id: uuid.UUID | None = None,
) -> SupplierLedgerEntry:
    """Manually post an approved supplier charge (increases liability)."""
    supplier = db.scalar(select(Supplier).where(Supplier.id == supplier_id).with_for_update())
    if not supplier:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Supplier {supplier_id} not found")

    entry = SupplierLedgerEntry(
        supplier_id=supplier_id,
        entry_type=LedgerEntryType.CHARGE.value,
        amount_minor=payload.amount_minor,
        direction=LedgerDirection.CREDIT.value,
        source_event_key=None,
        order_id=payload.order_id,
        order_line_id=payload.order_line_id,
        reference=payload.reference,
        effective_date=payload.effective_date,
        status="posted",
        notes=payload.notes,
        recorded_by_user_id=actor_id,
        recorded_at=_utcnow(),
    )
    db.add(entry)
    db.flush()
    db.commit()
    db.refresh(entry)
    return entry


def post_manual_credit_note(
    db: Session,
    supplier_id: uuid.UUID,
    payload: ManualCreditNoteRequest,
    actor_id: uuid.UUID | None = None,
) -> SupplierLedgerEntry:
    """Manually post an acknowledged vendor credit note (decreases liability)."""
    supplier = db.scalar(select(Supplier).where(Supplier.id == supplier_id).with_for_update())
    if not supplier:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Supplier {supplier_id} not found")

    entry = SupplierLedgerEntry(
        supplier_id=supplier_id,
        entry_type=LedgerEntryType.CREDIT_NOTE.value,
        amount_minor=payload.amount_minor,
        direction=LedgerDirection.DEBIT.value,
        source_event_key=None,
        order_id=payload.order_id,
        reference=payload.reference,
        effective_date=payload.effective_date,
        status="posted",
        notes=payload.notes,
        recorded_by_user_id=actor_id,
        recorded_at=_utcnow(),
    )
    db.add(entry)
    db.flush()
    db.commit()
    db.refresh(entry)
    return entry


def reverse_ledger_entry(
    db: Session,
    entry_id: uuid.UUID,
    reason: str,
    actor_id: uuid.UUID | None = None,
) -> SupplierLedgerEntry:
    """
    Immutably reverse a posted ledger entry by generating an opposing adjustment.
    Never alters or deletes the historical original entry.
    """
    entry = db.scalar(select(SupplierLedgerEntry).where(SupplierLedgerEntry.id == entry_id).with_for_update())
    if not entry:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Ledger entry {entry_id} not found")

    if entry.status == "reversed":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Entry is already reversed")
    if entry.reversal_entry_id is not None:
        raise HTTPException(400, 'A reversal cannot itself be reversed. Record an explicit new correction.')

    # Check if entry is tied to allocations
    has_allocs = db.scalar(
        select(func.count(SupplierPaymentAllocation.id)).where(
            or_(
                SupplierPaymentAllocation.payment_entry_id == entry_id,
                SupplierPaymentAllocation.charge_entry_id == entry_id,
            )
        )
    )
    if has_allocs and has_allocs > 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Cannot reverse entry with active payment allocations. Deallocate first.",
        )

    # Mark original as reversed
    entry.status = "reversed"

    # Determine opposing direction
    opposing_direction = (
        LedgerDirection.DEBIT.value
        if entry.direction == LedgerDirection.CREDIT.value
        else LedgerDirection.CREDIT.value
    )

    reversal = SupplierLedgerEntry(
        supplier_id=entry.supplier_id,
        entry_type=LedgerEntryType.ADJUSTMENT.value,
        amount_minor=entry.amount_minor,
        direction=opposing_direction,
        source_event_key=None,
        order_id=entry.order_id,
        order_line_id=entry.order_line_id,
        shipment_id=entry.shipment_id,
        reference=f"Reversal of {entry.reference}",
        effective_date=date.today(),
        status="posted",
        reversal_entry_id=entry.id,
        notes=f"Reversal reason: {reason}",
        recorded_by_user_id=actor_id,
        recorded_at=_utcnow(),
    )
    db.add(reversal)
    db.flush()
    db.commit()
    db.refresh(reversal)
    return reversal


def preview_opening_balance(
    db: Session,
    supplier_id: uuid.UUID,
    payload: OpeningBalanceRequest,
) -> dict:
    """Preview the exact financial impact of an opening balance entry before committing."""
    supplier = db.scalar(select(Supplier).where(Supplier.id == supplier_id).with_for_update())
    if not supplier:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Supplier {supplier_id} not found")

    summary = get_supplier_ledger_summary(db, supplier_id)
    current_out = summary["outstanding_payable_minor"]

    if payload.direction == "credit":
        projected = current_out + payload.amount_minor
    else:
        projected = current_out - payload.amount_minor

    return {
        "supplier_id": supplier_id,
        "supplier_name": supplier.name,
        "amount_minor": payload.amount_minor,
        "direction": payload.direction,
        "as_of_date": payload.as_of_date,
        "reference": payload.reference,
        "notes": payload.notes,
        "current_outstanding_minor": current_out,
        "projected_outstanding_minor": projected,
    }


def apply_opening_balance(
    db: Session,
    supplier_id: uuid.UUID,
    payload: OpeningBalanceRequest,
    actor_id: uuid.UUID | None = None,
) -> SupplierLedgerEntry:
    """Commit a validated opening balance entry with audit reference."""
    supplier = db.scalar(select(Supplier).where(Supplier.id == supplier_id).with_for_update())
    if not supplier:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Supplier {supplier_id} not found")

    entry = SupplierLedgerEntry(
        supplier_id=supplier_id,
        entry_type=LedgerEntryType.OPENING_BALANCE.value,
        amount_minor=payload.amount_minor,
        direction=payload.direction,
        source_event_key=f"opening_balance:{supplier_id}:{payload.as_of_date.isoformat()}",
        reference=payload.reference,
        effective_date=payload.as_of_date,
        status="posted",
        notes=payload.notes,
        recorded_by_user_id=actor_id,
        recorded_at=_utcnow(),
    )
    db.add(entry)
    try:
        db.flush()
        db.commit()
        db.refresh(entry)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "An opening balance with this cut-off date already exists for this supplier.",
        )
    return entry


def post_event_liability_if_applicable(
    db: Session, order: Order, trigger_type: PayableTriggerType,
    shipment_id: uuid.UUID | None = None, actor_id: uuid.UUID | None = None,
) -> list[SupplierLedgerEntry]:
    """Post once per acquisition, using purchase snapshots in the caller's transaction."""
    from datetime import timedelta
    from zoneinfo import ZoneInfo
    from app.models.shipments import ShipmentAllocation
    from app.models.inventory import StockReservation
    db.flush()  # Production sessions disable autoflush; include the new exact allocations.
    db.scalar(select(Order).where(Order.id == order.id).with_for_update())
    lines = list(db.scalars(select(OrderLine).where(OrderLine.order_id == order.id)))
    if shipment_id:
        ids = set(db.scalars(select(StockReservation.order_line_id).join(
            ShipmentAllocation, ShipmentAllocation.reservation_id == StockReservation.id).where(
                ShipmentAllocation.shipment_id == shipment_id)))
        lines = [line for line in lines if line.id in ids]
    created = []
    for line in lines:
        snapshot = line.acquisition_snapshot
        # Historical purchases never inherit today's supplier or agreement.
        if not snapshot or snapshot['payable_trigger'] != trigger_type:
            continue
        quantity = snapshot['vendor_quantity']
        if not quantity:
            continue
        source_key = f'acquisition:{line.id}'
        if db.scalar(select(SupplierLedgerEntry.id).where(
                SupplierLedgerEntry.order_line_id == line.id,
                SupplierLedgerEntry.entry_type == 'charge')):
            continue
        vendor_segments = [s for s in snapshot['segments'] if not s['owned']]
        amount = sum(s['quantity'] * s['unit_cost_minor'] for s in vendor_segments)
        if not amount:
            continue
        event_date = _utcnow().astimezone(timezone(timedelta(hours=5))).date()
        due_date = event_date + timedelta(days=snapshot['payment_terms_days'])
        entry = SupplierLedgerEntry(
            supplier_id=uuid.UUID(snapshot['supplier_id']), entry_type='charge',
            direction='credit', amount_minor=amount, source_event_key=source_key,
            order_id=order.id, order_line_id=line.id, shipment_id=shipment_id,
            reference=f'PO #{order.order_number} ({trigger_type})', effective_date=event_date,
            status='posted', recorded_by_user_id=actor_id, recorded_at=_utcnow(),
            notes=f"Agreement {snapshot['agreement_id']}; due {due_date.isoformat()}; {quantity} vendor units")
        db.add(entry)
        created.append(entry)
    db.flush()
    return created


def post_supplier_payment(
    db: Session,
    supplier_id: uuid.UUID,
    payload: SupplierPaymentRequest,
    actor_id: uuid.UUID | None = None,
) -> tuple[SupplierLedgerEntry, list[SupplierPaymentAllocation]]:
    """
    Post a supplier payment and allocate against charges.
    Supports idempotency, row-level locking to prevent concurrent overpayment,
    and partial payments with unallocated portion preserved as advance.
    """
    supplier = db.scalar(select(Supplier).where(Supplier.id == supplier_id).with_for_update())
    if not supplier:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Supplier {supplier_id} not found")

    source_key = (
        f"payment:{supplier_id}:{payload.idempotency_key}"
        if payload.idempotency_key
        else None
    )
    if source_key:
        existing = db.scalar(
            select(SupplierLedgerEntry).where(
                SupplierLedgerEntry.source_event_key == source_key
            )
        )
        if existing:
            # Idempotent response: payment already recorded
            if (existing.amount_minor != payload.amount_minor or existing.reference != payload.reference
                    or existing.effective_date != payload.effective_date):
                raise HTTPException(409, 'This payment key belongs to different payment details.')
            existing_allocs = db.scalars(
                select(SupplierPaymentAllocation).where(
                    SupplierPaymentAllocation.payment_entry_id == existing.id
                )
            ).all()
            return existing, list(existing_allocs)

    # 1. Create the payment ledger entry (Debit direction reduces liability)
    payment_entry = SupplierLedgerEntry(
        supplier_id=supplier_id,
        entry_type=LedgerEntryType.PAYMENT.value,
        amount_minor=payload.amount_minor,
        direction=LedgerDirection.DEBIT.value,
        source_event_key=source_key,
        reference=payload.reference,
        effective_date=payload.effective_date,
        status="posted",
        notes=f"Payment via {payload.payment_method}. {payload.notes or ''}".strip(),
        recorded_by_user_id=actor_id,
        recorded_at=_utcnow(),
    )
    db.add(payment_entry)
    db.flush()

    created_allocations: list[SupplierPaymentAllocation] = []
    remaining_payment_minor = payload.amount_minor

    # 2. Allocations
    if payload.allocations:
        # Explicit allocations requested
        total_requested = sum(a.allocated_amount_minor for a in payload.allocations)
        if total_requested > payload.amount_minor:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Total allocation ({total_requested}) cannot exceed payment amount ({payload.amount_minor})",
            )

        for item in payload.allocations:
            charge = db.scalars(
                select(SupplierLedgerEntry)
                .where(
                    SupplierLedgerEntry.id == item.charge_entry_id,
                    SupplierLedgerEntry.supplier_id == supplier_id,
                )
                .with_for_update()
            ).first()

            if not charge or charge.status != "posted" or charge.direction != LedgerDirection.CREDIT.value:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"Charge {item.charge_entry_id} is invalid or does not belong to supplier {supplier_id}",
                )

            # Sum existing allocations on this charge
            already_alloc = db.scalar(
                select(func.coalesce(func.sum(SupplierPaymentAllocation.allocated_amount_minor), 0)).where(
                    SupplierPaymentAllocation.charge_entry_id == charge.id
                )
            ) or 0

            unpaid = charge.amount_minor - already_alloc
            if item.allocated_amount_minor > unpaid:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"Allocated amount {item.allocated_amount_minor} exceeds unpaid balance {unpaid} for charge {charge.reference}",
                )

            alloc = SupplierPaymentAllocation(
                payment_entry_id=payment_entry.id,
                charge_entry_id=charge.id,
                allocated_amount_minor=item.allocated_amount_minor,
            )
            db.add(alloc)
            created_allocations.append(alloc)
            db.flush()
            remaining_payment_minor -= item.allocated_amount_minor

    elif payload.auto_allocate_fifo:
        # Auto-allocate against oldest unpaid charges FIFO
        candidate_charges = db.scalars(
            select(SupplierLedgerEntry)
            .where(
                SupplierLedgerEntry.supplier_id == supplier_id,
                SupplierLedgerEntry.status == "posted",
                SupplierLedgerEntry.direction == LedgerDirection.CREDIT.value,
                SupplierLedgerEntry.entry_type.in_(["charge", "opening_balance"]),
            )
            .order_by(SupplierLedgerEntry.effective_date.asc(), SupplierLedgerEntry.recorded_at.asc())
            .with_for_update()
        ).all()

        for charge in candidate_charges:
            if remaining_payment_minor <= 0:
                break

            already_alloc = db.scalar(
                select(func.coalesce(func.sum(SupplierPaymentAllocation.allocated_amount_minor), 0)).where(
                    SupplierPaymentAllocation.charge_entry_id == charge.id
                )
            ) or 0

            unpaid = charge.amount_minor - already_alloc
            if unpaid <= 0:
                continue

            to_allocate = min(remaining_payment_minor, unpaid)
            alloc = SupplierPaymentAllocation(
                payment_entry_id=payment_entry.id,
                charge_entry_id=charge.id,
                allocated_amount_minor=to_allocate,
            )
            db.add(alloc)
            created_allocations.append(alloc)
            db.flush()
            remaining_payment_minor -= to_allocate

    db.flush()
    db.commit()
    db.refresh(payment_entry)
    for a in created_allocations:
        db.refresh(a)

    return payment_entry, created_allocations


def post_supplier_advance(
    db: Session,
    supplier_id: uuid.UUID,
    payload: SupplierAdvanceRequest,
    actor_id: uuid.UUID | None = None,
) -> SupplierLedgerEntry:
    """Disburse an unallocated advance payment to a supplier."""
    supplier = db.scalar(select(Supplier).where(Supplier.id == supplier_id).with_for_update())
    if not supplier:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Supplier {supplier_id} not found")

    source_key = (
        f"advance:{supplier_id}:{payload.idempotency_key}"
        if payload.idempotency_key
        else None
    )
    if source_key:
        existing = db.scalar(
            select(SupplierLedgerEntry).where(
                SupplierLedgerEntry.source_event_key == source_key
            )
        )
        if existing:
            return existing

    advance_entry = SupplierLedgerEntry(
        supplier_id=supplier_id,
        entry_type=LedgerEntryType.ADVANCE.value,
        amount_minor=payload.amount_minor,
        direction=LedgerDirection.DEBIT.value,
        source_event_key=source_key,
        reference=payload.reference,
        effective_date=payload.effective_date,
        status="posted",
        notes=f"Advance via {payload.payment_method}. {payload.notes or ''}".strip(),
        recorded_by_user_id=actor_id,
        recorded_at=_utcnow(),
    )
    db.add(advance_entry)
    db.flush()
    db.commit()
    db.refresh(advance_entry)
    return advance_entry


def allocate_payment_advance(
    db: Session,
    supplier_id: uuid.UUID,
    payment_entry_id: uuid.UUID,
    payload: AllocatePaymentRequest,
) -> SupplierPaymentAllocation:
    """Allocate unallocated funds from an existing payment or advance to a charge."""
    # Lock payment
    payment = db.scalars(
        select(SupplierLedgerEntry)
        .where(
            SupplierLedgerEntry.id == payment_entry_id,
            SupplierLedgerEntry.supplier_id == supplier_id,
        )
        .with_for_update()
    ).first()
    if not payment or payment.status != "posted" or payment.entry_type not in ("payment", "advance"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payment entry not found or invalid")

    # Lock charge
    charge = db.scalars(
        select(SupplierLedgerEntry)
        .where(
            SupplierLedgerEntry.id == payload.charge_entry_id,
            SupplierLedgerEntry.supplier_id == supplier_id,
        )
        .with_for_update()
    ).first()
    if not charge or charge.status != "posted" or charge.entry_type not in ("charge", "opening_balance"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Charge entry not found or invalid")

    # Check payment available
    payment_alloc = db.scalar(
        select(func.coalesce(func.sum(SupplierPaymentAllocation.allocated_amount_minor), 0)).where(
            SupplierPaymentAllocation.payment_entry_id == payment.id
        )
    ) or 0
    payment_available = payment.amount_minor - payment_alloc
    if payload.amount_minor > payment_available:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Allocated amount {payload.amount_minor} exceeds available payment balance {payment_available}",
        )

    # Check charge unpaid
    charge_alloc = db.scalar(
        select(func.coalesce(func.sum(SupplierPaymentAllocation.allocated_amount_minor), 0)).where(
            SupplierPaymentAllocation.charge_entry_id == charge.id
        )
    ) or 0
    charge_unpaid = charge.amount_minor - charge_alloc
    if payload.amount_minor > charge_unpaid:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Allocated amount {payload.amount_minor} exceeds unpaid charge balance {charge_unpaid}",
        )

    alloc = SupplierPaymentAllocation(
        payment_entry_id=payment.id,
        charge_entry_id=charge.id,
        allocated_amount_minor=payload.amount_minor,
    )
    db.add(alloc)
    db.flush()
    db.commit()
    db.refresh(alloc)
    return alloc


def post_supplier_refund(
    db: Session,
    supplier_id: uuid.UUID,
    payload: SupplierRefundRequest,
    actor_id: uuid.UUID | None = None,
) -> SupplierLedgerEntry:
    """Record a cash refund received FROM the vendor back to AlphaZee."""
    supplier = db.scalar(select(Supplier).where(Supplier.id == supplier_id).with_for_update())
    if not supplier:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Supplier {supplier_id} not found")

    source_key = (
        f"refund:{supplier_id}:{payload.idempotency_key}"
        if payload.idempotency_key
        else None
    )
    if source_key:
        existing = db.scalar(
            select(SupplierLedgerEntry).where(
                SupplierLedgerEntry.source_event_key == source_key
            )
        )
        if existing:
            return existing

    refund_entry = SupplierLedgerEntry(
        supplier_id=supplier_id,
        entry_type=LedgerEntryType.REFUND_RECEIVED.value,
        amount_minor=payload.amount_minor,
        direction=LedgerDirection.CREDIT.value,
        source_event_key=source_key,
        reference=payload.reference,
        effective_date=payload.effective_date,
        status="posted",
        notes=f"Supplier refund received via {payload.refund_method}. {payload.notes or ''}".strip(),
        recorded_by_user_id=actor_id,
        recorded_at=_utcnow(),
    )
    db.add(refund_entry)
    db.flush()
    db.commit()
    db.refresh(refund_entry)
    return refund_entry


def get_unpaid_charges_and_advances(
    db: Session,
    supplier_id: uuid.UUID,
) -> dict:
    """Return lists of unpaid charges and unallocated payments/advances for this supplier."""
    supplier = db.scalar(select(Supplier).where(Supplier.id == supplier_id).with_for_update())
    if not supplier:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Supplier {supplier_id} not found")

    charges = db.scalars(
        select(SupplierLedgerEntry)
        .where(
            SupplierLedgerEntry.supplier_id == supplier_id,
            SupplierLedgerEntry.status == "posted",
            SupplierLedgerEntry.direction == LedgerDirection.CREDIT.value,
            SupplierLedgerEntry.entry_type.in_(["charge", "opening_balance"]),
        )
        .order_by(SupplierLedgerEntry.effective_date.asc(), SupplierLedgerEntry.recorded_at.asc())
    ).all()

    payments = db.scalars(
        select(SupplierLedgerEntry)
        .where(
            SupplierLedgerEntry.supplier_id == supplier_id,
            SupplierLedgerEntry.status == "posted",
            SupplierLedgerEntry.direction == LedgerDirection.DEBIT.value,
            SupplierLedgerEntry.entry_type.in_(["payment", "advance"]),
        )
        .order_by(SupplierLedgerEntry.effective_date.asc(), SupplierLedgerEntry.recorded_at.asc())
    ).all()

    all_entry_ids = [c.id for c in charges] + [p.id for p in payments]
    charge_alloc_map: dict[uuid.UUID, int] = {}
    payment_alloc_map: dict[uuid.UUID, int] = {}

    if all_entry_ids:
        allocs = db.execute(
            select(
                SupplierPaymentAllocation.payment_entry_id,
                SupplierPaymentAllocation.charge_entry_id,
                SupplierPaymentAllocation.allocated_amount_minor,
            ).where(
                or_(
                    SupplierPaymentAllocation.payment_entry_id.in_(all_entry_ids),
                    SupplierPaymentAllocation.charge_entry_id.in_(all_entry_ids),
                )
            )
        ).all()

        for p_id, c_id, amt in allocs:
            charge_alloc_map[c_id] = charge_alloc_map.get(c_id, 0) + amt
            payment_alloc_map[p_id] = payment_alloc_map.get(p_id, 0) + amt

    unpaid_charges = []
    for c in charges:
        alloc_amt = charge_alloc_map.get(c.id, 0)
        unpaid = max(0, c.amount_minor - alloc_amt)
        if unpaid > 0:
            unpaid_charges.append({
                "id": c.id,
                "reference": c.reference,
                "effective_date": c.effective_date,
                "amount_minor": c.amount_minor,
                "allocated_amount_minor": alloc_amt,
                "unpaid_amount_minor": unpaid,
            })

    unallocated_payments = []
    for p in payments:
        alloc_amt = payment_alloc_map.get(p.id, 0)
        unallocated = max(0, p.amount_minor - alloc_amt)
        if unallocated > 0:
            unallocated_payments.append({
                "id": p.id,
                "reference": p.reference,
                "effective_date": p.effective_date,
                "amount_minor": p.amount_minor,
                "allocated_amount_minor": alloc_amt,
                "unallocated_amount_minor": unallocated,
            })

    return {
        "unpaid_charges": unpaid_charges,
        "unallocated_payments": unallocated_payments,
    }


def get_supplier_statement(
    db: Session,
    supplier_id: uuid.UUID,
    start_date: date,
    end_date: date,
) -> dict:
    """
    Generate period statement with exact opening, movement, and closing balances.
    Formula: Opening Balance + Period Movement == Closing Balance.
    """
    supplier = db.scalar(select(Supplier).where(Supplier.id == supplier_id).with_for_update())
    if not supplier:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Supplier {supplier_id} not found")

    # 1. Opening balance as-of start_date:
    # All posted entries before start_date (Credits increase liability, Debits decrease liability)
    prior_credits = db.scalar(
        select(func.coalesce(func.sum(SupplierLedgerEntry.amount_minor), 0)).where(
            SupplierLedgerEntry.supplier_id == supplier_id,
            SupplierLedgerEntry.direction == LedgerDirection.CREDIT.value,
            SupplierLedgerEntry.effective_date < start_date,
        )
    ) or 0

    prior_debits = db.scalar(
        select(func.coalesce(func.sum(SupplierLedgerEntry.amount_minor), 0)).where(
            SupplierLedgerEntry.supplier_id == supplier_id,
            SupplierLedgerEntry.direction == LedgerDirection.DEBIT.value,
            SupplierLedgerEntry.effective_date < start_date,
        )
    ) or 0

    opening_payable = prior_credits - prior_debits

    # 2. Entries within period [start_date, end_date]
    period_entries = db.scalars(
        select(SupplierLedgerEntry)
        .where(
            SupplierLedgerEntry.supplier_id == supplier_id,
            SupplierLedgerEntry.effective_date >= start_date,
            SupplierLedgerEntry.effective_date <= end_date,
        )
        .order_by(
            SupplierLedgerEntry.effective_date.asc(),
            SupplierLedgerEntry.recorded_at.asc(),
        )
    ).all()

    # 3. Categorized movements and running balance
    charges_in_period = 0
    credits_in_period = 0
    payments_in_period = 0
    refunds_in_period = 0

    running_payable = opening_payable
    statement_entries = []

    for entry in period_entries:
        if entry.direction == LedgerDirection.CREDIT.value:
            running_payable += entry.amount_minor
            if entry.entry_type == "refund_received":
                refunds_in_period += entry.amount_minor
            else:
                charges_in_period += entry.amount_minor
        else:  # DEBIT
            running_payable -= entry.amount_minor
            if entry.entry_type in ("payment", "advance"):
                payments_in_period += entry.amount_minor
            else:
                credits_in_period += entry.amount_minor

        statement_entries.append({
            "id": entry.id,
            "effective_date": entry.effective_date,
            "entry_type": entry.entry_type,
            "direction": entry.direction,
            "reference": entry.reference,
            "amount_minor": entry.amount_minor,
            "running_payable_minor": running_payable,
            "notes": entry.notes,
            "status": entry.status,
        })

    net_movement = (charges_in_period + refunds_in_period) - (credits_in_period + payments_in_period)
    closing_payable = opening_payable + net_movement

    summary = get_supplier_ledger_summary(db, supplier_id)

    return {
        "supplier_id": supplier_id,
        "supplier_name": supplier.name,
        "start_date": start_date,
        "end_date": end_date,
        "opening_payable_minor": opening_payable,
        "charges_in_period_minor": charges_in_period,
        "credits_in_period_minor": credits_in_period,
        "payments_in_period_minor": payments_in_period,
        "refunds_in_period_minor": refunds_in_period,
        "net_movement_minor": net_movement,
        "closing_payable_minor": closing_payable,
        "unallocated_advances_minor": summary["unallocated_advances_minor"],
        "entries": statement_entries,
    }

