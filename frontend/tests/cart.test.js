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
});
