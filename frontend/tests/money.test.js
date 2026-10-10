import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { formatPkr, pkrToMinor, extractPriceMinor, formatDisplayPrice } from '../src/utils/money.js';

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

  it('formats fractional paisas with exact two-decimal precision', () => {
    assert.equal(formatPkr(345050), 'PKR 3,450.50');
    assert.equal(formatPkr(345099), 'PKR 3,450.99');
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

describe('extractPriceMinor', () => {
  it('extracts minor units from CurrencyAmount objects', () => {
    assert.equal(extractPriceMinor({ minor: 345050, formatted: 'PKR 3,450.50' }), 345050);
    assert.equal(extractPriceMinor({ minor: 0 }), 0);
  });

  it('extracts minor units from objects with price_minor or min_price_minor', () => {
    assert.equal(extractPriceMinor({ price_minor: 345000 }), 345000);
    assert.equal(extractPriceMinor({ min_price_minor: 680000 }), 680000);
  });

  it('extracts minor units from plain numbers', () => {
    assert.equal(extractPriceMinor(345000), 345000);
    assert.equal(extractPriceMinor(0), 0);
  });

  it('returns null for missing or invalid prices', () => {
    assert.equal(extractPriceMinor(null), null);
    assert.equal(extractPriceMinor(undefined), null);
    assert.equal(extractPriceMinor({ minor: -500 }), null);
    assert.equal(extractPriceMinor({ minor: 'invalid' }), null);
    assert.equal(extractPriceMinor(-100), null);
    assert.equal(extractPriceMinor(1.5), null);
    assert.equal(extractPriceMinor('345000'), null);
  });
});

describe('formatDisplayPrice', () => {
  it('prefers formatted string from CurrencyAmount object', () => {
    assert.equal(formatDisplayPrice({ formatted: 'PKR 3,450.50', minor: 345050 }), 'PKR 3,450.50');
  });

  it('formats minor units when formatted string is omitted', () => {
    assert.equal(formatDisplayPrice({ minor: 345000 }), 'PKR 3,450');
    assert.equal(formatDisplayPrice(345050), 'PKR 3,450.50');
  });

  it('returns fallback when price is missing or invalid', () => {
    assert.equal(formatDisplayPrice(null), 'Price unavailable');
    assert.equal(formatDisplayPrice(undefined), 'Price unavailable');
    assert.equal(formatDisplayPrice({ minor: -100 }), 'Price unavailable');
    assert.equal(formatDisplayPrice(null, 'N/A'), 'N/A');
  });
});
