import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createMockElement } from './helpers/dom.js';
import { mountVariantStock } from '../src/components/admin/VariantStock.js';
import { mountStockHolds } from '../src/components/admin/StockHolds.js';

const flush = () => new Promise(resolve => setTimeout(resolve, 35));
const state = { public_availability: 'available', readiness_reasons: [], historical_mappings: [], mapping: {
  supplier_id: 'sample-supplier', supplier_name: 'SAMPLE vendor', supplier_variant_id: 'sample-link',
  supplier_cost_minor: 1234, version: 0, physical_on_hand: 10, held_reservations: 0, available_to_sell: 10,
  page: 1, page_size: 20, total: 0, holds: [],
} };
function install() {
  globalThis.document = { createElement: createMockElement };
  globalThis.window = { confirm: () => true };
  return createMockElement('div');
}
const response = (data, status=200) => ({ ok: status < 400, status, json: async () => data });

test('variant stock uses exact wholesale paisas and versioned adjustments, retains other drafts and failed input', async () => {
  const host = install(), calls = [], dirty = [];
  let fail = false;
  globalThis.fetch = async (url, options={}) => {
    calls.push({ url, body: options.body ? JSON.parse(options.body) : null });
    if (url.endsWith('/stock')) return response(state);
    if (url.endsWith('/adjust') && fail) return response({ detail: 'conflict' }, 409);
    return response({});
  };
  const controller = mountVariantStock(host, {id: 42, sku: 'SAMPLE'}, { isCurrent: () => true,
    onDirty: (_id,value) => dirty.push(value), suppliers: async () => ({suppliers:[{id:'sample-supplier', name:'SAMPLE vendor', status:'active'}]}) });
  host.querySelector('[data-load-stock]').click(); await flush();
  const fill = (name,value) => {
    const input = host.querySelector(`[name="${name}"]`); input.value = value;
    host.dispatchEvent({ type: 'input', target: input, stopPropagation() {} });
  };
  fill('stock_cost','12.345'); host.querySelector('[data-save-mapping]').click(); await flush();
  assert.match(host.querySelector('[data-stock-feedback]').textContent, /two decimals/);
  assert.equal(calls.filter(c=>c.body).length,0);
  fill('stock_delta','3'); fill('stock_cost','12.34'); fill('stock_supplier','sample-supplier');
  host.querySelector('[data-adjust-stock]').click(); await flush();
  assert.match(host.querySelector('[data-stock-feedback]').textContent, /mapping before/);
  host.querySelector('[data-save-mapping]').click(); await flush();
  assert.deepEqual(calls.find(c=>c.url.endsWith('/variants')).body, { variant_id:42, supplier_cost_minor:1234, active:true });
  assert.equal(host.querySelector('[name="stock_delta"]').value,'3');
  assert.equal(dirty.at(-1),true);
  fail = true; host.querySelector('[data-adjust-stock]').click(); await flush();
  assert.match(host.querySelector('[data-stock-feedback]').textContent, /input is retained/);
  assert.equal(host.querySelector('[name="stock_delta"]').value,'3');
  const body = calls.find(c=>c.url.endsWith('/adjust')).body;
  assert.equal(body.expected_version,0); assert.equal(body.quantity_delta,3);
  fail = false; host.querySelector('[data-adjust-stock]').click(); await flush();
  assert.match(host.querySelector('[data-stock-feedback]').textContent, /saved/);
  assert.equal(dirty.at(-1),false);
  controller.destroy();
});

test('holds paginate with private order links, legacy explanations and empty states', async () => {
  const host = install(), calls=[];
  let failed = true;
  const initial = { ...state.mapping, total:21, held_reservations:25, holds:[{quantity:2, stage:'held', order_id:'sample-order', order_number:'SAMPLE-1', order_link:'/admin/orders?order_id=sample-order'},
    {quantity:3, stage:'dispatched', legacy_stock_hold:true, order_link:null}] };
  globalThis.fetch = async url => { calls.push(url); if (failed) throw new Error('SAMPLE offline'); return response({ ...initial, page:2, holds:[] }); };
  const view = mountStockHolds(host,'sample-link', initial);
  assert.match(host.innerHTML,/legacy reconciliation required/);
  assert.equal(host.querySelector('a').href,'/admin/orders?order_id=sample-order');
  assert.equal(host.querySelector('[data-holds-prev]').disabled,true);
  host.querySelector('[data-holds-refresh]').click(); await flush();
  assert.equal(host.querySelector('[data-holds-prev]').disabled,true);
  assert.equal(host.querySelector('[data-holds-next]').disabled,false);
  assert.match(host.querySelector('[role="status"]').textContent,/offline/);
  failed = false;
  host.querySelector('[data-holds-next]').click(); await flush();
  assert.match(calls.at(-1),/page=2/); assert.match(host.innerHTML,/No active holds/);
  assert.equal(host.querySelector('[data-holds-next]').disabled,true);
  view.destroy();
});

