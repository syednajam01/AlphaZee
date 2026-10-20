"""Quantity-level acquisition snapshots. All writes share the inventory balance lock."""
from sqlalchemy import select, func
from app.models.owned_stock import OwnedStockLot, OwnedStockAllocation
from app.models.inventory import StockReservation, InventoryBalance, SupplierVariant
from app.models.orders import OrderLine
from app.models.supplier_finance import SupplierAgreement


def owned_physical(db, mapping_id):
    # Lot remainder excludes reservations; add back only units still physically held.
    remaining = db.scalar(select(func.coalesce(func.sum(OwnedStockLot.remaining_quantity), 0)).where(
        OwnedStockLot.supplier_variant_id == mapping_id)) or 0
    held = db.scalar(select(func.coalesce(func.sum(OwnedStockAllocation.quantity), 0))
        .join(StockReservation, StockReservation.id == OwnedStockAllocation.reservation_id).where(
            StockReservation.supplier_variant_id == mapping_id,
            StockReservation.stage.in_(['held', 'confirmed']))) or 0
    return int(remaining + held)


def allocate_acquisition(db, reservation):
    line = db.get(OrderLine, reservation.order_line_id)
    if line is None:
        return  # Retain orphan/legacy operational holds without inventing a purchase.
    if line.acquisition_snapshot is not None:
        return
    mapping = db.get(SupplierVariant, reservation.supplier_variant_id)
    if mapping.supplier_cost_minor is None:
        raise ValueError('Set the acquisition cost before reserving stock.')
    agreement = db.scalar(select(SupplierAgreement).where(
        SupplierAgreement.supplier_id == mapping.supplier_id,
        SupplierAgreement.is_active.is_(True)).order_by(SupplierAgreement.created_at.desc()))
    lots = db.scalars(select(OwnedStockLot).where(
        OwnedStockLot.supplier_variant_id == mapping.id, OwnedStockLot.remaining_quantity > 0)
        .order_by(OwnedStockLot.created_at, OwnedStockLot.id).with_for_update()).all()
    remaining = reservation.quantity
    segments = []
    for lot in lots:
        take = min(remaining, lot.remaining_quantity)
        if not take:
            break
        lot.remaining_quantity -= take
        db.add(OwnedStockAllocation(reservation_id=reservation.id, lot_id=lot.id, quantity=take))
        segments.append({'quantity': take, 'unit_cost_minor': lot.unit_cost_minor, 'owned': True})
        remaining -= take
    internal = mapping.supplier.supplier_type == 'alphazee_internal'
    if remaining:
        segments.append({'quantity': remaining, 'unit_cost_minor': mapping.supplier_cost_minor, 'owned': internal})
    line.ownership_source = 'alphazee_owned' if all(s['owned'] for s in segments) else 'vendor_consignment'
    line.acquisition_cost_minor = sum(s['quantity'] * s['unit_cost_minor'] for s in segments)
    line.acquisition_snapshot = {
        'supplier_id': str(mapping.supplier_id), 'supplier_name': mapping.supplier.name, 'supplier_variant_id': str(mapping.id),
        'agreement_id': str(agreement.id) if agreement else None,
        'payable_trigger': agreement.payable_trigger if agreement else 'manual',
        'payment_terms_days': agreement.payment_terms_days if agreement else 0,
        'vendor_quantity': 0 if internal else remaining, 'segments': segments,
    }
    # The total is authoritative for mixed historical costs; never round a unit average.
    if len({s['unit_cost_minor'] for s in segments}) == 1:
        line.unit_cost_minor = segments[0]['unit_cost_minor']
    db.flush()


def release_owned_allocation(db, reservation):
    for allocation in db.scalars(select(OwnedStockAllocation).where(
            OwnedStockAllocation.reservation_id == reservation.id)):
        lot = db.scalar(select(OwnedStockLot).where(OwnedStockLot.id == allocation.lot_id).with_for_update())
        lot.remaining_quantity += allocation.quantity
        db.delete(allocation)


def cost_segments(line):
    return (line.acquisition_snapshot or {}).get('segments') or [
        {'quantity': line.quantity, 'unit_cost_minor': line.unit_cost_minor or 0, 'owned': line.ownership_source == 'alphazee_owned'}]


def returned_cost(line, quantity, offset=0):
    """Stable FIFO disposition of units, preserving exact integer acquisition costs."""
    total = 0
    for segment in cost_segments(line):
        skip = min(offset, segment['quantity'])
        offset -= skip
        take = min(quantity, segment['quantity'] - skip)
        total += take * segment['unit_cost_minor']
        quantity -= take
    return total


def restock_owned(db, mapping_id, line, quantity, source_ref, offset=0):
    """Called only after the physical return adjustment, in its transaction."""
    for index, segment in enumerate(cost_segments(line)):
        skip = min(offset, segment['quantity'])
        offset -= skip
        take = min(quantity, segment['quantity'] - skip)
        if take:
            db.add(OwnedStockLot(supplier_variant_id=mapping_id,
                source_ref=f'{source_ref}:{index}', remaining_quantity=take,
                unit_cost_minor=segment['unit_cost_minor']))
        quantity -= take
    db.flush()
