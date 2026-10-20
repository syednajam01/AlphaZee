"""Regression evidence through real commerce APIs, on the guarded disposable DB only."""
from datetime import date, datetime, timedelta, timezone
import uuid
import pytest
from sqlalchemy import select, func
from app.models.catalog import Collection, Product, Variant, AvailabilityStatus
from app.models.suppliers import Supplier
from app.models.inventory import SupplierVariant, InventoryBalance, StockReservation
from app.models.orders import Order, OrderLine
from app.models.shipments import Shipment
from app.models.owned_stock import OwnedStockLot
from app.models.supplier_finance import SupplierAgreement, SupplierLedgerEntry
from app.models.business_expenses import BusinessExpense
from app.services.financial_report import get_period_financial_report


@pytest.fixture
def admin_client(client, admin_headers):
    # CookieJar must merge owner, checkout and private-order cookies naturally.
    from http.cookies import SimpleCookie
    cookies = SimpleCookie(); cookies.load(admin_headers['Cookie'])
    for name, cookie in cookies.items():
        client.cookies.set(name, cookie.value)
    client.headers.update({k: v for k, v in admin_headers.items() if k != 'Cookie'})
    return client


@pytest.fixture
def catalog(db_session):
    db_session.autoflush = False  # Match production, including pending allocation visibility.
    token = uuid.uuid4().hex[:8]
    supplier = Supplier(name='SAMPLE Repair Vendor', slug=f'repair-{token}', status='active')
    collection = Collection(id=f'repair-{token}', slug=f'repair-{token}', name='SAMPLE Repairs', is_active=True)
    db_session.add_all([supplier, collection]); db_session.flush()
    product = Product(id=f'repair-{token}', slug=f'repair-{token}', title='SAMPLE Tee',
        collection_id=collection.id, status='published', is_active=True,
        stock_management_source='vendor_managed', vendor_id=supplier.id)
    db_session.add(product); db_session.flush()
    variant = Variant(product_id=product.id, sku=f'REPAIR-{token}', size='M', color='Black',
        price_minor=200000, is_active=True, availability=AvailabilityStatus.AVAILABLE)
    db_session.add(variant); db_session.flush()
    mapping = SupplierVariant(supplier_id=supplier.id, variant_id=variant.id, supplier_cost_minor=120000)
    db_session.add(mapping); db_session.flush()
    balance = InventoryBalance(supplier_variant_id=mapping.id, on_hand=10)
    agreement = SupplierAgreement(supplier_id=supplier.id, payable_trigger='dispatch',
        payment_terms_days=7, effective_from=datetime.now(timezone.utc), is_active=True)
    db_session.add_all([balance, agreement]); db_session.commit()
    return supplier, product, variant, mapping, balance, agreement


def post(client, url, payload=None, expected=200):
    response = client.post(url, json=payload)
    assert response.status_code == expected, response.text
    return response.json() if response.content else None


def buy(client, variant, quantity=1, **extra):
    client.get('/api/v1/orders/checkout-session')
    response = client.post('/api/v1/orders', headers={'Idempotency-Key': f'chk_{uuid.uuid4().hex}'}, json={
        'customer_name': 'SAMPLE Repairs Buyer', 'customer_phone': '03001234567',
        'shipping_address_line1': 'SAMPLE Street 123', 'shipping_city': 'Karachi',
        'shipping_province': 'Sindh', 'payment_method': 'cod',
        'items': [{'variant_id': variant.id, 'quantity': quantity}], **extra})
    assert response.status_code == 201, response.text
    return response.json()


def dispatch(client, order):
    post(client, f"/api/v1/admin/orders/{order['id']}/confirm-supplier", {})
    return post(client, f"/api/v1/admin/orders/{order['id']}/dispatch", {
        'courier_code': 'manual', 'tracking_number': f'REPAIR-{uuid.uuid4().hex[:8]}',
        'shipping_cost_minor': 20000}, 201)


