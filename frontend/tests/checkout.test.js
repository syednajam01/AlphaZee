import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { cart } from '../src/utils/cart.js';
import { submitOrder, recoverPendingOrder, getPendingCheckoutAttempt, uploadReceipt, fetchOrderStatus, ApiError } from '../src/utils/api.js';

describe('Storefront Order API Client & Checkout Cart State', () => {
  let originalFetch;

  beforeEach(() => {
    cart.clear();
    originalFetch = global.fetch;
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('retries a lost checkout response with the same key and payload', async () => {
    const payload = { customer_name: 'SAMPLE Buyer', items: [{ variant_id: 101, quantity: 1 }] };
    const submissions = [];
    let loseResponse = true;
    global.fetch = async (url, options) => {
      if (String(url).endsWith('/checkout-session')) return { ok: true, json: async () => ({ ready: true }) };
      submissions.push({ key: options.headers['Idempotency-Key'], body: options.body });
      if (loseResponse) { loseResponse = false; throw new Error('Connection lost'); }
      return { ok: true, json: async () => ({ id: 'SAMPLE-order-1' }) };
    };
    await assert.rejects(submitOrder(payload), /Connection lost/);
    assert.equal(getPendingCheckoutAttempt()?.payload.customer_name, 'SAMPLE Buyer');
    await assert.rejects(submitOrder({ ...payload, customer_name: 'Changed Buyer' }), /previous checkout/i);
    const recovered = await recoverPendingOrder();
    assert.equal(recovered.id, 'SAMPLE-order-1');
    assert.equal(submissions.length, 2);
    assert.equal(submissions[0].key, submissions[1].key);
    assert.equal(submissions[0].body, submissions[1].body);
    assert.equal(getPendingCheckoutAttempt(), null);
  });

  it('recovers a pending attempt from session storage after module reload', async () => {
    const oldWindow = globalThis.window;
    const storage = new Map();
    globalThis.window = { sessionStorage: {
      getItem: key => storage.get(key) || null,
      setItem: (key, value) => storage.set(key, value),
      removeItem: key => storage.delete(key),
    } };
    let calls = 0;
    const keys = [];
    global.fetch = async (url, options) => {
      if (String(url).endsWith('/checkout-session')) return { ok: true, json: async () => ({ ready: true }) };
      keys.push(options.headers['Idempotency-Key']);
      calls += 1;
      if (calls === 1) throw new Error('Response lost');
      return { ok: true, json: async () => ({ id: 'SAMPLE-recovered' }) };
    };
    try {
      await assert.rejects(submitOrder({ customer_name: 'SAMPLE Reload Buyer', items: [] }), /Response lost/);
      const reloaded = await import(`../src/utils/api.js?checkout-reload=${Date.now()}`);
      assert.equal((await reloaded.recoverPendingOrder()).id, 'SAMPLE-recovered');
      assert.equal(keys[0], keys[1]);
      assert.equal(storage.size, 0);
    } finally {
      if (getPendingCheckoutAttempt()) await recoverPendingOrder();
      globalThis.window = oldWindow;
    }
  });

  it('submits order payload and returns created order response', async () => {
    const mockOrderResponse = {
      id: 'ord-12345',
      order_number: 'AZ-20261011-A1B2C3',
      customer_name: 'Zainab Ahmed',
      customer_phone: '03001234567',
      payment_method: 'bank_transfer',
      payment_status: 'pending',
      order_status: 'placed',
      total: {
        minor: 700000,
        formatted: 'PKR 7,000',
      },
      lines: [
        {
          id: 'line-1',
          variant_id: 101,
          product_title: 'Boxy Tee',
          quantity: 2,
          line_total: { minor: 700000, formatted: 'PKR 7,000' },
        },
      ],
      bank_instructions: {
        bank_name: 'Meezan Bank Ltd.',
        account_title: 'AlphaZee Private Limited',
        account_number: '01020304050607',
        iban: 'PK00MEZN0001020304050607',
      },
    };

    let calledUrl = '';
    let calledOptions = {};

    global.fetch = async (url, options) => {
      calledUrl = url;
      calledOptions = options;
      return {
        ok: true,
        json: async () => mockOrderResponse,
      };
    };

    const orderPayload = {
      customer_name: 'Zainab Ahmed',
      customer_phone: '0300-1234567',
      shipping_address_line1: 'Clifton Block 5',
      shipping_city: 'Karachi',
      shipping_province: 'Sindh',
      payment_method: 'bank_transfer',
      items: [{ variant_id: 101, quantity: 2 }],
    };

    const result = await submitOrder(orderPayload);

    assert.ok(calledUrl.endsWith('/api/v1/orders'));
    assert.equal(calledOptions.method, 'POST');
    assert.ok(calledOptions.headers['Idempotency-Key'], 'Expected Idempotency-Key header to be present');
    assert.equal(result.order_number, 'AZ-20261011-A1B2C3');
    assert.equal(result.total.formatted, 'PKR 7,000');
    assert.equal(result.bank_instructions.bank_name, 'Meezan Bank Ltd.');
  });

  it('handles 409 Insufficient Stock error from backend with detailed message', async () => {
    global.fetch = async () => ({
      ok: false,
      status: 409,
      statusText: 'Conflict',
      json: async () => ({ detail: 'Unable to place order: Insufficient stock for requested items.' }),
    });

    await assert.rejects(
      async () => {
        await submitOrder({
          customer_name: 'Ali Khan',
          customer_phone: '0300-9999999',
          shipping_address_line1: 'Street 1',
          shipping_city: 'Lahore',
          shipping_province: 'Punjab',
          payment_method: 'cod',
          items: [{ variant_id: 101, quantity: 99 }],
        });
      },
      (err) => {
        assert.ok(err instanceof ApiError);
        assert.equal(err.status, 409);
        assert.ok(err.message.includes('Insufficient stock'));
        return true;
      }
    );
  });

  it('uploads payment receipt screenshot for bank transfer order', async () => {
    let calledUrl = '';
    let calledBody = null;

    global.fetch = async (url, options) => {
      calledUrl = url;
      calledBody = JSON.parse(options.body);
      return {
        ok: true,
        json: async () => ({
          order_number: 'AZ-20261011-A1B2C3',
          receipts: [{ receipt_image_url: 'https://storage.alphazee.pk/receipts/proof.png' }],
        }),
      };
    };

    const receiptResult = await uploadReceipt('AZ-20261011-A1B2C3', {
      customer_phone: '0300-1234567',
      receipt_image_url: 'https://storage.alphazee.pk/receipts/proof.png',
      bank_reference: 'TXN-998877',
    });

    assert.ok(calledUrl.includes('/orders/AZ-20261011-A1B2C3/receipt'));
    assert.equal(calledBody.receipt_image_url, 'https://storage.alphazee.pk/receipts/proof.png');
    assert.equal(receiptResult.receipts.length, 1);
  });

  it('fetches order status with phone parameter', async () => {
    let calledUrl = '';

    global.fetch = async (url) => {
      calledUrl = url;
      return {
        ok: true,
        json: async () => ({
          order_number: 'AZ-20261011-A1B2C3',
          order_status: 'confirmed',
          payment_status: 'verified',
        }),
      };
    };

    const statusResult = await fetchOrderStatus('AZ-20261011-A1B2C3', '03001234567');
    assert.ok(calledUrl.includes('/orders/AZ-20261011-A1B2C3?phone=03001234567'));
    assert.equal(statusResult.order_status, 'confirmed');
    assert.equal(statusResult.payment_status, 'verified');
  });
});
