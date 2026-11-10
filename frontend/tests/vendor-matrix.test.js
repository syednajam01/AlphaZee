import { test } from 'node:test';
import assert from 'node:assert/strict';
import { groupVendorStock, parseVendorCount, VendorCountDrafts } from '../src/utils/vendorMatrix.js';

const item = (id = 1, extra = {}) => ({ variant_id: id, product_id: 'shirt', product_title: 'Oxford', color: 'Ink', size: 'M', allocated_on_hand: 10, held_quantity: 2, version: 4, ...extra });

test('matrix groups by stable product identity/color and sorts sizes without dropping duplicate sizes', () => {
  const groups = groupVendorStock([item(1, { size: 'XL' }), item(2, { size: 'S' }), item(3, { size: 'M' }), item(4, { product_id: 'other' }), item(5, { color: 'Chalk' }), item(6, { size: 'S' })]);
  assert.equal(groups.length, 3);
  assert.deepEqual(groups[0].items.map(row => row.variant_id), [2, 6, 3, 1]);
});

test('count validation rejects blank, fractions, exponent forms, negative and overflow values', () => {
  for (const value of ['', '-1', '1.2', '1e3', 'Infinity', '2147483648', ' 2 ']) assert.equal(parseVendorCount(value), null);
  assert.equal(parseVendorCount('0'), 0); assert.equal(parseVendorCount('0012'), 12);
});

test('only actual changes are pending; versions survive refresh and conflicts require explicit reset', () => {
  const drafts = new VendorCountDrafts(), row = item();
  drafts.edit(row, '010'); assert.equal(drafts.pending().length, 0);
  drafts.edit(row, '8'); drafts.reconcile([item(1, { version: 5, allocated_on_hand: 9 })]);
  assert.equal(drafts.get(1).value, '8'); assert.equal(drafts.get(1).baseVersion, 4);
  assert.equal(drafts.snapshot([1])[0].needsReview, true);
  drafts.edit(item(1, { version: 5, allocated_on_hand: 9 }), '7');
  assert.equal(drafts.get(1).baseVersion, 4);
  drafts.reset(1); drafts.edit(item(1, { version: 5 }), '7');
  assert.equal(drafts.get(1).baseVersion, 5);
});

test('partial saves retain failures and never resubmit successful or reported sizes', () => {
  const drafts = new VendorCountDrafts();
  for (const id of [1, 2, 3]) drafts.edit(item(id), '8');
  drafts.acknowledge(1, { variant_id: 1, allocated_on_hand: 8, version: 5 });
  drafts.fail(2, { status: 503, message: 'SAMPLE unavailable' });
  drafts.acknowledge(3, { variant_id: 3, allocated_on_hand: 10, version: 4, shortage_detected: true });
  assert.deepEqual(drafts.snapshot([1, 2, 3]).map(d => d.item.variant_id), [2]);
  assert.equal(drafts.get(3).value, '8'); assert.match(drafts.get(3).message, /Recorded stock stays 10/);
});

test('drafts on another page survive reconciliation and clearing removes all vendor data', () => {
  const drafts = new VendorCountDrafts(); drafts.edit(item(), '6');
  drafts.reconcile([item(2)]); assert.equal(drafts.get(1).value, '6');
  drafts.clear(); assert.equal(drafts.entries.size, 0);
});

test('batch snapshots follow the displayed size order after resets and retries', () => {
  const drafts = new VendorCountDrafts();
  drafts.edit(item(2), '6'); drafts.edit(item(1), '7');
  assert.deepEqual(drafts.snapshot([1, 2]).map(change => change.item.variant_id), [1, 2]);
});