def return_unit(client, order):
    ret = post(client, '/api/v1/returns/request', {'order_id': order['id'],
        'order_line_id': order['lines'][0]['id'], 'return_type': 'refund_bank_transfer',
        'reason': 'size_too_small', 'quantity': 1}, 201)
    for action, payload in [('approve', {}), ('receive', {'received_quantity': 1}),
            ('inspect', {'sellable_quantity': 1, 'damaged_quantity': 0}), ('complete', {})]:
        post(client, f"/api/v1/admin/returns/{ret['id']}/{action}", payload)
    return ret


def test_real_return_resale_mixed_cost_and_no_second_payable(admin_client, db_session, catalog):
    supplier, product, variant, mapping, balance, agreement = catalog
    first = buy(admin_client, variant)
    shipment = dispatch(admin_client, first)
    post(admin_client, f"/api/v1/admin/shipments/{shipment['id']}/status", {'status': 'delivered'})
    assert db_session.scalar(select(func.sum(SupplierLedgerEntry.amount_minor))) == 120000
    return_unit(admin_client, first)
    from app.services.financial_report import get_order_economics_list
    rows, _ = get_order_economics_list(db_session, order_id=str(first['id']))
    assert rows[0]['estimated_contribution_minor'] == -20000
    lot = db_session.scalar(select(OwnedStockLot))
    assert lot.remaining_quantity == 1 and lot.unit_cost_minor == 120000
    mapping.supplier_cost_minor = 130001
    db_session.commit()
    second = buy(admin_client, variant, 2)
    line = db_session.get(OrderLine, uuid.UUID(second['lines'][0]['id']))
    assert line.acquisition_cost_minor == 250001
    assert line.acquisition_snapshot['vendor_quantity'] == 1
    # Later terms affect future purchases, never this acquired transaction.
    agreement.payable_trigger = 'delivery'
    db_session.commit()
    shipment2 = dispatch(admin_client, second)
    assert db_session.scalar(select(func.sum(SupplierLedgerEntry.amount_minor))) == 250001
    post(admin_client, f"/api/v1/admin/shipments/{shipment2['id']}/status", {'status': 'delivered'})
    assert db_session.scalar(select(func.count(SupplierLedgerEntry.id))) == 2
    assert lot.remaining_quantity == 0


def test_pickup_is_a_real_idempotent_action(admin_client, db_session, catalog):
    agreement = catalog[-1]; agreement.payable_trigger = 'confirmed_pickup'; db_session.commit()
    order = buy(admin_client, catalog[2])
    post(admin_client, f"/api/v1/admin/orders/{order['id']}/confirm-supplier", {})
    for _ in range(2):
        post(admin_client, f"/api/v1/admin/orders/{order['id']}/confirm-pickup")
    assert db_session.scalar(select(func.count(SupplierLedgerEntry.id))) == 1
    assert db_session.get(Order, uuid.UUID(order['id'])).supplier_picked_up_at is not None


def test_shortage_blocks_checkout_and_requires_recount(admin_client, db_session, catalog):
    from app.services.vendor_portal import provision_vendor_user, update_vendor_counted_quantity, resolve_shortage
    from app.models.vendor_portal import VendorStockShortage
    from app.queries.catalog_stock import public_availability
    supplier, _, variant, mapping, balance, _ = catalog
    vendor = provision_vendor_user(db_session, supplier.id, 'sample_repair_vendor', 'SAMPLE-repair-password-2026')
    db_session.commit()
    first = buy(admin_client, variant)
    for _ in range(2):
        result = update_vendor_counted_quantity(db_session, supplier.id, vendor, variant.id, 0,
            balance.version, 'stock_correction')
        assert result['available_quantity'] == 0
    db_session.commit()
    assert db_session.scalar(select(func.count(VendorStockShortage.id))) == 1
    assert public_availability(db_session, [variant])[variant.id] == 'unavailable'
    shortage = db_session.scalar(select(VendorStockShortage))
    with pytest.raises(ValueError, match='fresh physical count'):
        resolve_shortage(db_session, shortage.id, vendor.user_id, 'resolved', 'checked')
    # Real checkout reaches the reservation gate and cannot oversell the old stored count.
    admin_client.get('/api/v1/orders/checkout-session')
    response = admin_client.post('/api/v1/orders', headers={'Idempotency-Key': f'chk_{uuid.uuid4().hex}'}, json={
        'customer_name': 'SAMPLE Blocked Buyer', 'customer_phone': '03001234567',
        'shipping_address_line1': 'SAMPLE Street 456', 'shipping_city': 'Karachi',
        'shipping_province': 'Sindh', 'payment_method': 'cod', 'items': [{'variant_id': variant.id, 'quantity': 1}]})
    assert response.status_code == 409
    assert db_session.scalar(select(func.count(StockReservation.id)).where(StockReservation.supplier_variant_id == mapping.id)) == 1


