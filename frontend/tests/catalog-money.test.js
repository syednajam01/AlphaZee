import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseCatalogPkr } from '../src/utils/money.js';

test('catalog PKR input converts exact decimal text within storage bounds', () => {
  assert.equal(parseCatalogPkr('3450.50'), 345050);
  assert.equal(parseCatalogPkr('0.29'), 29);
  assert.equal(parseCatalogPkr('0'), 0);
  assert.equal(parseCatalogPkr(' 001.2 '), 120);
  assert.equal(parseCatalogPkr('21474836.47'), 2147483647);
  for (const value of ['21474836.48', '999999999999999999999', '1.005', '-1', '1e3', '', '1,234', 'NaN', true, 1.2]) {
    assert.equal(parseCatalogPkr(value), null);
  }
});
