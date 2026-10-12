import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { cart } from '../src/utils/cart.js';
import { submitOrder, uploadReceipt, fetchOrderStatus, ApiError } from '../src/utils/api.js';

describe('Storefront Order API Client & Checkout Cart State', () => {
  let originalFetch;

  beforeEach(() => {
    cart.clear();
    originalFetch = global.fetch;
  });

  afterEach(() => {
    global.fetch = originalFetch;
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