def test_shipping_authoritative_quote_snapshot_and_tamper(admin_client, db_session, catalog):
    settings = admin_client.get('/api/v1/admin/settings').json()
    response = admin_client.put('/api/v1/admin/settings', json={'shipping_rules_configured': True,
        'shipping_coverage_area': 'Karachi', 'standard_shipping_fee_minor': 25000,
        'free_shipping_threshold_minor': 400000, 'expected_version': settings['version']})
    assert response.status_code == 200, response.text
    quote = post(admin_client, '/api/v1/orders/quote', {'items': [{'variant_id': catalog[2].id, 'quantity': 1}],
        'shipping_city': 'Karachi', 'shipping_province': 'Sindh'})
    assert quote['total_minor'] == 225000
    order = buy(admin_client, catalog[2], expected_total_minor=225000)
    assert order['total']['minor'] == 225000
    stored = db_session.get(Order, uuid.UUID(order['id']))
    assert stored.shipping_rule_snapshot['fee_minor'] == 25000
    # A caller-supplied fee is rejected by the public input contract.
    post(admin_client, '/api/v1/orders/quote', {'items': [{'variant_id': catalog[2].id, 'quantity': 1}],
        'shipping_city': 'Lahore', 'shipping_province': 'Punjab'}, expected=400)


def test_period_dates_and_unrelated_freight_add(admin_client, db_session, catalog):
    order = buy(admin_client, catalog[2]); shipment = dispatch(admin_client, order)
    post(admin_client, f"/api/v1/admin/shipments/{shipment['id']}/status", {'status': 'delivered'})
    stored = db_session.get(Order, uuid.UUID(order['id']))
    stored.placed_at = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
    parcel = db_session.get(Shipment, uuid.UUID(shipment['id']))
    parcel.delivered_at = datetime(2026, 2, 1, 19, tzinfo=timezone.utc)  # Feb 2 midnight Karachi
    parcel.created_at = datetime(2026, 2, 1, 10, tzinfo=timezone.utc)
    db_session.add(BusinessExpense(category='outbound_delivery', amount_minor=10000,
        incurred_date=date(2026, 2, 1), payee='Independent delivery', payment_method='cash'))
    db_session.flush()
    feb1 = get_period_financial_report(db_session, date(2026,2,1), date(2026,2,1))
    feb2 = get_period_financial_report(db_session, date(2026,2,2), date(2026,2,2))
    assert feb1['revenue']['net_revenue_minor'] == 0
    assert feb2['revenue']['net_revenue_minor'] == 200000
    assert feb1['freight']['outbound_freight_minor'] == 30000


def test_rto_inspection_damage_and_owned_resale(admin_client, db_session, catalog):
    order = buy(admin_client, catalog[2], 2)
    shipment = dispatch(admin_client, order)
    url = f"/api/v1/admin/shipments/{shipment['id']}/status"
    post(admin_client, url, {'status': 'rto_initiated', 'rto_courier_cost_minor': 15000})
    line_id = order['lines'][0]['id']
    post(admin_client, url, {'status': 'rto_delivered', 'received_lines': [
        {'order_line_id': line_id, 'received_quantity': 2}]})
    inspection = {'lines': [{'order_line_id': line_id, 'sellable_quantity': 1, 'damaged_quantity': 1}],
                  'notes': 'SAMPLE one intact and one torn'}
    for _ in range(2):
        post(admin_client, f"/api/v1/admin/shipments/{shipment['id']}/inspect-rto", inspection)
    assert db_session.scalar(select(func.sum(OwnedStockLot.remaining_quantity))) == 1
    report = get_period_financial_report(db_session)
    assert report['revenue']['net_revenue_minor'] == 0
    assert report['cogs']['inventory_writeoffs_minor'] == 120000
    assert report['freight']['total_freight_minor'] == 35000
    from app.services.financial_report import get_order_economics_list
    rows, _ = get_order_economics_list(db_session, order_id=str(order['id']))
    assert rows[0]['estimated_contribution_minor'] == -155000
    owned_order = buy(admin_client, catalog[2])
    assert db_session.get(OrderLine, uuid.UUID(owned_order['lines'][0]['id'])).ownership_source == 'alphazee_owned'
    dispatch(admin_client, owned_order)
    assert db_session.scalar(select(func.sum(SupplierLedgerEntry.amount_minor))) == 240000


