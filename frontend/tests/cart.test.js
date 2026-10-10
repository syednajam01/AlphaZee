import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { cart } from '../src/utils/cart.js';

describe('CartStore', () => {
  beforeEach(() => {
    cart.clear();
  });

  it('adds valid item keyed by variant_id', () => {
    const success = cart.addItem({
      variant_id: 101,
      product_id: 'prod-tee',
      title: 'Boxy Tee',
      price_minor: 345000,
      size: 'M',
      color: 'Chalk White',
    }, {}, 1);

    assert.equal(success, true);
    const state = cart.getState();
    assert.equal(state.count, 1);
    assert.equal(state.items.length, 1);
    assert.equal(state.items[0].variant_id, 101);
    assert.equal(state.total_minor, 345000);
    assert.equal(state.formattedTotal, 'PKR 3,450');
  });

  it('increments quantity when same variant_id added', () => {
    cart.addItem({
      variant_id: 101,
      product_id: 'prod-tee',
      title: 'Boxy Tee',
      price_minor: 345000,
    }, {}, 1);

    cart.addItem({
      variant_id: 101,
      product_id: 'prod-tee',
      title: 'Boxy Tee',
      price_minor: 345000,
    }, {}, 2);

    const state = cart.getState();
    assert.equal(state.count, 3);
    assert.equal(state.items.length, 1);
    assert.equal(state.total_minor, 1035000);
    assert.equal(state.formattedTotal, 'PKR 10,350');
  });

  it('rejects items missing variant_id', () => {
    const success = cart.addItem({
      product_id: 'prod-tee',
      title: 'Boxy Tee',
      price_minor: 345000,
      // no variant_id
    });

    assert.equal(success, false);
    assert.equal(cart.getState().count, 0);
  });

  it('clamps maximum quantity to 99', () => {
    cart.addItem({
      variant_id: 101,
      product_id: 'prod-tee',
      title: 'Boxy Tee',
      price_minor: 345000,
    }, {}, 150);

    const state = cart.getState();
    assert.equal(state.count, 99);
  });

  it('updates quantity and removes when zero or below', () => {
    cart.addItem({
      variant_id: 101,
      product_id: 'prod-tee',
      title: 'Boxy Tee',
      price_minor: 345000,
    }, {}, 2);

    cart.updateQuantity(101, -1);
    assert.equal(cart.getState().count, 1);

    cart.updateQuantity(101, -1);
    assert.equal(cart.getState().count, 0);
    assert.equal(cart.getState().items.length, 0);
  });

  it('removes item by variant_id', () => {
    cart.addItem({
      variant_id: 101,
      product_id: 'prod-tee',
      title: 'Boxy Tee',
      price_minor: 345000,
    });
    cart.addItem({
      variant_id: 102,
      product_id: 'prod-hoodie',
      title: 'Fleece Hoodie',
      price_minor: 680000,
    });

    assert.equal(cart.getState().count, 2);
    cart.removeItem(101);
    assert.equal(cart.getState().count, 1);
    assert.equal(cart.getState().items[0].variant_id, 102);
  });

  it('rejects invalid variant_id types (objects, arrays, booleans, negative numbers)', () => {
    assert.equal(cart.addItem({ variant_id: {}, product_id: 'p1', title: 'Tee', price_minor: 100 }), false);
    assert.equal(cart.addItem({ variant_id: [], product_id: 'p1', title: 'Tee', price_minor: 100 }), false);
    assert.equal(cart.addItem({ variant_id: true, product_id: 'p1', title: 'Tee', price_minor: 100 }), false);
    assert.equal(cart.addItem({ variant_id: false, product_id: 'p1', title: 'Tee', price_minor: 100 }), false);
    assert.equal(cart.addItem({ variant_id: -5, product_id: 'p1', title: 'Tee', price_minor: 100 }), false);
    assert.equal(cart.addItem({ variant_id: 0, product_id: 'p1', title: 'Tee', price_minor: 100 }), false);
    assert.equal(cart.addItem({ variant_id: 'abc', product_id: 'p1', title: 'Tee', price_minor: 100 }), false);
    assert.equal(cart.addItem({ variant_id: '  ', product_id: 'p1', title: 'Tee', price_minor: 100 }), false);
    assert.equal(cart.getState().count, 0);

    // Valid string digit ID should be accepted and coerced to number
    assert.equal(cart.addItem({ variant_id: ' 105 ', product_id: 'p1', title: 'Tee', price_minor: 100 }), true);
    assert.equal(cart.getState().items[0].variant_id, 105);
  });

  it('reconciles price.minor and availability from live API without requiring is_active', async () => {
    const originalFetch = globalThis.fetch;
    try {
      cart.addItem({
        variant_id: 201,
        product_id: 'prod-tee',
        slug: 'boxy-tee',
        title: 'Boxy Tee',
        price_minor: 300000,
      });

      globalThis.fetch = async () => ({
        ok: true,
        json: async () => ({
          slug: 'boxy-tee',
          variants: [
            {
              id: 201,
              price: { minor: 350000, pkr: 3500, formatted: 'PKR 3,500' },
              availability: 'available',
              // Note: is_active is omitted by public API schema
            },
          ],
        }),
      });

      await cart.reconcileWithApi();

      const item = cart.getState().items[0];
      assert.equal(item.price_minor, 350000);
      assert.equal(item.is_available, true);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it('marks items unavailable when API returns 404 for product', async () => {
    const originalFetch = globalThis.fetch;
    try {
      cart.addItem({
        variant_id: 201,
        product_id: 'prod-tee',
        slug: 'deleted-tee',
        title: 'Deleted Tee',
        price_minor: 300000,
      });
      assert.equal(cart.getState().items[0].is_available, true);

      globalThis.fetch = async () => ({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: async () => ({ detail: 'Product not found' }),
      });

      await cart.reconcileWithApi();

      const item = cart.getState().items[0];
      assert.equal(item.is_available, false);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });
});
