import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { formatPkr, pkrToMinor } from '../src/utils/money.js';

describe('formatPkr', () => {
  it('formats standard minor units to PKR with comma separator', () => {
    assert.equal(formatPkr(345000), 'PKR 3,450');
    assert.equal(formatPkr(680000), 'PKR 6,800');
    assert.equal(formatPkr(1250000), 'PKR 12,500');
  });

  it('formats zero correctly', () => {
    assert.equal(formatPkr(0), 'PKR 0');
  });

  it('handles null, undefined, and NaN gracefully', () => {
    assert.equal(formatPkr(null), 'PKR 0');
    assert.equal(formatPkr(undefined), 'PKR 0');
    assert.equal(formatPkr(NaN), 'PKR 0');
  });

  it('handles fractional paisas by integer division without floating errors', () => {
    // 345099 paisas = 3450 rupees
    assert.equal(formatPkr(345099), 'PKR 3,450');
  });
});

describe('pkrToMinor', () => {
  it('converts whole rupees to integer paisas', () => {
    assert.equal(pkrToMinor(3450), 345000);
    assert.equal(pkrToMinor(0), 0);
  });

  it('handles non-numeric inputs safely', () => {
    assert.equal(pkrToMinor('invalid'), 0);
    assert.equal(pkrToMinor(null), 0);
  });
});
