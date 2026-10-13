"""Append-only settlement and executed-refund accounting in PKR minor units."""
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.finance import CourierSettlementEntry, RefundExecution
from app.models.returns import OrderReturn
from app.models.shipments import Shipment


class FinanceError(ValueError):
    pass


def settlement_totals(shipment: Shipment) -> dict[str, int | str]:
    entries = shipment.settlement_entries
    receipts = sum(e.amount_minor for e in entries if e.entry_type == 'receipt')
    deductions = sum(e.amount_minor for e in entries if e.entry_type != 'receipt')
    outstanding = max(0, shipment.cod_amount_minor - receipts - deductions)
    if shipment.cod_amount_minor <= 0:
        state = 'not_applicable'
    elif outstanding == 0:
        state = 'remitted'
    elif any(e.final_statement for e in entries):
        state = 'disputed'
    elif receipts or deductions:
        state = 'partial'
    else:
        state = 'pending_remittance'
    return {'receipts_minor': receipts, 'deductions_minor': deductions,
            'outstanding_minor': outstanding, 'status': state}


def record_settlement(db: Session, *, shipment_id: uuid.UUID, amount_minor: int,
                      reference: str | None, deductions: list[tuple[str, int, str, str]],
                      final_statement: bool = False,
                      actor_user_id: uuid.UUID | None = None) -> Shipment:
    shipment = db.scalar(select(Shipment).where(Shipment.id == shipment_id).with_for_update()
                         .execution_options(populate_existing=True))
    if shipment is None:
        raise FinanceError('Shipment not found.')
    if shipment.cod_amount_minor <= 0 or (shipment.delivered_at is None and shipment.status != 'delivered'):
        raise FinanceError('Only delivered COD parcels can be settled.')
    if amount_minor < 0 or (amount_minor == 0 and not deductions):
        raise FinanceError('Record a positive receipt or a documented deduction.')
    refs = [reference] if amount_minor else []
    refs += [deduction[2] for deduction in deductions]
    clean_refs = [str(ref or '').strip().upper() for ref in refs]
    if any(len(ref) < 3 or len(ref) > 120 for ref in clean_refs) or len(set(clean_refs)) != len(clean_refs):
        raise FinanceError('Each receipt and deduction needs a distinct reference of 3–120 characters.')
    if db.scalar(select(CourierSettlementEntry.id).where(
            CourierSettlementEntry.reference.in_(clean_refs))) is not None:
        raise FinanceError('A settlement reference is already recorded.')
    totals = settlement_totals(shipment)
    existing_by_type = {kind: sum(e.amount_minor for e in shipment.settlement_entries
                                  if e.entry_type == kind) for kind in
                        ('outbound_shipping', 'rto_shipping', 'other_deduction')}
    deduction_total = 0
    new_entries = []
    for (kind, amount, ref, note), clean_ref in zip(deductions, clean_refs[1 if amount_minor else 0:]):
        if kind not in existing_by_type or amount <= 0 or not note or len(note.strip()) < 5:
            raise FinanceError('Deduction requires a supported type, positive amount, and evidence note.')
        existing_by_type[kind] += amount
        if kind == 'outbound_shipping' and existing_by_type[kind] > shipment.shipping_cost_minor:
            raise FinanceError('Outbound deduction exceeds recorded courier cost.')
        if kind == 'rto_shipping' and existing_by_type[kind] > shipment.rto_courier_cost_minor:
            raise FinanceError('RTO deduction exceeds recorded return cost.')
        deduction_total += amount
        new_entries.append(CourierSettlementEntry(shipment_id=shipment.id, entry_type=kind,
            amount_minor=amount, reference=clean_ref, note=note.strip(),
            recorded_by_user_id=actor_user_id))
    if final_statement and not amount_minor and new_entries:
        new_entries[-1].final_statement = True
    if int(totals['receipts_minor']) + int(totals['deductions_minor']) + amount_minor + deduction_total > shipment.cod_amount_minor:
        raise FinanceError('Receipts plus deductions exceed collected COD.')
    if amount_minor:
        receipt = CourierSettlementEntry(shipment_id=shipment.id, entry_type='receipt',
            amount_minor=amount_minor, reference=clean_refs[0], final_statement=final_statement,
            recorded_by_user_id=actor_user_id)
        new_entries.append(receipt)
    db.add_all(new_entries)
    db.flush()
    db.expire(shipment, ['settlement_entries'])
    summary = settlement_totals(shipment)
    shipment.cod_remitted_amount_minor = int(summary['receipts_minor'])
    shipment.cod_remittance_status = str(summary['status'])
    if amount_minor:
        shipment.cod_remittance_reference = clean_refs[0]
        shipment.cod_remitted_at = receipt.recorded_at
    db.flush()
    return shipment


def record_refund_execution(db: Session, *, return_id: uuid.UUID, amount_minor: int,
                            reference: str, channel: str, note: str | None = None,
                            actor_user_id: uuid.UUID | None = None) -> RefundExecution:
    ret = db.scalar(select(OrderReturn).where(OrderReturn.id == return_id).with_for_update()
                    .execution_options(populate_existing=True))
    if ret is None or ret.status != 'completed' or ret.return_type != 'refund_bank_transfer':
        raise FinanceError('Complete the bank refund return before recording payment.')
    if ret.order.payment_status not in ('verified', 'refunded'):
        raise FinanceError('The original customer payment is not verified.')
    clean_ref = reference.strip().upper()
    if amount_minor <= 0 or len(clean_ref) < 3 or len(clean_ref) > 120:
        raise FinanceError('A positive refund and unique payment reference are required.')
    if channel not in ('bank_transfer', 'cash', 'other'):
        raise FinanceError('Use a supported refund payment channel.')
    if db.scalar(select(RefundExecution.id).where(RefundExecution.reference == clean_ref)) is not None:
        raise FinanceError('Refund payment reference is already recorded.')
    paid = db.scalar(select(func.coalesce(func.sum(RefundExecution.amount_minor), 0)).where(
        RefundExecution.return_id == ret.id)) or 0
    if paid + amount_minor > ret.refund_amount_minor:
        raise FinanceError('Executed refunds exceed the approved refund amount.')
    execution = RefundExecution(return_id=ret.id, amount_minor=amount_minor,
        reference=clean_ref, channel=channel, note=note.strip() if note else None,
        recorded_by_user_id=actor_user_id)
    db.add(execution)
    db.flush()
    ret.refund_reference = clean_ref
    db.flush()
    return execution
