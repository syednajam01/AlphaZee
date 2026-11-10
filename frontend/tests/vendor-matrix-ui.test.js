import { test } from 'node:test';
import assert from 'node:assert/strict';
import { installDom } from '../react-tests/dom.js';
import { initVendorPortal } from '../src/components/VendorPortal.js';

const tick = () => new Promise(resolve => setTimeout(resolve, 20));
function setup() {
  const { dom } = installDom(); let poll, cleared = false, reads = 0, gate;
  window.setInterval = callback => { poll = callback; return 99; };
  window.clearInterval = id => { cleared = id === 99; };
  const item = { variant_id: 7, product_id: 'sample', product_title: 'SAMPLE tee', color: 'Ink', size: 'M', variant_sku: 'SAMPLE-M', allocated_on_hand: 10, held_quantity: 2, available_quantity: 8, version: 1, supplier_cost_minor: 140000 };
  globalThis.fetch = async url => {
    if (String(url).includes('/auth/session')) return { ok: true, json: async () => ({ authenticated: true, csrf_token: 'sample-test-only', username: 'SAMPLE staff', vendor_name: 'SAMPLE shop' }) };
    reads++; const wait = gate; gate = null; if (wait) await wait;
    return { ok: true, json: async () => ({ items: [{ ...item }], total_items: 1 }) };
  };
  const app = initVendorPortal();
  return { dom, app, item, poll: () => poll(), reads: () => reads, cleared: () => cleared, defer: promise => { gate = promise; } };
}

test('visible polling preserves edits/focus, pauses inside dialogs and is removed on destroy', async () => {
  const state = setup();
  try {
    await tick();
    let input = document.getElementById('vp-matrix-count-7'); input.focus(); input.value = '12'; input.dispatchEvent(new window.Event('input')); input.setSelectionRange(0, 1);
    state.poll(); await tick();
    input = document.getElementById('vp-matrix-count-7');
    assert.equal(input.value, '12'); assert.equal(document.activeElement.id, input.id);
    assert.equal(input.selectionStart, 0); assert.equal(input.selectionEnd, 1);
    const search = document.getElementById('vp-stock-search'); search.focus(); search.value = 'SAMPLE'; search.dispatchEvent(new window.Event('input')); search.setSelectionRange(1, 3);
    state.poll(); await tick();
    assert.equal(document.getElementById('vp-stock-search').value, 'SAMPLE');
    assert.equal(document.getElementById('vp-stock-search').selectionStart, 1);
    // Let the independent search debounce settle before measuring polling.
    await new Promise(resolve => setTimeout(resolve, 350));
    document.getElementById('vp-count-open-7').click();
    document.getElementById('vp-note').value = 'SAMPLE unsaved note';
    const before = state.reads(); state.poll(); await tick();
    assert.equal(state.reads(), before); assert.equal(document.getElementById('vp-note').value, 'SAMPLE unsaved note');
    state.app.destroy(); assert(state.cleared()); assert.equal(document.getElementById('app').textContent, '');
    state.poll(); window.dispatchEvent(new window.Event('focus')); await tick(); assert.equal(state.reads(), before);
  } finally { state.app.destroy(); state.dom.window.close(); }
});

test('an in-flight background refresh cannot erase a newly opened count dialog note', async () => {
  const state = setup();
  try {
    await tick(); let release;
    state.defer(new Promise(resolve => { release = resolve; })); state.poll();
    document.getElementById('vp-count-open-7').click(); document.getElementById('vp-note').value = 'SAMPLE keep this note';
    state.item.allocated_on_hand = 15; state.item.version = 2;
    release(); await tick();
    assert.equal(document.getElementById('vp-note').value, 'SAMPLE keep this note');
    document.getElementById('vp-cancel-count').click();
    assert.equal(document.getElementById('vp-matrix-count-7').value, '15');
  } finally { state.app.destroy(); state.dom.window.close(); }
});

test('a pending search debounce preserves a subsequently opened count dialog', async () => {
  const state = setup();
  try {
    await tick();
    const search = document.getElementById('vp-stock-search');
    search.value = 'SAMPLE'; search.dispatchEvent(new window.Event('input'));
    document.getElementById('vp-count-open-7').click();
    document.getElementById('vp-note').value = 'SAMPLE pending search note';
    await new Promise(resolve => setTimeout(resolve, 400));
    assert.equal(document.getElementById('vp-note').value, 'SAMPLE pending search note');
    document.getElementById('vp-cancel-count').click();
    assert.equal(document.getElementById('vp-stock-search').value, 'SAMPLE');
  } finally { state.app.destroy(); state.dom.window.close(); }
});
