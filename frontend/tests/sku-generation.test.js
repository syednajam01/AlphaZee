import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { generateSku } from '../src/utils/sku.js';

describe('SKU Generation Algorithm', () => {
  it('generates SKU for user exact specification: syed najam ul huda + green + medium -> snuh-g-m', () => {
    const sku = generateSku('syed najam ul huda', 'green', 'medium');
    assert.strictEqual(sku, 'snuh-g-m');
  });

  it('handles standard single and multi-word product titles', () => {
    assert.strictEqual(generateSku('Linen Shirt', 'Navy', 'M'), 'ls-n-m');
    assert.strictEqual(generateSku('Silk Tunic', 'Crimson', 'S'), 'st-c-s');
    assert.strictEqual(generateSku('Boxy Graphic Tee', 'Black', 'XL'), 'bgt-b-xl');
  });

  it('handles multi-word colors properly', () => {
    assert.strictEqual(generateSku('Casual Hoodie', 'Royal Blue', 'One Size'), 'ch-rb-os');
    assert.strictEqual(generateSku('Denim Jacket', 'Dark Olive Green', 'L'), 'dj-dog-l');
  });

  it('handles numeric and standard size codes', () => {
    assert.strictEqual(generateSku('Slim Chino', 'Beige', '32'), 'sc-b-32');
    assert.strictEqual(generateSku('Classic Polo', 'White', '2XL'), 'cp-w-2xl');
    assert.strictEqual(generateSku('Cotton Vest', 'Grey', 'Extra Large'), 'cv-g-xl');
  });

  it('falls back gracefully on empty or special character inputs', () => {
    assert.strictEqual(generateSku('', '', ''), 'prod-c-sz');
    assert.strictEqual(generateSku('!!!', '???', '---'), 'prod-c-sz');
  });
});
