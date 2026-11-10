import { test } from 'node:test';
import assert from 'node:assert/strict';
import { fetchVendorSession, fetchVendorStock, reportVendorShortage, updateVendorStockCount } from '../src/utils/api.js';

test('vendor session restore, pagination and shortage payload match backend contracts', async () => {
  const previous = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url, options = {}) => {
    calls.push({ url, options });
    return { ok: true, status: 200, json: async () => ({ csrf_token: 'sample-only' }) };
  };
  try {
    await fetchVendorSession();
    assert.equal(calls[0].url, '/api/v1/vendor/auth/session');
    assert.equal(calls[0].options.cache, 'no-store');
    await fetchVendorStock({ page: 3, limit: 50, search: 'tee & ink' });
    const query = new URL(calls[1].url, 'https://sample.invalid').searchParams;
    assert.equal(query.get('offset'), '100');
    assert.equal(query.get('limit'), '50');
    assert.equal(query.get('search'), 'tee & ink');
    assert.equal(query.has('page'), false);
    await reportVendorShortage(42, { reported_count: 0, note: 'SAMPLE damaged unit' });
    assert.equal(calls[2].url, '/api/v1/vendor/stock/42/shortage');
    assert.deepEqual(JSON.parse(calls[2].options.body), { variant_id: 42, reported_count: 0, note: 'SAMPLE damaged unit' });
    assert.equal(calls[2].options.headers['X-CSRF-Token'], 'sample-only');
  } finally { globalThis.fetch = previous; }
});

test('vendor stock writes notify other local tabs without private stock or identity data', async () => {
  const previousFetch = globalThis.fetch, previousWindow = globalThis.window;
  const notices = [], events = [];
  globalThis.window = { localStorage: { setItem: (key, value) => notices.push({ key, value }) }, dispatchEvent: event => events.push(event.type) };
  globalThis.fetch = async () => ({ ok: true, status: 200, json: async () => ({}) });
  try {
    await updateVendorStockCount(42, { counted_quantity: 8, expected_version: 1, reason: 'manual_count' });
    assert.equal(notices[0].key, 'alphazee_catalog_changed');
    assert.match(notices[0].value, /^\d+-[\d.]+$/);
    assert.deepEqual(events, ['alphazee:catalog-change']);
  } finally { globalThis.fetch = previousFetch; globalThis.window = previousWindow; }
});
