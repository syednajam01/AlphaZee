import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import {
  fetchAdminOverview,
  fetchAdminInventory,
  adjustAdminInventory,
  fetchAdminOrders,
  verifyOrderPayment,
  confirmSupplierAcceptance,
  reviewExpiredOrders,
  fetchPaymentInstructionsPreview,
  markPaymentInstructionsSent,
  resolvePaymentReview,
  deliverOrder,
  cancelOrder,
  initiateOrderRto,
  receiveOrderRto,
  inspectAndRestockRtoOrder,
  receiveAdminReturn,
  inspectAdminReturn,
  previewLegacyShipmentStock,
  reconcileLegacyShipmentStock,
  dispatchAdminOrder,
  updateAdminShipmentStatus,
  recordAdminCodRemittance,
  fetchAdminSuppliers,
  createAdminSupplier,
  assignSupplierVariant,
  fetchAdminProfitLoss,
  loginOwner,
  logoutOwner,
  fetchOwnerSession,
  removeLegacyAdminCredentials,
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

  it('uses cookies and in-memory CSRF, and removes the legacy shared key', async () => {
    const removed = [];
    const originalWindow = globalThis.window;
    globalThis.window = { sessionStorage: { removeItem: key => removed.push(key) } };
    removeLegacyAdminCredentials();
    globalThis.window = originalWindow;
    assert.ok(removed.includes('alphazee_admin_key'));
    let captured;
    global.fetch = async (url, options) => {
      captured = { url, options };
      return { ok: true, json: async () => ({ username: 'sample', csrf_token: 'sample-csrf' }) };
    };
    await loginOwner('sample', 'SAMPLE-password');
    assert.equal(captured.options.credentials, 'same-origin');
    assert.equal(captured.options.headers['X-Admin-Key'], undefined);
    await adjustAdminInventory({ quantity_delta: 1 });
    assert.equal(captured.options.headers['X-CSRF-Token'], 'sample-csrf');
    await logoutOwner();
    assert.ok(captured.url.endsWith('/auth/logout'));
    assert.equal(captured.options.headers['X-CSRF-Token'], 'sample-csrf');
    await fetchAdminOverview();
    assert.equal(captured.options.headers['X-Admin-Key'], undefined);
  });

  it('confirms supplier acceptance and flags expired bank orders for review', async () => {
    let confirmBody = null;
    let reviewCalled = false;

    global.fetch = async (url, options) => {
      if (url.includes('/confirm-supplier')) {
        confirmBody = JSON.parse(options.body);
        return {
          ok: true,
          json: async () => ({
            id: 'ord-101',
            order_status: 'confirmed',
            supplier_notes: confirmBody.notes,
          }),
        };
      }
      if (url.endsWith('/orders/review-expired')) {
        reviewCalled = true;
        return {
          ok: true,
          json: async () => ({
            review_count: 2,
            review_order_ids: ['ord-1', 'ord-2'],
          }),
        };
      }
      return { ok: true, json: async () => ({}) };
    };

    const confirmed = await confirmSupplierAcceptance('ord-101', 'All pieces packed');
    assert.equal(confirmed.order_status, 'confirmed');
    assert.equal(confirmBody.notes, 'All pieces packed');

    const reviewed = await reviewExpiredOrders();
    assert.equal(reviewCalled, true);
    assert.equal(reviewed.review_count, 2);
  });

  it('previews instructions and sends explicit handoff and review decisions', async () => {
    const requests = [];
    global.fetch = async (url, options = {}) => {
      requests.push({ url, options });
      return { ok: true, json: async () => ({ order_number: 'SAMPLE-1' }) };
    };
    await fetchPaymentInstructionsPreview('order-1');
    await markPaymentInstructionsSent('order-1', { channel: 'sms', reference: 'message-123' });
    await resolvePaymentReview('order-1', { resolution: 'release_unpaid', note: 'Funds checked' });
    assert.ok(requests[0].url.endsWith('/orders/order-1/payment-instructions-preview'));
    assert.deepEqual(JSON.parse(requests[1].options.body), {
      confirmed_sent: true, channel: 'sms', reference: 'message-123',
    });
    assert.deepEqual(JSON.parse(requests[2].options.body), {
      funds_checked: true, resolution: 'release_unpaid', note: 'Funds checked',
    });
  });

  it('handles two-step RTO return initiation and warehouse receipt confirmation', async () => {
    let capturedRtoBody = null;
    let rtoReceivedCalled = false;

    global.fetch = async (url, options) => {
      if (url.endsWith('/orders/ord-99/rto')) {
        capturedRtoBody = JSON.parse(options.body);
        return {
          ok: true,
          json: async () => ({
            id: 'ord-99',
            order_status: 'rto',
          }),
        };
      }
      if (url.endsWith('/orders/ord-99/rto-received')) {
        rtoReceivedCalled = true;
        return {
          ok: true,
          json: async () => ({
            id: 'ord-99',
            order_status: 'rto',
          }),
        };
      }
      return { ok: true, json: async () => ({}) };
    };

    const rtoRes = await initiateOrderRto('ord-99', {
      reason: 'Customer doorstep refusal',
      rto_courier_cost_minor: 15000,
    });
    assert.equal(rtoRes.order_status, 'rto');
    assert.equal(capturedRtoBody.reason, 'Customer doorstep refusal');
    assert.equal(capturedRtoBody.rto_courier_cost_minor, 15000);

    const receivedRes = await receiveOrderRto('ord-99', [{ order_line_id: 'line-1', received_quantity: 2 }]);
    assert.equal(rtoReceivedCalled, true);
    assert.equal(receivedRes.order_status, 'rto');
  });

  it('handles RTO condition inspection and restock payload', async () => {
    let capturedInspectBody = null;

    global.fetch = async (url, options) => {
      if (url.endsWith('/orders/ord-99/rto-inspect')) {
        capturedInspectBody = JSON.parse(options.body);
        return {
          ok: true,
          json: async () => ({
            id: 'ord-99',
            order_status: 'rto',
          }),
        };
      }
      return { ok: true, json: async () => ({}) };
    };

    const res = await inspectAndRestockRtoOrder('ord-99', {
      lines: [{ order_line_id: 'line-1', sellable_quantity: 1, damaged_quantity: 1 }],
      notes: 'Physical condition verified pristine',
    });
    assert.equal(res.order_status, 'rto');
    assert.deepEqual(capturedInspectBody.lines, [{ order_line_id: 'line-1', sellable_quantity: 1, damaged_quantity: 1 }]);
    assert.equal(capturedInspectBody.notes, 'Physical condition verified pristine');
  });

  it('sends exact customer-return quantities and explicit legacy decisions', async () => {
    const calls = [];
    global.fetch = async (url, options = {}) => {
      calls.push({ url, options });
      return { ok: true, json: async () => ({ lines: [] }) };
    };
    await receiveAdminReturn('ret-1', 2);
    await inspectAdminReturn('ret-1', { sellable_quantity: 1, damaged_quantity: 1, notes: 'Torn' });
    await previewLegacyShipmentStock('ship-1');
    await reconcileLegacyShipmentStock('ship-1', { lines: [{ reservation_id: 'res-1', physical_deducted: true }], note: 'Ledger checked' });
    assert.deepEqual(JSON.parse(calls[0].options.body), { received_quantity: 2 });
    assert.deepEqual(JSON.parse(calls[1].options.body), { sellable_quantity: 1, damaged_quantity: 1, notes: 'Torn' });
    assert.ok(calls[2].url.endsWith('/shipments/ship-1/stock-reconciliation'));
    assert.equal(JSON.parse(calls[3].options.body).lines[0].physical_deducted, true);
  });
});



