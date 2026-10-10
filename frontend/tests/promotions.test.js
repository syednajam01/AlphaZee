import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import {
  validateCoupon,
  requestOrderReturn,
  fetchAdminCoupons,
  createAdminCoupon,
  deleteAdminCoupon,
  fetchAdminReturns,
  approveAdminReturn,
  completeAdminReturn,
  fetchAdminMarketingAnalytics,
} from '../src/utils/api.js';
import { captureLandingUtmParams, getStoredUtmParams } from '../src/utils/utm.js';

describe('Promotions, UTM Marketing Attribution & Returns Tests', () => {
  let originalFetch;
  let originalWindow;
  let originalSessionStorage;

  beforeEach(() => {
    originalFetch = global.fetch;
    originalWindow = global.window;
    originalSessionStorage = global.sessionStorage;
  });

  afterEach(() => {
    global.fetch = originalFetch;
    global.window = originalWindow;
    global.sessionStorage = originalSessionStorage;
  });

  it('validates coupon code via storefront API client', async () => {
    let calledUrl = '';
    let calledBody = null;

    global.fetch = async (url, options) => {
      calledUrl = url;
      calledBody = JSON.parse(options.body);
      return {
        ok: true,
        json: async () => ({
          valid: true,
          code: 'EID20',
          discount_type: 'percentage',
          discount_value: 20,
          discount_amount: { minor: 40000, formatted: 'PKR 400' },
          is_free_shipping: false,
          message: 'Coupon successfully applied.',
        }),
      };
    };

    const res = await validateCoupon('eid20', 200000, 0);

    assert.ok(calledUrl.endsWith('/api/v1/coupons/validate'));
    assert.equal(calledBody.code, 'eid20');
    assert.equal(calledBody.subtotal_minor, 200000);
    assert.equal(res.valid, true);
    assert.equal(res.discount_amount.minor, 40000);
  });

  it('submits customer return request via storefront API client', async () => {
    let calledUrl = '';
    let calledBody = null;

    global.fetch = async (url, options) => {
      calledUrl = url;
      calledBody = JSON.parse(options.body);
      return {
        ok: true,
        json: async () => ({
          id: 'ret-12345',
          status: 'requested',
          return_type: 'size_exchange',
          reason: 'size_too_small',
        }),
      };
    };

    const payload = {
      order_id: 'ord-111',
      order_line_id: 'line-222',
      return_type: 'size_exchange',
      reason: 'size_too_small',
      customer_notes: 'Need Size L',
    };

    const res = await requestOrderReturn(payload);

    assert.ok(calledUrl.endsWith('/api/v1/returns/request'));
    assert.equal(calledBody.return_type, 'size_exchange');
    assert.equal(res.status, 'requested');
  });

  it('handles admin coupon CRUD requests', async () => {
    let callHistory = [];

    global.fetch = async (url, options = {}) => {
      callHistory.push({ url, method: options.method || 'GET' });
      if (options.method === 'POST') {
        return {
          ok: true,
          json: async () => ({ id: 'cpn-1', code: 'FLASH50', discount_type: 'percentage' }),
        };
      }
      if (options.method === 'DELETE') {
        return { ok: true, json: async () => ({}) };
      }
      return {
        ok: true,
        json: async () => [{ id: 'cpn-1', code: 'FLASH50' }],
      };
    };

    const list = await fetchAdminCoupons();
    assert.equal(list.length, 1);
    assert.equal(callHistory[0].method, 'GET');

    const created = await createAdminCoupon({ code: 'FLASH50', discount_type: 'percentage', discount_value: 50 });
    assert.equal(created.code, 'FLASH50');
    assert.equal(callHistory[1].method, 'POST');

    await deleteAdminCoupon('cpn-1');
    assert.equal(callHistory[2].method, 'DELETE');
  });

  it('handles admin return approval and completion API methods', async () => {
    let callHistory = [];

    global.fetch = async (url, options = {}) => {
      callHistory.push({ url, method: options.method || 'GET', body: options.body });
      return {
        ok: true,
        json: async () => ({ id: 'ret-1', status: 'completed' }),
      };
    };

    await approveAdminReturn('ret-1');
    assert.ok(callHistory[0].url.includes('/admin/returns/ret-1/approve'));

    await completeAdminReturn('ret-1', { refund_reference: 'REF-1234', should_restock: true });
    assert.ok(callHistory[1].url.includes('/admin/returns/ret-1/complete'));
  });

  it('fetches marketing attribution analytics', async () => {
    global.fetch = async (url) => {
      return {
        ok: true,
        json: async () => ({
          total_campaigns: 1,
          channels: [
            {
              utm_source: 'tiktok',
              utm_medium: 'spark_ad',
              utm_campaign: 'winter_launch',
              orders_count: 5,
              revenue_minor: 1500000,
              formatted_revenue: 'PKR 15,000',
              discount_minor: 150000,
              formatted_discount: 'PKR 1,500',
            },
          ],
        }),
      };
    };

    const res = await fetchAdminMarketingAnalytics();
    assert.equal(res.total_campaigns, 1);
    assert.equal(res.channels[0].utm_source, 'tiktok');
    assert.equal(res.channels[0].orders_count, 5);
  });

  it('captures and retrieves UTM parameters from storage', () => {
    let store = {};
    global.sessionStorage = {
      getItem: (key) => store[key] || null,
      setItem: (key, val) => { store[key] = String(val); },
      clear: () => { store = {}; },
    };

    global.window = {
      location: {
        search: '?utm_source=instagram&utm_medium=reels&utm_campaign=summer_vibes',
      },
    };

    captureLandingUtmParams();

    const utm = getStoredUtmParams();
    assert.equal(utm.utm_source, 'instagram');
    assert.equal(utm.utm_medium, 'reels');
    assert.equal(utm.utm_campaign, 'summer_vibes');
  });
});