def test_owned_hold_cancellation_and_vendor_count_isolation(admin_client, db_session, catalog):
    from app.services.vendor_portal import provision_vendor_user, update_vendor_counted_quantity
    from app.services.stock_ownership import owned_physical
    supplier, _, variant, mapping, balance, _ = catalog
    first = buy(admin_client, variant)
    shipment = dispatch(admin_client, first)
    post(admin_client, f"/api/v1/admin/shipments/{shipment['id']}/status", {'status': 'delivered'})
    return_unit(admin_client, first)
    vendor = provision_vendor_user(db_session, supplier.id, 'sample_isolated_count', 'SAMPLE-count-password-2026')
    db_session.commit()
    held_order = buy(admin_client, variant)
    result = update_vendor_counted_quantity(db_session, supplier.id, vendor, variant.id, 2,
        balance.version, 'stock_correction')
    assert result['allocated_on_hand'] == 2 and result['held_quantity'] == 0
    assert balance.on_hand == 3 and owned_physical(db_session, mapping.id) == 1
    post(admin_client, f"/api/v1/admin/orders/{held_order['id']}/cancel", {})
    assert db_session.scalar(select(func.sum(OwnedStockLot.remaining_quantity))) == 1


def test_legacy_ownership_review_and_no_inferred_historical_debt(admin_client, db_session, catalog):
    _, product, variant, mapping, balance, _ = catalog
    balance.ownership_review_required = True; db_session.commit()
    result = post(admin_client, f'/api/v1/admin/inventory/{mapping.id}/ownership-review', {
        'expected_version': balance.version, 'owned_lots': [{'quantity': 2, 'unit_cost_minor': 111111}],
        'note': 'SAMPLE matched two old returned garments against purchase records'})
    assert result['reviewed'] is True
    order = buy(admin_client, variant, 3)
    line = db_session.get(OrderLine, uuid.UUID(order['lines'][0]['id']))
    assert line.acquisition_snapshot['vendor_quantity'] == 1
    assert line.acquisition_cost_minor == 342222
    assert db_session.scalar(select(func.count(SupplierLedgerEntry.id))) == 0


def test_ledger_reversal_preserves_exact_signed_balance_and_history(db_session, catalog):
    from app.services.supplier_finance import post_manual_charge, reverse_ledger_entry, get_supplier_ledger_summary, get_supplier_statement
    from app.schemas.supplier_finance import ManualChargeRequest
    supplier = catalog[0]
    entry = post_manual_charge(db_session, supplier.id, ManualChargeRequest(
        amount_minor=50000, reference='SAMPLE wrong entry', effective_date=date(2026,1,1)))
    reverse_ledger_entry(db_session, entry.id, 'SAMPLE wrong vendor')
    summary = get_supplier_ledger_summary(db_session, supplier.id)
    assert summary['total_charges_minor'] == 0 and summary['outstanding_payable_minor'] == 0
    statement = get_supplier_statement(db_session, supplier.id, date(2025,1,1), date(2027,1,1))
    assert statement['closing_payable_minor'] == 0


