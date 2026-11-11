import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createMockElement } from './helpers/dom.js';
import { createAdminConsoleModal } from '../src/components/AdminConsole.js';

const tick = () => new Promise(resolve => setTimeout(resolve, 30));

test('Admin Inventory Workspace: search, stock filter pills, inline stepper editing, and no add button', async () => {
  const doc = createMockElement('document');
  doc.body = createMockElement('body');
  doc.createElement = createMockElement;
  doc.activeElement = doc.body;
  globalThis.document = doc;
  globalThis.window = { localStorage: { removeItem() {} }, sessionStorage: { removeItem() {} } };
  globalThis.confirm = () => true;

  const calls = [];
  const items = [
    {
      supplier_variant_id: 'sv-1',
      supplier_id: 'supp-1',
      supplier_name: 'Vendor Alpha',
      variant_id: 101,
      product_title: 'syed najam ul huda shirt',
      sku: 'snuhs-g-m',
      color: 'Green',
      size: 'Medium',
      physical_on_hand: 5,
      held_reservations: 1,
      available_to_sell: 4,
      version: 1,
    },
    {
      supplier_variant_id: 'sv-2',
      supplier_id: 'supp-1',
      supplier_name: 'Vendor Alpha',
      variant_id: 102,
      product_title: 'Linen Kurta',
      sku: 'lk-w-s',
      color: 'White',
      size: 'Small',
      physical_on_hand: 2,
      held_reservations: 0,
      available_to_sell: 2, // Low stock (< 3)
      version: 1,
    },
    {
      supplier_variant_id: 'sv-3',
      supplier_id: 'supp-2',
      supplier_name: 'Vendor Beta',
      variant_id: 103,
      product_title: 'Denim Jeans',
      sku: 'dj-b-32',
      color: 'Blue',
      size: '32',
      physical_on_hand: 0,
      held_reservations: 0,
      available_to_sell: 0, // Out of stock (0)
      version: 1,
    },
  ];

  globalThis.fetch = async (url, options = {}) => {
    const path = String(url);
    const body = options.body ? JSON.parse(options.body) : null;
    calls.push({ path, body });
    if (path.endsWith('/auth/session')) return { ok: true, status: 200, json: async () => ({ username: 'syed123', csrf_token: 'csrf-xyz' }) };
    if (path.endsWith('/admin/overview')) return { ok: true, status: 200, json: async () => ({ total_skus: 3, low_stock_skus: 1 }) };
    if (path.endsWith('/admin/inventory/summary')) return { ok: true, status: 200, json: async () => ({ items, total_variants: 3 }) };
    if (path.endsWith('/admin/inventory/adjust')) {
      const it = items.find(x => x.supplier_variant_id === body.supplier_variant_id);
      if (it) {
        it.physical_on_hand += body.quantity_delta;
        it.available_to_sell = Math.max(0, it.physical_on_hand - it.held_reservations);
        it.version++;
      }
      return { ok: true, status: 200, json: async () => ({ physical_on_hand: it.physical_on_hand, version: it.version }) };
    }
    return { ok: true, status: 200, json: async () => ({}) };
  };

  const admin = createAdminConsoleModal();
  doc.body.appendChild(admin.element);
  await admin.open();
  await tick();

  // Switch to inventory tab
  const invBtn = admin.element.querySelectorAll('.admin-tab-btn').find(b => b.dataset.tab === 'inventory');
  invBtn.click();
  await tick();

  const container = admin.element.querySelector('#admin-tab-content');
  assert.ok(container, 'Inventory content mounted');

  // 1. Verify NO "+" add button exists
  const addButtons = container.querySelectorAll('.btn-add-product, .btn-primary:not(.inv-save-btn)');
  assert.equal(addButtons.length, 0, 'No add product button on inventory tab');

  // 2. Verify Toolbar: Search Input and Filter Pills
  const searchInput = container.querySelector('#inv-search-input');
  assert.ok(searchInput, 'Search input exists');

  const filterPills = container.querySelectorAll('.inv-filter-pill');
  assert.equal(filterPills.length, 4, '4 filter pills exist (all, low, zero, normal)');

  // 3. Test Filter Pill: Low Stock (< 3)
  const lowPill = filterPills.find(p => p.dataset.filter === 'low');
  assert.ok(lowPill, 'Low stock pill exists');
  lowPill.click();
  await tick();

  let displayedRows = container.querySelectorAll('.inv-row');
  assert.equal(displayedRows.length, 1, 'Only 1 row shown for low stock');
  assert.ok(displayedRows[0].textContent.includes('Linen Kurta'), 'Linen Kurta is the low stock item');

  // 4. Test Filter Pill: 0 Out of Stock
  const zeroPill = filterPills.find(p => p.dataset.filter === 'zero');
  zeroPill.click();
  await tick();
  displayedRows = container.querySelectorAll('.inv-row');
  assert.equal(displayedRows.length, 1, 'Only 1 row shown for out of stock');
  assert.ok(displayedRows[0].textContent.includes('Denim Jeans'), 'Denim Jeans is out of stock');

  // 5. Test Filter Pill: Normal Stock
  const normalPill = filterPills.find(p => p.dataset.filter === 'normal');
  normalPill.click();
  await tick();
  displayedRows = container.querySelectorAll('.inv-row');
  assert.equal(displayedRows.length, 1, 'Only 1 row shown for normal stock');
  assert.ok(displayedRows[0].textContent.includes('syed najam ul huda shirt'));

  // 6. Reset to All
  const allPill = filterPills.find(p => p.dataset.filter === 'all');
  allPill.click();
  await tick();
  displayedRows = container.querySelectorAll('.inv-row');
  assert.equal(displayedRows.length, 3, 'All 3 rows shown');

  // 7. Test Search Query: "snuh"
  searchInput.value = 'snuh';
  searchInput.dispatchEvent({ type: 'input', target: searchInput });
  await tick();
  displayedRows = container.querySelectorAll('.inv-row');
  assert.equal(displayedRows.length, 1, 'Search filters to 1 item');
  assert.ok(displayedRows[0].textContent.includes('snuhs-g-m'));

  // Clear search
  const clearBtn = container.querySelector('#inv-search-clear');
  clearBtn.click();
  await tick();
  assert.equal(container.querySelectorAll('.inv-row').length, 3);

  // 8. Test Inline Stepper & Save: Increase physical stock of first item from 5 to 8
  const firstRow = container.querySelectorAll('.inv-row')[0];
  const stepper = firstRow.querySelector('.inv-stepper');
  const stepperInput = stepper.querySelector('.inv-stepper-input');
  const plusBtn = stepper.querySelector('.btn-plus');
  const saveBtn = stepper.querySelector('.inv-save-btn');

  assert.equal(stepperInput.value, '5');
  plusBtn.click();
  plusBtn.click();
  plusBtn.click();
  assert.equal(stepperInput.value, '8');

  // Save button should now be visible
  assert.equal(saveBtn.hidden, false, 'Save button is visible when stock modified');

  // Click Save
  saveBtn.click();
  await tick();

  const adjustCall = calls.find(c => c.path.endsWith('/admin/inventory/adjust'));
  assert.ok(adjustCall, 'adjustAdminInventory API called');
  assert.equal(adjustCall.body.quantity_delta, 3);
  assert.equal(adjustCall.body.expected_version, 1);
  assert.equal(adjustCall.body.reason, 'manual_count');

  // Verify dynamic available calculation: Physical 8 - Held 1 = Available 7
  assert.equal(items[0].physical_on_hand, 8);
  assert.equal(items[0].available_to_sell, 7);

  admin.close();
});
