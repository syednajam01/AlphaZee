import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import {
  fetchAdminOverview,
  fetchAdminInventory,
  adjustAdminInventory,
  fetchAdminOrders,
  verifyOrderPayment,
  deliverOrder,
  cancelOrder,
  dispatchAdminOrder,
  updateAdminShipmentStatus,
  recordAdminCodRemittance,
  fetchAdminSuppliers,
  createAdminSupplier,
  assignSupplierVariant,
  fetchAdminProfitLoss,
} from '../src/utils/api.js';

describe('Admin API Client Methods', () => {
  let originalFetch;

  beforeEach(() => {
    originalFetch = global.fetch;
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('fetches admin overview metrics', async () => {
    global.fetch = async (url) => {
      assert.ok(url.endsWith('/api/v1/admin/overview'));
      return {
        ok: true,
        json: async () => ({
          gross_revenue_minor: 6480000,
          formatted_gross_revenue: 'PKR 64,800',
          total_orders: 12,
          pending_orders: 3,
          confirmed_orders: 5,
          delivered_orders: 4,
          total_skus: 8,
          low_stock_skus: 1,
        }),
      };
    };

    const overview = await fetchAdminOverview();
    assert.equal(overview.total_orders, 12);
    assert.equal(overview.formatted_gross_revenue, 'PKR 64,800');
    assert.equal(overview.low_stock_skus, 1);
  });

  it('adjusts physical inventory with optimistic concurrency payload', async () => {
    let calledOptions = {};

    global.fetch = async (url, options) => {
      assert.ok(url.endsWith('/api/v1/admin/inventory/adjust'));
      calledOptions = options;
      return {
        ok: true,
        json: async () => ({
          supplier_variant_id: 'sv-123',
          physical_on_hand: 15,
          available_to_sell: 15,
          version: 2,
        }),
      };
    };

    const res = await adjustAdminInventory({
      supplier_variant_id: 'sv-123',
      quantity_delta: 5,
      expected_version: 1,
      reason: 'supplier_receipt',
      reference_id: 'PO-001',
    });

    assert.equal(calledOptions.method, 'POST');
    assert.equal(res.physical_on_hand, 15);
    assert.equal(res.version, 2);
  });

  it('handles supplier creation and variant cost assignment', async () => {
    let createBody = null;
    let assignBody = null;

    global.fetch = async (url, options) => {
      if (url.endsWith('/api/v1/admin/suppliers')) {
        createBody = JSON.parse(options.body);
        return {
          ok: true,
          json: async () => ({
            id: 'sup-999',
            name: createBody.name,
            slug: createBody.slug,
            status: 'active',
          }),
        };
      }
      if (url.includes('/variants')) {
        assignBody = JSON.parse(options.body);
        return {
          ok: true,
          json: async () => ({
            id: 'sv-link-1',
            supplier_id: 'sup-999',
            variant_id: assignBody.variant_id,
            supplier_cost_minor: assignBody.supplier_cost_minor,
            active: true,
          }),
        };
      }
      return { ok: true, json: async () => ({}) };
    };

    const sup = await createAdminSupplier({
      name: 'Lahore Fabrics',
      slug: 'lahore-fabrics',
      status: 'active',
    });
    assert.equal(sup.name, 'Lahore Fabrics');

    const sv = await assignSupplierVariant('sup-999', {
      variant_id: 101,
      supplier_cost_minor: 180000,
      active: true,
    });
    assert.equal(sv.supplier_cost_minor, 180000);
    assert.equal(sv.active, true);
  });

  it('handles courier dispatch, status update, and COD remittance', async () => {
    let capturedDispath = null;
    let capturedStatus = null;
    let capturedRemittance = null;

    global.fetch = async (url, options) => {
      if (url.includes('/dispatch')) {
        capturedDispath = JSON.parse(options.body);
        return {
          ok: true,
          json: async () => ({
            id: 'ship-101',
            order_id: 'ord-101',
            courier_code: capturedDispath.courier_code,
            tracking_number: capturedDispath.tracking_number,
            status: 'dispatched',
          }),
        };
      }
      if (url.includes('/status')) {
        capturedStatus = JSON.parse(options.body);
        return {
          ok: true,
          json: async () => ({
            id: 'ship-101',
            status: capturedStatus.status,
            rto_reason: capturedStatus.rto_reason,
          }),
        };
      }
      if (url.includes('/remittance')) {
        capturedRemittance = JSON.parse(options.body);
        return {
          ok: true,
          json: async () => ({
            id: 'ship-101',
            cod_remitted_amount_minor: capturedRemittance.remitted_amount_minor,
            cod_remittance_status: 'remitted',
            cod_remittance_reference: capturedRemittance.reference,
          }),
        };
      }
      if (url.endsWith('/analytics/profit-loss')) {
        return {
          ok: true,
          json: async () => ({
            gross_revenue_minor: 3500000,
            formatted_gross_revenue: 'PKR 35,000',
            cogs_minor: 2000000,
            formatted_cogs: 'PKR 20,000',
            total_courier_expenses_minor: 300000,
            formatted_courier_expenses: 'PKR 3,000',
            gross_profit_minor: 1200000,
            formatted_gross_profit: 'PKR 12,000',
            gross_margin_percent: 34.29,
            total_shipments_count: 10,
            rto_rate_percent: 10.0,
          }),
        };
      }
      return { ok: true, json: async () => ({}) };
    };

    // 1. Dispatch
    const ship = await dispatchAdminOrder('ord-101', {
      courier_code: 'trax',
      tracking_number: 'TRX-123',
      shipping_cost_minor: 25000,
    });
    assert.equal(ship.courier_code, 'trax');
    assert.equal(ship.status, 'dispatched');

    // 2. Status update
    const updatedShip = await updateAdminShipmentStatus('ship-101', {
      status: 'rto_delivered',
      rto_reason: 'Refused by customer',
      rto_courier_cost_minor: 15000,
    });
    assert.equal(updatedShip.status, 'rto_delivered');
    assert.equal(updatedShip.rto_reason, 'Refused by customer');

    // 3. COD remittance
    const remitted = await recordAdminCodRemittance('ship-101', {
      remitted_amount_minor: 350000,
      reference: 'TRAX-OCT11',
    });
    assert.equal(remitted.cod_remittance_status, 'remitted');
    assert.equal(remitted.cod_remittance_reference, 'TRAX-OCT11');

    // 4. Profit and Loss report
    const pnl = await fetchAdminProfitLoss();
    assert.equal(pnl.gross_revenue_minor, 3500000);
    assert.equal(pnl.formatted_gross_profit, 'PKR 12,000');
    assert.equal(pnl.rto_rate_percent, 10.0);
  });
});