def test_new_vendor_replacement_is_charged_once(admin_client, db_session, catalog):
    supplier, product, original, _, _, _ = catalog
    replacement = Variant(product_id=product.id, sku=f'REPLACE-{uuid.uuid4().hex[:8]}', size='L', color='Black',
        price_minor=200000, is_active=True, availability=AvailabilityStatus.AVAILABLE)
    db_session.add(replacement); db_session.flush()
    mapping = SupplierVariant(supplier_id=supplier.id, variant_id=replacement.id, supplier_cost_minor=90000)
    db_session.add(mapping); db_session.flush()
    db_session.add(InventoryBalance(supplier_variant_id=mapping.id, on_hand=3)); db_session.commit()
    order = buy(admin_client, original)
    shipment = dispatch(admin_client, order)
    post(admin_client, f"/api/v1/admin/shipments/{shipment['id']}/status", {'status': 'delivered'})
    ret = post(admin_client, '/api/v1/returns/request', {'order_id': order['id'],
        'order_line_id': order['lines'][0]['id'], 'return_type': 'size_exchange',
        'exchange_variant_id': replacement.id, 'reason': 'size_too_small', 'quantity': 1}, 201)
    for action, payload in [('approve', {}), ('receive', {'received_quantity': 1}),
            ('inspect', {'sellable_quantity': 1, 'damaged_quantity': 0})]:
        post(admin_client, f"/api/v1/admin/returns/{ret['id']}/{action}", payload)
    post(admin_client, f"/api/v1/admin/returns/{ret['id']}/dispatch-replacement", {
        'courier_code': 'manual', 'tracking_number': 'SAMPLE-REPLACEMENT', 'shipping_cost_minor': 0})
    amounts = sorted(db_session.scalars(select(SupplierLedgerEntry.amount_minor).where(
        SupplierLedgerEntry.order_id == uuid.UUID(order['id']), SupplierLedgerEntry.entry_type == 'charge')))
    assert amounts == [90000, 120000]


def test_return_reversal_uses_its_own_period(admin_client, db_session, catalog):
    order = buy(admin_client, catalog[2]); shipment = dispatch(admin_client, order)
    post(admin_client, f"/api/v1/admin/shipments/{shipment['id']}/status", {'status': 'delivered'})
    ret = return_unit(admin_client, order)
    from app.models.returns import OrderReturn
    parcel = db_session.get(Shipment, uuid.UUID(shipment['id']))
    parcel.delivered_at = datetime(2026,1,15,12,tzinfo=timezone.utc)
    returned = db_session.get(OrderReturn, uuid.UUID(ret['id']))
    returned.inspected_at = datetime(2026,2,15,12,tzinfo=timezone.utc)
    db_session.flush()
    report = get_period_financial_report(db_session, date(2026,2,1), date(2026,2,28))
    assert report['revenue']['gross_sales_minor'] == 0
    assert report['revenue']['sales_reversals_minor'] == 200000
    assert report['cogs']['cogs_reversals_minor'] == 120000


def test_cash_reversals_use_original_payment_kind(db_session, catalog):
    from app.services.supplier_finance import post_supplier_payment, post_supplier_refund, reverse_ledger_entry
    from app.schemas.supplier_finance import SupplierPaymentRequest, SupplierRefundRequest
    baseline = get_period_financial_report(db_session)['cash_reconciliation']
    payment, _ = post_supplier_payment(db_session, catalog[0].id, SupplierPaymentRequest(
        amount_minor=50000, reference='SAMPLE wrong payment', effective_date=date.today(),
        auto_allocate_fifo=False))
    reverse_ledger_entry(db_session, payment.id, 'SAMPLE correction')
    refund = post_supplier_refund(db_session, catalog[0].id, SupplierRefundRequest(
        amount_minor=20000, reference='SAMPLE wrong refund', effective_date=date.today()))
    reverse_ledger_entry(db_session, refund.id, 'SAMPLE correction')
    result = get_period_financial_report(db_session)['cash_reconciliation']
    assert result['supplier_payments_paid_minor'] == baseline['supplier_payments_paid_minor']
    assert result['total_cash_inflow_minor'] == baseline['total_cash_inflow_minor']
    assert result['net_cash_movement_minor'] == baseline['net_cash_movement_minor']
