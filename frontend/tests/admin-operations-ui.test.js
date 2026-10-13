import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createMockElement } from './helpers/dom.js';
import { createAdminConsoleModal } from '../src/components/AdminConsole.js';

const tick = () => new Promise(resolve => setTimeout(resolve, 20));

test('owner dispatch, delivery, stock adjustment and supplier mapping submit once and reload', async () => {
  const doc = createMockElement('document');
  doc.body = createMockElement('body');
  doc.createElement = createMockElement;
  doc.activeElement = doc.body;
  globalThis.document = doc;
  globalThis.window = { localStorage: { removeItem() {} }, sessionStorage: { removeItem() {} } };
  globalThis.confirm = () => true;
  const calls = [];
  const order = {
    id: 'order-1', order_number: 'AZ-TEST-1', customer_name: 'Sample Customer',
    customer_phone: '03001112222', shipping_city: 'Lahore', total: { formatted: 'PKR 6,000' },
    payment_method: 'cod', payment_status: 'pending', order_status: 'confirmed',
    shipments: [], lines: [],
  };
  let stock = 10;
  let version = 1;
  let mapped = false;
  globalThis.fetch = async (url, options = {}) => {
    const path = String(url);
    const body = options.body ? JSON.parse(options.body) : null;
    calls.push({ path, body });
    let data = {};
    if (path.endsWith('/auth/session')) data = { username: 'sample_owner', csrf_token: 'csrf-test' };
    else if (path.endsWith('/admin/overview')) data = { formatted_gross_revenue: 'PKR 0', total_orders: 1, pending_orders: 0, total_skus: 1, low_stock_skus: 0 };
    else if (path.includes('/admin/orders?')) data = { orders: [order], total: 1, page: 1, page_size: 20 };
    else if (path.endsWith('/admin/orders/order-1/dispatch')) {
      order.order_status = 'dispatched';
      order.shipments = [{ id: 'shipment-1', status: 'dispatched', cod_amount_minor: 600000,
        settlement_outstanding_minor: 600000 }];
      data = order.shipments[0];
    } else if (path.endsWith('/admin/shipments/shipment-1/status')) {
      order.order_status = 'delivered';
      order.shipments[0].status = 'delivered';
      data = order.shipments[0];
    } else if (path.endsWith('/admin/inventory/summary')) data = { items: [{
      supplier_variant_id: 'supplier-variant-1', supplier_id: 'supplier-1', supplier_name: 'Sample Supplier',
      variant_id: 7, product_title: 'Sample Tee', sku: 'SAMPLE-TEE', physical_on_hand: stock,
      held_reservations: 0, available_to_sell: stock, version,
    }], total_variants: 1 };
    else if (path.endsWith('/admin/inventory/adjust')) {
      stock += body.quantity_delta;
      version++;
      data = { physical_on_hand: stock, version };
    } else if (path.endsWith('/admin/suppliers')) data = { suppliers: [{ id: 'supplier-1', name: 'Sample Supplier', slug: 'sample-supplier', status: 'active' }] };
    else if (path.endsWith('/admin/catalog/variants')) data = [{ id: 7, product_title: 'Sample Tee', sku: 'SAMPLE-TEE', is_active: true, active_supplier_id: mapped ? 'supplier-1' : null }];
    else if (path.endsWith('/admin/suppliers/supplier-1/variants')) { mapped = true; data = { id: 'supplier-variant-1', ...body }; }
    return { ok: true, status: 200, json: async () => data };
  };
  const admin = createAdminConsoleModal();
  doc.body.appendChild(admin.element);
  await admin.open();
  const switchTab = async name => {
    admin.element.querySelectorAll('.admin-tab-btn').find(b => b.dataset.tab === name).click();
    await tick();
  };
  await switchTab('orders');
  assert.ok(admin.element.querySelector('.btn-dispatch-order'));
  admin.element.querySelector('#admin-dispatch-form').reset = () => {};
  const opener = admin.element.querySelector('.btn-dispatch-order');
  opener.click();
  doc.dispatchEvent({ type: 'keydown', key: 'Escape', preventDefault() {} });
  assert.equal(admin.element.querySelector('#admin-dispatch-modal').style.display, 'none');
  assert.equal(doc.activeElement, opener);
  opener.click();
  const dispatchForm = admin.element.querySelector('#admin-dispatch-form');
  dispatchForm.querySelector('#dispatch-courier-code').value = 'trax';
  dispatchForm.querySelector('#dispatch-tracking-number').value = 'TRX-TEST-01';
  dispatchForm.querySelector('#dispatch-shipping-cost').value = '250';
  dispatchForm.querySelector('#dispatch-tracking-url').value = '';
  dispatchForm.dispatchEvent({ type: 'submit', currentTarget: dispatchForm, preventDefault() {} });
  dispatchForm.dispatchEvent({ type: 'submit', currentTarget: dispatchForm, preventDefault() {} });
  await tick();
  const dispatches = calls.filter(call => call.path.endsWith('/admin/orders/order-1/dispatch'));
  assert.equal(dispatches.length, 1);
  assert.equal(dispatches[0].body.shipping_cost_minor, 25000);
  assert.ok(admin.element.querySelector('.btn-mark-delivered'));
  admin.element.querySelector('.btn-mark-delivered').click();
  await tick();
  assert.equal(order.order_status, 'delivered');

  await switchTab('inventory');
  const inventoryForm = admin.element.querySelector('#inventory-adjust-form');
  inventoryForm.querySelector('#inventory-target').value = 'supplier-variant-1';
  inventoryForm.querySelector('#inventory-delta').value = '3';
  inventoryForm.querySelector('#inventory-reason').value = 'supplier_receipt';
  inventoryForm.querySelector('#inventory-reference').value = 'PO-TEST-01';
  inventoryForm.dispatchEvent({ type: 'submit', currentTarget: inventoryForm, preventDefault() {} });
  await tick();
  assert.equal(stock, 13);
  assert.equal(calls.find(call => call.path.endsWith('/admin/inventory/adjust')).body.expected_version, 1);
  assert.match(admin.element.querySelector('#admin-session-message').textContent, /stock refreshed/);

  await switchTab('suppliers');
  const mappingForm = admin.element.querySelector('#supplier-variant-form');
  mappingForm.querySelector('#mapping-supplier').value = 'supplier-1';
  mappingForm.querySelector('#mapping-variant').value = '7';
  mappingForm.querySelector('#mapping-cost').value = '1800';
  mappingForm.dispatchEvent({ type: 'submit', currentTarget: mappingForm, preventDefault() {} });
  await tick();
  assert.equal(mapped, true);
  assert.equal(calls.find(call => call.path.endsWith('/admin/suppliers/supplier-1/variants')).body.supplier_cost_minor, 180000);
  admin.close();
});
