"""Public eligibility exposes no supplier information; owner holds are explicit."""
from sqlalchemy import func, select
from app.models.catalog import AvailabilityStatus, Variant
from app.models.inventory import InventoryBalance, StockReservation, SupplierVariant
from app.models.orders import Order, OrderLine
from app.models.suppliers import Supplier
from app.queries.stock_rules import holding_predicate


def public_availability(db, variants):
    ids = [v.id for v in variants]
    if not ids: return {}
    held = select(StockReservation.supplier_variant_id.label('sv_id'), func.sum(StockReservation.quantity).label('quantity')).where(holding_predicate()).group_by(StockReservation.supplier_variant_id).subquery()
    eligible = set(db.scalars(select(SupplierVariant.variant_id)
        .join(Supplier, Supplier.id == SupplierVariant.supplier_id)
        .join(InventoryBalance, InventoryBalance.supplier_variant_id == SupplierVariant.id)
        .outerjoin(held, held.c.sv_id == SupplierVariant.id).where(
            SupplierVariant.variant_id.in_(ids), SupplierVariant.active.is_(True), Supplier.status == 'active',
            SupplierVariant.supplier_cost_minor.is_not(None), SupplierVariant.supplier_cost_minor >= 0,
            InventoryBalance.on_hand > func.coalesce(held.c.quantity, 0))))
    return {v.id: ('available' if v.is_active and v.price_minor is not None and v.id in eligible else 'unavailable')
            if v.availability == AvailabilityStatus.AVAILABLE else v.availability.value for v in variants}


def hold_details(db, supplier_variant_id, page=1, page_size=20):
    if db.get(SupplierVariant, supplier_variant_id) is None: return None
    # Every stock writer takes this balance lock exclusively. A share lock keeps
    # the aggregate and paginated breakdown consistent throughout this response.
    balance = db.scalar(select(InventoryBalance).where(InventoryBalance.supplier_variant_id == supplier_variant_id)
                        .with_for_update(read=True).execution_options(populate_existing=True))
    predicate = [StockReservation.supplier_variant_id == supplier_variant_id, holding_predicate()]
    held, count = db.execute(select(func.coalesce(func.sum(StockReservation.quantity), 0), func.count()).where(*predicate)).one()
    rows = db.execute(select(StockReservation, Order.id, Order.order_number, Order.order_status)
        .outerjoin(OrderLine, OrderLine.id == StockReservation.order_line_id).outerjoin(Order, Order.id == OrderLine.order_id)
        .where(*predicate).order_by(StockReservation.created_at, StockReservation.id).offset((page-1)*page_size).limit(page_size)).all()
    physical = balance.on_hand if balance else 0
    return {'supplier_variant_id': supplier_variant_id, 'physical_on_hand': physical, 'held_reservations': held,
            'available_to_sell': max(0, physical-held), 'version': balance.version if balance else None,
            'total': count, 'page': page, 'page_size': page_size,
            'holds': [{'reservation_id': r.id, 'order_line_id': r.order_line_id, 'quantity': r.quantity,
                       'stage': r.stage, 'legacy_stock_hold': r.legacy_stock_hold, 'created_at': r.created_at,
                       'order_id': order_id, 'order_number': number, 'order_status': state,
                       'order_link': f'/admin/orders?order_id={order_id}' if order_id else None}
                      for r, order_id, number, state in rows]}


def variant_stock(db, identifier):
    variant = db.get(Variant, identifier)
    if variant is None: return None
    mappings = list(db.scalars(select(SupplierVariant).where(SupplierVariant.variant_id == identifier).order_by(SupplierVariant.id)))
    details = [{ 'supplier_id': link.supplier_id, 'supplier_name': link.supplier.name,
                 'supplier_status': link.supplier.status, 'supplier_cost_minor': link.supplier_cost_minor,
                 'active': link.active, **hold_details(db, link.id)} for link in mappings]
    sv = next((link for link in mappings if link.active), None)
    result = {'variant_id': identifier, 'owner_availability': variant.availability.value,
              'public_availability': public_availability(db, [variant])[identifier], 'mapping': None,
              'historical_mappings': [item for item in details if not item['active']]}
    reasons = []
    if not variant.is_active: reasons.append('Activate the variant')
    if variant.price_minor is None: reasons.append('Set a retail price')
    if variant.availability != AvailabilityStatus.AVAILABLE: reasons.append('Set owner availability to Available')
    if not sv: reasons.append('Choose an active supplier and wholesale cost')
    else:
        result['mapping'] = next(item for item in details if item['active'])
        if sv.supplier.status != 'active': reasons.append('Choose an active supplier')
        if sv.supplier_cost_minor is None: reasons.append('Set a wholesale cost')
        if result['mapping']['available_to_sell'] <= 0: reasons.append('Receive stock or review current holds')
    product = variant.product
    if product.status != 'published' or not product.collection or not product.collection.is_active:
        reasons.append('Publish in an active collection before selling')
    result['readiness_reasons'] = reasons
    return result