test('destroyed variant panels ignore late private responses', async () => {
  const host = install(); let finish;
  globalThis.fetch = () => new Promise(resolve => { finish = resolve; });
  const view = mountVariantStock(host,{id:1,sku:'SAMPLE'}, {isCurrent:()=>true, onDirty(){}, suppliers:async()=>({suppliers:[]})});
  host.querySelector('[data-load-stock]').click(); await flush();
  view.destroy(); const before=host.innerHTML;
  finish(response(state)); await flush();
  assert.equal(host.innerHTML,before);
});

test('inherits product supplier, renders supplier badge, omits inline supplier registration, and saves mapping', async () => {
  const host = install(), calls = [];
  const unmappedState = {
    public_availability: 'unavailable',
    readiness_reasons: ['No active supplier mapping'],
    historical_mappings: [],
    mapping: null,
  };
  globalThis.fetch = async (url, options = {}) => {
    calls.push({ url, body: options.body ? JSON.parse(options.body) : null });
    if (url.endsWith('/stock')) return response(unmappedState);
    return response({});
  };

  const suppliersList = {
    suppliers: [
      { id: 'internal-sup-id', name: 'AlphaZee Warehouse', supplier_type: 'alphazee_internal', status: 'active' },
      { id: 'vendor-sup-id', name: 'Silk Route Vendor', supplier_type: 'external_vendor', status: 'active' },
    ]
  };

  const vendorProduct = {
    stock_management_source: 'vendor_managed',
    vendor_id: 'vendor-sup-id',
  };
  const controller = mountVariantStock(host, { id: 101, sku: 'PROD-BLK-M' }, {
    isCurrent: () => true,
    onDirty() {},
    suppliers: async () => suppliersList,
    product: vendorProduct,
  });

  host.querySelector('[data-load-stock]').click();
  await flush();

  // Verify inline registration accordion is NOT present
  assert.equal(host.querySelector('[data-new-supplier]'), null);
  assert.equal(host.querySelector('[name="stock_new_name"]'), null);

  // Verify supplier badge shows vendor name
  assert.match(host.querySelector('.supplier-badge').textContent, /Silk Route Vendor/);

  // Verify preselected supplier value matches vendor
  assert.equal(host.querySelector('[name="stock_supplier"]').value, 'vendor-sup-id');

  // Fill cost and save
  const costInput = host.querySelector('[name="stock_cost"]');
  costInput.value = '2500';
  host.dispatchEvent({ type: 'input', target: costInput, stopPropagation() {} });

  host.querySelector('[data-save-mapping]').click();
  await flush();

  const assignCall = calls.find(c => c.url.includes('/suppliers/'));
  assert.ok(assignCall);
  assert.match(assignCall.url, /vendor-sup-id/);
  assert.deepEqual(assignCall.body, { variant_id: 101, supplier_cost_minor: 250000, active: true });

  controller.destroy();

  // Test 2: Internal managed product inherits alphazee_internal supplier
  const internalProduct = {
    stock_management_source: 'alphazee_managed',
    vendor_id: null,
  };
  const internalHost = install();
  const internalCalls = [];
  globalThis.fetch = async (url, options = {}) => {
    internalCalls.push({ url, body: options.body ? JSON.parse(options.body) : null });
    if (url.endsWith('/stock')) return response(unmappedState);
    return response({});
  };
  const internalController = mountVariantStock(internalHost, { id: 102, sku: 'PROD-WHT-S' }, {
    isCurrent: () => true,
    onDirty() {},
    suppliers: async () => suppliersList,
    product: internalProduct,
  });

  internalHost.querySelector('[data-load-stock]').click();
  await flush();

  assert.equal(internalHost.querySelector('[data-new-supplier]'), null);
  assert.match(internalHost.querySelector('.supplier-badge').textContent, /AlphaZee Warehouse/);
  assert.equal(internalHost.querySelector('[name="stock_supplier"]').value, 'internal-sup-id');

  const intCostInput = internalHost.querySelector('[name="stock_cost"]');
  intCostInput.value = '1800';
  internalHost.dispatchEvent({ type: 'input', target: intCostInput, stopPropagation() {} });

  internalHost.querySelector('[data-save-mapping]').click();
  await flush();

  const intAssignCall = internalCalls.find(c => c.url.includes('/suppliers/'));
  assert.ok(intAssignCall);
  assert.match(intAssignCall.url, /internal-sup-id/);
  assert.deepEqual(intAssignCall.body, { variant_id: 102, supplier_cost_minor: 180000, active: true });

  internalController.destroy();
});
