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

  it('preserves items but marks availability as unverified on network / offline failure', async () => {
    const originalFetch = globalThis.fetch;
    try {
      cart.addItem({
        variant_id: 202,
        product_id: 'prod-tee',
        slug: 'offline-tee',
        title: 'Offline Tee',
        price_minor: 300000,
      });

      // Initially added item is considered available
      assert.equal(cart.getState().items[0].is_available, true);

      // Simulate offline / network error (rejecting fetch)
      globalThis.fetch = async () => {
        throw new Error('TypeError: Failed to fetch (offline)');
      };

      await cart.reconcileWithApi();

      const state = cart.getState();
      assert.equal(state.items.length, 1);
      assert.equal(state.items[0].is_available, false);
      assert.equal(state.items[0].availability, 'unverified');
      assert.equal(state.hasUnavailable, true);
      assert.equal(state.hasUnverified, true);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it('rejects fractional quantity in addItem and fractional deltas in updateQuantity', () => {
    // addItem rejects fractional quantities
    assert.equal(cart.addItem({ variant_id: 301, product_id: 'p1', title: 'Tee', price_minor: 100 }, {}, 1.5), false);
    assert.equal(cart.addItem({ variant_id: 301, product_id: 'p1', title: 'Tee', price_minor: 100 }, {}, 0), false);
    assert.equal(cart.addItem({ variant_id: 301, product_id: 'p1', title: 'Tee', price_minor: 100 }, {}, -1), false);
    assert.equal(cart.getState().count, 0);

    // Add valid item with quantity 2
    assert.equal(cart.addItem({ variant_id: 301, product_id: 'p1', title: 'Tee', price_minor: 100 }, {}, 2), true);
    assert.equal(cart.getState().count, 2);

    // updateQuantity rejects fractional deltas like 1.5, -0.5, or strings
    cart.updateQuantity(301, 1.5);
    assert.equal(cart.getState().count, 2); // remains 2

    cart.updateQuantity(301, -0.5);
    assert.equal(cart.getState().count, 2); // remains 2

    cart.updateQuantity(301, '1');
    assert.equal(cart.getState().count, 2); // remains 2

    // Integer delta works
    cart.updateQuantity(301, 1);
    assert.equal(cart.getState().count, 3);
  });

  it('strictly validates safe integers for variant_id', () => {
    // Non-safe integer or float variant IDs rejected
    assert.equal(cart.addItem({ variant_id: 1.5, product_id: 'p1', title: 'Tee', price_minor: 100 }), false);
    assert.equal(cart.addItem({ variant_id: Number.MAX_SAFE_INTEGER + 1, product_id: 'p1', title: 'Tee', price_minor: 100 }), false);
    assert.equal(cart.addItem({ variant_id: Infinity, product_id: 'p1', title: 'Tee', price_minor: 100 }), false);
    assert.equal(cart.addItem({ variant_id: NaN, product_id: 'p1', title: 'Tee', price_minor: 100 }), false);
    assert.equal(cart.addItem({ variant_id: '9007199254740992', product_id: 'p1', title: 'Tee', price_minor: 100 }), false);

    // Safe integer variant ID accepted
    assert.equal(cart.addItem({ variant_id: Number.MAX_SAFE_INTEGER, product_id: 'p1', title: 'Tee', price_minor: 100 }), true);
    assert.equal(cart.getState().items[0].variant_id, Number.MAX_SAFE_INTEGER);
  });

  it('rejects negative or missing prices and prevents adding invalid price items', () => {
    // Missing price rejected
    assert.equal(cart.addItem({
      variant_id: 401,
      product_id: 'p1',
      title: 'Tee',
    }), false);

    // Negative nested price rejected
    assert.equal(cart.addItem({
      variant_id: 402,
      product_id: 'p1',
      title: 'Tee',
      price: { minor: -500 },
    }), false);

    // Negative direct price_minor rejected
    assert.equal(cart.addItem({
      variant_id: 403,
      product_id: 'p1',
      title: 'Tee',
      price_minor: -100,
    }), false);

    assert.equal(cart.getState().count, 0);

    // Valid price with minor units accepted
    assert.equal(cart.addItem({
      variant_id: 404,
      product_id: 'p1',
      title: 'Tee',
      price: { minor: 345050, formatted: 'PKR 3,450.50' },
    }), true);

    const state = cart.getState();
    assert.equal(state.count, 1);
    assert.equal(state.items[0].price_minor, 345050);
    assert.equal(state.total_minor, 345050);
    assert.equal(state.formattedTotal, 'PKR 3,450.50');
  });

  it('marks item unavailable during reconciliation if live variant has missing/invalid price', async () => {
    const originalFetch = globalThis.fetch;
    try {
      cart.addItem({
        variant_id: 501,
        product_id: 'p1',
        slug: 'invalid-price-prod',
        title: 'Tee',
        price_minor: 345000,
      });

      assert.equal(cart.getState().items[0].is_available, true);

      // Live variant returns invalid price
      globalThis.fetch = async () => ({
        ok: true,
        json: async () => ({
          slug: 'invalid-price-prod',
          variants: [
            {
              id: 501,
              price: { minor: -500 }, // invalid price
              availability: 'available',
            },
          ],
        }),
      });

      await cart.reconcileWithApi();

      const item = cart.getState().items[0];
      assert.equal(item.is_available, false);
      assert.equal(item.availability, 'unavailable');
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it('marks item unverified during reconciliation if slug is missing', async () => {
    cart.addItem({
      variant_id: 601,
      product_id: 'p-no-slug',
      slug: '', // missing slug
      title: 'No Slug Piece',
      price_minor: 250000,
    });

    assert.equal(cart.getState().items[0].is_available, true);

    await cart.reconcileWithApi();

    const item = cart.getState().items[0];
    assert.equal(item.is_available, false);
    assert.equal(item.availability, 'unverified');
    assert.equal(cart.getState().hasUnavailable, true);
    assert.equal(cart.getState().hasUnverified, true);
  });

  it('exposes isReconciling state during active reconciliation', async () => {
    const originalFetch = globalThis.fetch;
    try {
      cart.addItem({
        variant_id: 701,
        product_id: 'p7',
        slug: 'slow-slug',
        title: 'Slow Item',
        price_minor: 100000,
      });

      let reconcileObserved = false;
      globalThis.fetch = async () => {
        // While fetch is ongoing, check isReconciling
        reconcileObserved = cart.getState().isReconciling;
        return {
          ok: true,
          json: async () => ({
            slug: 'slow-slug',
            variants: [{ id: 701, price: { minor: 100000 }, availability: 'available' }],
          }),
        };
      };

      assert.equal(cart.getState().isReconciling, false);
      const promise = cart.reconcileWithApi();
      await promise;

      assert.equal(reconcileObserved, true);
      assert.equal(cart.getState().isReconciling, false);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });
});
