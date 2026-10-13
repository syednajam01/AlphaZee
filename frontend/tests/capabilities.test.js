import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createCapabilitiesStore } from '../src/utils/capabilities.js';

test('checkout starts closed and requires explicit isolated test capabilities', async () => {
  for (const payload of [null, {}, { checkout_enabled: true }, { checkout_enabled: 'true', test_mode: true }]) {
    const store = createCapabilitiesStore(async () => payload);
    assert.equal(store.getState().checkoutEnabled, false);
    await store.refresh();
    assert.equal(store.getState().checkoutEnabled, false);
  }
  const store = createCapabilitiesStore(async () => ({ checkout_enabled: true, test_mode: true }));
  await store.refresh();
  assert.equal(store.getState().checkoutEnabled, true);
  assert.deepEqual(store.getState().paymentMethods, ['cod']);
});

test('bank transfer is advertised only when the API explicitly enables it', async () => {
  const store = createCapabilitiesStore(async () => ({ checkout_enabled: true, test_mode: true, payment_methods: ['cod', 'bank_transfer', 'unknown'] }));
  await store.refresh();
  assert.deepEqual(store.getState().paymentMethods, ['cod', 'bank_transfer']);
});

test('failed capability refresh closes checkout and notifies subscribers', async () => {
  let fail = false;
  const observed = [];
  const store = createCapabilitiesStore(async () => {
    if (fail) throw new Error('API offline');
    return { checkout_enabled: true, test_mode: true };
  });
  store.subscribe(state => observed.push(state.checkoutEnabled));
  await store.refresh();
  fail = true;
  const pending = store.refresh();
  assert.equal(store.getState().checkoutEnabled, false);
  await pending;
  assert.equal(store.getState().checkoutEnabled, false);
  assert.ok(observed.includes(true));
  assert.equal(observed.at(-1), false);
});
