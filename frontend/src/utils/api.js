/**
 * Central API client for AlphaZee frontend storefront.
 *
 * Uses same-origin /api/v1 requests proxied through Vite in development,
 * or configurable VITE_API_BASE.
 */

const API_BASE = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE) || '/api/v1';

export class ApiError extends Error {
  constructor(message, status = 0, data = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  try {
    const res = await fetch(url, {
      headers: {
        'Accept': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!res.ok) {
      let errorData = null;
      try {
        errorData = await res.json();
      } catch {
        // Response was not JSON
      }
      const message = errorData?.detail || `API request failed: ${res.status} ${res.statusText}`;
      throw new ApiError(message, res.status, errorData);
    }

    return await res.json();
  } catch (err) {
    if (err instanceof ApiError) throw err;
    throw new ApiError(err.message || 'Network error while contacting store backend', 0);
  }
}

/**
 * Fetch all active collections ordered by display_order.
 * @returns {Promise<{ collections: Array, total: number }>}
 */
export async function fetchCollections() {
  return request('/collections');
}

/**
 * Fetch paginated active products, optionally filtered by collection.
 * @param {Object} params
 * @param {string|null} [params.collectionId]
 * @param {number} [params.page=1]
 * @param {number} [params.pageSize=20]
 * @param {AbortSignal|null} [params.signal]
 * @returns {Promise<{ products: Array, total: number, page: number, page_size: number, collection_id: string|null }>}
 */
export async function fetchProducts({ collectionId = null, page = 1, pageSize = 20, signal = null } = {}) {
  const query = new URLSearchParams();
  if (collectionId && collectionId !== 'all') {
    query.set('collection_id', collectionId);
  }
  query.set('page', String(page));
  query.set('page_size', String(pageSize));
  return request(`/products?${query.toString()}`, { signal: signal || undefined });
}

/**
 * Fetch active products featured in the hero carousel.
 * @returns {Promise<Array>}
 */
export async function fetchHeroProducts({ signal = null } = {}) {
  return request('/products/hero', { signal: signal || undefined });
}

/**
 * Fetch product detail by slug with variants.
 * @param {string} slug
 * @param {Object} [options]
 * @param {AbortSignal|null} [options.signal]
 * @returns {Promise<Object>}
 */
export async function fetchProductBySlug(slug, { signal = null } = {}) {
  return request(`/products/${encodeURIComponent(slug)}`, { signal: signal || undefined });
}

/**
 * Submit customer checkout order to backend.
 * @param {Object} orderData
 * @returns {Promise<Object>} Created order details
 */
export async function submitOrder(orderData) {
  return request('/orders', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(orderData),
  });
}

/**
 * Upload bank transfer receipt proof.
 * @param {string} orderNumber
 * @param {Object} receiptData
 * @returns {Promise<Object>} Updated order details
 */
export async function uploadReceipt(orderNumber, receiptData) {
  return request(`/orders/${encodeURIComponent(orderNumber)}/receipt`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(receiptData),
  });
}

/**
 * Track order status with phone verification.
 * @param {string} orderNumber
 * @param {string} phone
 * @returns {Promise<Object>} Order details
 */
export async function fetchOrderStatus(orderNumber, phone) {
  const query = new URLSearchParams({ phone });
  return request(`/orders/${encodeURIComponent(orderNumber)}?${query.toString()}`);
}

/**
 * Fetch high-level admin dashboard overview metrics.
 * @returns {Promise<Object>}
 */
export async function fetchAdminOverview() {
  return request('/admin/overview');
}

/**
 * Fetch real-time inventory metrics across all active supplier variants.
 * @returns {Promise<{ items: Array, total_variants: number }>}
 */
export async function fetchAdminInventory() {
  return request('/admin/inventory/summary');
}

/**
 * Adjust physical stock with optimistic concurrency guard.
 * @param {Object} payload { supplier_variant_id, quantity_delta, expected_version, reason, reference_id }
 * @returns {Promise<Object>}
 */
export async function adjustAdminInventory(payload) {
  return request('/admin/inventory/adjust', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

/**
 * Fetch paginated admin orders with optional status filter.
 * @param {Object} [params]
 * @param {string|null} [params.status]
 * @param {number} [params.page=1]
 * @param {number} [params.pageSize=20]
 * @returns {Promise<{ orders: Array, total: number, page: number, page_size: number }>}
 */
export async function fetchAdminOrders({ status = null, page = 1, pageSize = 20 } = {}) {
  const query = new URLSearchParams();
  if (status && status !== 'all') query.set('order_status', status);
  query.set('page', String(page));
  query.set('page_size', String(pageSize));
  return request(`/admin/orders?${query.toString()}`);
}

/**
 * Owner verifies received bank transfer funds.
 * @param {string} orderId
 * @param {string|null} [receiptId]
 * @returns {Promise<Object>} Updated order details
 */
export async function verifyOrderPayment(orderId, receiptId = null) {
  const query = receiptId ? `?receipt_id=${encodeURIComponent(receiptId)}` : '';
  return request(`/admin/orders/${encodeURIComponent(orderId)}/verify-payment${query}`, {
    method: 'POST',
  });
}

/**
 * Mark order as delivered.
 * @param {string} orderId
 * @returns {Promise<Object>} Updated order details
 */
export async function deliverOrder(orderId) {
  return request(`/admin/orders/${encodeURIComponent(orderId)}/deliver`, {
    method: 'POST',
  });
}

/**
 * Cancel order and release held reservations.
 * @param {string} orderId
 * @returns {Promise<Object>} Updated order details
 */
export async function cancelOrder(orderId) {
  return request(`/admin/orders/${encodeURIComponent(orderId)}/cancel`, {
    method: 'POST',
  });
}

/**
 * Fetch all registered suppliers.
 * @returns {Promise<{ suppliers: Array, total: number }>}
 */
export async function fetchAdminSuppliers() {
  return request('/admin/suppliers');
}

/**
 * Register a new supplier.
 * @param {Object} supplierData { name, slug, status, notes }
 * @returns {Promise<Object>}
 */
export async function createAdminSupplier(supplierData) {
  return request('/admin/suppliers', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(supplierData),
  });
}

/**
 * Assign a catalog variant to a supplier.
 * @param {string} supplierId
 * @param {Object} payload { variant_id, supplier_cost_minor, active }
 * @returns {Promise<Object>}
 */
export async function assignSupplierVariant(supplierId, payload) {
  return request(`/admin/suppliers/${encodeURIComponent(supplierId)}/variants`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

/**
 * Dispatch an order with courier tracking information.
 * @param {string} orderId
 * @param {Object} payload { courier_code, tracking_number, shipping_cost_minor, tracking_url }
 * @returns {Promise<Object>} Created shipment
 */
export async function dispatchAdminOrder(orderId, payload) {
  return request(`/admin/orders/${encodeURIComponent(orderId)}/dispatch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

/**
 * Update delivery status for a courier shipment.
 * @param {string} shipmentId
 * @param {Object} payload { status, rto_reason, rto_courier_cost_minor }
 * @returns {Promise<Object>} Updated shipment
 */
export async function updateAdminShipmentStatus(shipmentId, payload) {
  return request(`/admin/shipments/${encodeURIComponent(shipmentId)}/status`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

/**
 * Record courier COD cash remittance into bank account.
 * @param {string} shipmentId
 * @param {Object} payload { remitted_amount_minor, reference }
 * @returns {Promise<Object>} Updated shipment
 */
export async function recordAdminCodRemittance(shipmentId, payload) {
  return request(`/admin/shipments/${encodeURIComponent(shipmentId)}/remittance`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

/**
 * Fetch owner gross profit, COGS, courier expenses, and unit economics report.
 * @returns {Promise<Object>}
 */
export async function fetchAdminProfitLoss() {
  return request('/admin/analytics/profit-loss');
}

/**
 * Validate coupon code against subtotal in storefront checkout.
 * @param {string} code
 * @param {number} subtotalMinor
 * @param {number} [shippingFeeMinor=0]
 * @returns {Promise<Object>}
 */
export async function validateCoupon(code, subtotalMinor, shippingFeeMinor = 0) {
  return request('/coupons/validate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      code,
      subtotal_minor: subtotalMinor,
      shipping_fee_minor: shippingFeeMinor,
    }),
  });
}

/**
 * Submit customer return or size exchange request.
 * @param {Object} payload { order_id, order_line_id, return_type, reason, customer_notes, exchange_variant_id }
 * @returns {Promise<Object>}
 */
export async function requestOrderReturn(payload) {
  return request('/returns/request', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

/**
 * Fetch all promotional coupons for admin management.
 * @param {boolean} [activeOnly=false]
 * @returns {Promise<Array>}
 */
export async function fetchAdminCoupons(activeOnly = false) {
  const query = activeOnly ? '?active_only=true' : '';
  return request(`/admin/coupons${query}`);
}

/**
 * Create a new promotional discount coupon.
 * @param {Object} payload
 * @returns {Promise<Object>}
 */
export async function createAdminCoupon(payload) {
  return request('/admin/coupons', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

/**
 * Delete a coupon by ID.
 * @param {string} couponId
 * @returns {Promise<void>}
 */
export async function deleteAdminCoupon(couponId) {
  return request(`/admin/coupons/${encodeURIComponent(couponId)}`, {
    method: 'DELETE',
  });
}

/**
 * List customer return requests.
 * @param {Object} [filters] { orderId, status }
 * @returns {Promise<Array>}
 */
export async function fetchAdminReturns(filters = {}) {
  const params = new URLSearchParams();
  if (filters.orderId) params.set('order_id', filters.orderId);
  if (filters.status) params.set('status', filters.status);
  const qs = params.toString() ? `?${params.toString()}` : '';
  return request(`/admin/returns${qs}`);
}

/**
 * Approve a return request.
 * @param {string} returnId
 * @param {Object} [payload] { refund_amount_minor }
 * @returns {Promise<Object>}
 */
export async function approveAdminReturn(returnId, payload = {}) {
  return request(`/admin/returns/${encodeURIComponent(returnId)}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

/**
 * Complete a return request, record bank refund ref, and restock inventory.
 * @param {string} returnId
 * @param {Object} payload { refund_reference, should_restock }
 * @returns {Promise<Object>}
 */
export async function completeAdminReturn(returnId, payload = {}) {
  return request(`/admin/returns/${encodeURIComponent(returnId)}/complete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

/**
 * Reject a customer return request.
 * @param {string} returnId
 * @returns {Promise<Object>}
 */
export async function rejectAdminReturn(returnId) {
  return request(`/admin/returns/${encodeURIComponent(returnId)}/reject`, {
    method: 'POST',
  });
}

/**
 * Fetch marketing UTM campaign performance attribution summary.
 * @returns {Promise<Object>}
 */
export async function fetchAdminMarketingAnalytics() {
  return request('/admin/analytics/marketing');
}




