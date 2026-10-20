/**
 * Central API client for AlphaZee frontend storefront.
 *
 * Uses same-origin /api/v1 requests proxied through Vite in development,
 * or configurable VITE_API_BASE.
 */

const API_BASE = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE) || '/api/v1';
let ownerCsrfToken = null;
const ownerExpiryListeners = new Set();
let vendorCsrfToken = null;
const vendorExpiryListeners = new Set();

export function removeLegacyAdminCredentials() {
  if (typeof window === 'undefined') return;
  for (const name of ['sessionStorage', 'localStorage']) {
    try { window[name]?.removeItem('alphazee_admin_key'); } catch {}
  }
}
removeLegacyAdminCredentials();

export function onOwnerSessionExpired(listener) {
  ownerExpiryListeners.add(listener);
  return () => ownerExpiryListeners.delete(listener);
}

function forgetOwnerSession() {
  const hadSession = ownerCsrfToken !== null;
  ownerCsrfToken = null;
  if (hadSession) ownerExpiryListeners.forEach(listener => listener());
}

export function onVendorSessionExpired(listener) {
  vendorExpiryListeners.add(listener);
  return () => vendorExpiryListeners.delete(listener);
}

function forgetVendorSession() {
  const hadSession = vendorCsrfToken !== null;
  vendorCsrfToken = null;
  if (hadSession) vendorExpiryListeners.forEach(listener => listener());
}

export async function loginOwner(username, password) {
  const session = await request('/auth/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  ownerCsrfToken = session.csrf_token;
  return session;
}

export async function fetchOwnerSession() {
  const session = await request('/auth/session', { cache: 'no-store' });
  ownerCsrfToken = session.csrf_token;
  return session;
}

export async function logoutOwner() {
  await request('/auth/logout', { method: 'POST' });
  forgetOwnerSession();
}

export async function loginVendor(username, password) {
  const session = await request('/vendor/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  vendorCsrfToken = session.csrf_token;
  return session;
}

export async function fetchVendorSession() {
  const session = await request('/vendor/auth/me', { cache: 'no-store' });
  vendorCsrfToken = session.csrf_token;
  return session;
}

export async function logoutVendor() {
  try {
    await request('/vendor/auth/logout', { method: 'POST' });
  } finally {
    forgetVendorSession();
  }
}

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
  const headers = {
    'Accept': 'application/json',
    ...(typeof options.body === 'string' ? {'Content-Type':'application/json'} : {}),
    ...options.headers,
  };

  const method = (options.method || 'GET').toUpperCase();
  if ((endpoint.startsWith('/admin') || endpoint === '/auth/logout')
      && !['GET', 'HEAD', 'OPTIONS'].includes(method) && ownerCsrfToken) {
    headers['X-CSRF-Token'] = ownerCsrfToken;
  }
  if ((endpoint.startsWith('/vendor') && endpoint !== '/vendor/auth/login')
      && !['GET', 'HEAD', 'OPTIONS'].includes(method) && vendorCsrfToken) {
    headers['X-CSRF-Token'] = vendorCsrfToken;
  }

  try {
    const res = await fetch(url, {
      ...options,
      credentials: 'same-origin',
      headers,
    });

    if (!res.ok) {
      if (res.status === 401) {
        if (endpoint.startsWith('/admin') || endpoint === '/auth/session' || endpoint === '/auth/logout') {
          forgetOwnerSession();
        } else if (endpoint.startsWith('/vendor')) {
          forgetVendorSession();
        }
      }
      let errorData = null;
      try {
        errorData = await res.json();
      } catch {
        // Response was not JSON
      }
      const detail = errorData?.detail;
      const message = typeof detail === 'string' ? detail : detail?.message || `API request failed: ${res.status} ${res.statusText}`;
      throw new ApiError(message, res.status, errorData);
    }

    const data = res.status === 204 ? null : await res.json();
    if (!['GET','HEAD','OPTIONS'].includes(method) && /^\/admin\/(products|collections|media|suppliers|inventory)(\/|$)/.test(endpoint)) {
      try { window.localStorage?.setItem('alphazee_catalog_changed', `${Date.now()}-${Math.random()}`); } catch {}
      if (typeof window !== 'undefined') window.dispatchEvent?.(new Event('alphazee:catalog-change'));
    }
    return data;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    throw new ApiError(err.message || 'Network error while contacting store backend', 0);
  }
}

// Owner catalog contracts used by the M4 authoring screens. All writes inherit
// same-origin cookies/CSRF from the central request client.
export function fetchOwnerProducts(params = {}) {
  const query = new URLSearchParams(Object.entries(params).filter(([, value]) => value !== null && value !== ''));
  return request(`/admin/products?${query}`);
}
export function fetchOwnerProduct(id) { return request(`/admin/products/${encodeURIComponent(id)}`); }
export function createOwnerProduct(payload = {}) { return ownerCatalogWrite('/admin/products', payload); }
export function updateOwnerProduct(id, payload) { return ownerCatalogWrite(`/admin/products/${encodeURIComponent(id)}`, payload); }
export function transitionOwnerProduct(id, action, version) {
  if (!['publish', 'unpublish', 'archive', 'restore'].includes(action)) throw new Error('Unknown product action');
  return ownerCatalogWrite(`/admin/products/${encodeURIComponent(id)}/${action}`, { expected_version: version });
}
export function fetchOwnerCollections() { return request('/admin/collections'); }
export function fetchVariantStock(id) { return request(`/admin/catalog/variants/${encodeURIComponent(id)}/stock`); }
export function fetchStockHolds(id, params = {}) { return request(`/admin/inventory/${encodeURIComponent(id)}/holds?${new URLSearchParams(params)}`); }
export function createOwnerCollection(payload) { return ownerCatalogWrite('/admin/collections', payload); }
export function updateOwnerCollection(id, payload) { return ownerCatalogWrite(`/admin/collections/${encodeURIComponent(id)}`, payload); }
export function reorderOwnerCollections(items) { return ownerCatalogWrite('/admin/collections/reorder', { items }); }
function ownerCatalogWrite(path, payload) {
  return request(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
}

export function fetchOwnerMedia(params = {}) {
  return request(`/admin/media?${new URLSearchParams(params)}`);
}
export function fetchOwnerMediaAsset(id) { return request(`/admin/media/${encodeURIComponent(id)}`); }
export function saveProductMedia(id, payload) { return ownerCatalogWrite(`/admin/media/products/${encodeURIComponent(id)}`, payload); }
export function attachProductMedia(id, payload) { return ownerCatalogWrite(`/admin/media/products/${encodeURIComponent(id)}/attach`, payload); }
export function detachProductMedia(id, payload) { return ownerCatalogWrite(`/admin/media/products/${encodeURIComponent(id)}/detach`, payload); }
export function reorderProductMedia(id, payload) { return ownerCatalogWrite(`/admin/media/products/${encodeURIComponent(id)}/reorder`, payload); }
export function setProductRoles(id, payload) { return ownerCatalogWrite(`/admin/media/products/${encodeURIComponent(id)}/roles`, payload); }
export function saveCollectionMedia(id, payload) { return ownerCatalogWrite(`/admin/media/collections/${encodeURIComponent(id)}`, payload); }
export function saveMediaPoster(id, payload) { return ownerCatalogWrite(`/admin/media/${encodeURIComponent(id)}/poster`, payload); }
export function deleteOwnerMedia(id, expectedVersion) { return ownerCatalogWrite(`/admin/media/${encodeURIComponent(id)}/delete`, { expected_version: expectedVersion }); }

export function fetchHeroSlides({ signal = null } = {}) {
  return request('/hero/slides', { cache: 'no-store', signal: signal || undefined });
}
export function fetchAdminHeroSlides() { return request('/admin/media/hero/slides'); }
export function createAdminHeroSlide(payload) { return ownerCatalogWrite('/admin/media/hero/slides', payload); }
export function updateAdminHeroSlide(id, payload) { return ownerCatalogWrite(`/admin/media/hero/slides/${encodeURIComponent(id)}`, payload); }
export function reorderAdminHeroSlides(payload) { return ownerCatalogWrite('/admin/media/hero/slides/reorder', payload); }
export function deleteAdminHeroSlide(id, expectedVersion) { return ownerCatalogWrite(`/admin/media/hero/slides/${encodeURIComponent(id)}/delete`, { expected_version: expectedVersion }); }

// Let the browser set multipart boundaries; transport completion still awaits server acceptance.
export function uploadOwnerMedia(file, { signal, onProgress } = {}) {
  const body = new FormData();
  body.append('file', file);
  if (onProgress) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const abort = () => xhr.abort();
      const finish = () => signal?.removeEventListener('abort', abort);
      xhr.open('POST', `${API_BASE}/admin/media`);
      xhr.setRequestHeader('Accept', 'application/json');
      if (ownerCsrfToken) xhr.setRequestHeader('X-CSRF-Token', ownerCsrfToken);
      xhr.upload.onprogress = event => {
        if (event.lengthComputable) onProgress(Math.min(100, Math.round(event.loaded / event.total * 100)));
      };
      xhr.onload = () => {
        finish();
        let data;
        try { data = JSON.parse(xhr.responseText); } catch { data = null; }
        if (xhr.status >= 200 && xhr.status < 300 && data?.id) resolve(data);
        else {
          if (xhr.status === 401) forgetOwnerSession();
          const detail = data?.detail;
          reject(new ApiError(typeof detail === 'string' ? detail : detail?.message || 'Upload could not be accepted', xhr.status, data));
        }
      };
      xhr.onerror = () => { finish(); reject(new ApiError('Upload connection failed. Check the library before retrying.', 0)); };
      xhr.onabort = () => { finish(); const error = new Error('Upload canceled. Check the library before retrying.'); error.name = 'AbortError'; reject(error); };
      if (signal?.aborted) { const error = new Error('Upload canceled'); error.name = 'AbortError'; reject(error); return; }
      signal?.addEventListener('abort', abort, { once: true });
      xhr.send(body);
    });
  }
  return request('/admin/media', { method: 'POST', body, signal });
}

/**
 * Fetch all active collections ordered by display_order.
 * @returns {Promise<{ collections: Array, total: number }>}
 */
export async function fetchCollections() {
  return request('/collections', { cache: 'no-store' });
}

export async function fetchStorefrontCapabilities() {
  return request('/storefront/capabilities', { cache: 'no-store' });
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
  return request(`/products?${query.toString()}`, { cache: 'no-store', signal: signal || undefined });
}

/**
 * Fetch active products featured in the hero carousel.
 * @returns {Promise<Array>}
 */
export async function fetchHeroProducts({ signal = null } = {}) {
  return request('/products/hero', { cache: 'no-store', signal: signal || undefined });
}

/**
 * Fetch product detail by slug with variants.
 * @param {string} slug
 * @param {Object} [options]
 * @param {AbortSignal|null} [options.signal]
 * @returns {Promise<Object>}
 */
export async function fetchProductBySlug(slug, { signal = null } = {}) {
  return request(`/products/${encodeURIComponent(slug)}`, { cache: 'no-store', signal: signal || undefined });
}

export function fetchProductById(id, { signal = null } = {}) {
  return request(`/catalog/products/${encodeURIComponent(id)}`, { cache: 'no-store', signal: signal || undefined });
}

/**
 * Submit customer checkout order to backend.
 * Automatically attaches an Idempotency-Key to prevent duplicate order placement.
 * @param {Object} orderData
 * @param {string|null} [idempotencyKey=null]
 * @returns {Promise<Object>} Created order details
 */
export async function submitOrder(orderData, idempotencyKey = null) {
  const pending = getPendingCheckoutAttempt();
  const body = JSON.stringify(orderData);
  if (pending && JSON.stringify(pending.payload) !== body) {
    throw new ApiError('A previous checkout may have succeeded. Retry that submission before changing the order.', 409);
  }
  const effectiveIdemp = pending?.key || idempotencyKey || orderData.idempotency_key || newCheckoutKey();
  const attempt = pending || { key: effectiveIdemp, payload: orderData };
  // The cookie exists before the order request, so a lost response can be
  // retried with the same browser identity and exact payload after reload.
  await request('/orders/checkout-session', { cache: 'no-store' });
  savePendingCheckoutAttempt(attempt);
  try {
    const order = await request('/orders', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Idempotency-Key': effectiveIdemp,
    },
    body,
    });
    clearPendingCheckoutAttempt();
    return order;
  } catch (error) {
    if (error instanceof ApiError && [400, 409, 422].includes(error.status)) clearPendingCheckoutAttempt();
    throw error;
  }
}

const PENDING_CHECKOUT_KEY = 'alphazee_pending_checkout';
let memoryPendingCheckout = null;

function newCheckoutKey() {
  const bytes = new Uint8Array(24);
  globalThis.crypto.getRandomValues(bytes);
  return `chk_${Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('')}`;
}

export function getPendingCheckoutAttempt() {
  try {
    const stored = globalThis.window?.sessionStorage?.getItem(PENDING_CHECKOUT_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      if (typeof parsed.key === 'string' && parsed.payload && typeof parsed.payload === 'object') return parsed;
    }
  } catch {}
  return memoryPendingCheckout;
}

function savePendingCheckoutAttempt(attempt) {
  memoryPendingCheckout = attempt;
  try { globalThis.window?.sessionStorage?.setItem(PENDING_CHECKOUT_KEY, JSON.stringify(attempt)); } catch {}
}

function clearPendingCheckoutAttempt() {
  memoryPendingCheckout = null;
  try { globalThis.window?.sessionStorage?.removeItem(PENDING_CHECKOUT_KEY); } catch {}
}

export async function recoverPendingOrder() {
  const attempt = getPendingCheckoutAttempt();
  if (!attempt) return null;
  return submitOrder(attempt.payload, attempt.key);
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
 * Track order status with a private access code or existing scoped session.
 * @param {string} orderNumber
 * @param {string} accessCode
 * @returns {Promise<Object>} Order details
 */
export async function fetchOrderStatus(orderNumber, accessCode) {
  if (accessCode) {
    await request('/orders/access', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ order_number: orderNumber, access_code: accessCode }),
    });
  }
  return request(`/orders/${encodeURIComponent(orderNumber)}`);
}

export async function fetchExchangeOptions(orderNumber, lineId) {
  return request(`/orders/${encodeURIComponent(orderNumber)}/exchange-options/${encodeURIComponent(lineId)}`);
}

export async function recoverAdminOrderAccess(orderId, verificationNote) {
  return request(`/admin/orders/${encodeURIComponent(orderId)}/access-recovery`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ verification_note: verificationNote }),
  });
}

export async function revokeAdminOrderAccess(orderId) {
  return request(`/admin/orders/${encodeURIComponent(orderId)}/access-revoke`, {
    method: 'POST',
  });
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
export async function fetchAdminOrders({ status = null, page = 1, pageSize = 20, orderId = null, search = '' } = {}) {
  const query = new URLSearchParams();
  if (orderId) query.set('order_id', orderId);
  if (search.trim()) query.set('q', search.trim());
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
 * Record operational supplier acceptance and allocate inventory for fulfillment.
 * @param {string} orderId
 * @param {string|null} [notes]
 * @returns {Promise<Object>} Updated order details
 */
export async function confirmSupplierAcceptance(orderId, notes = null) {
  return request(`/admin/orders/${encodeURIComponent(orderId)}/confirm-supplier`, {
    method: 'POST',
    body: JSON.stringify({ notes }),
  });
}

/**
 * Flag expired unpaid bank transfers for owner review without releasing stock.
 * @returns {Promise<{ review_count: number, review_order_ids: string[] }>}
 */
export async function reviewExpiredOrders() {
  return request('/admin/orders/review-expired', {
    method: 'POST',
  });
}

export async function fetchPaymentInstructionsPreview(orderId) {
  return request(`/admin/orders/${encodeURIComponent(orderId)}/payment-instructions-preview`);
}

export async function markPaymentInstructionsSent(orderId, { channel, reference }) {
  return request(`/admin/orders/${encodeURIComponent(orderId)}/instructions-sent`, {
    method: 'POST',
    body: JSON.stringify({ confirmed_sent: true, channel, reference }),
  });
}

export async function resolvePaymentReview(orderId, { resolution, note }) {
  return request(`/admin/orders/${encodeURIComponent(orderId)}/payment-review`, {
    method: 'POST',
    body: JSON.stringify({ funds_checked: true, resolution, note }),
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
 * Initiate RTO return for a dispatched order in transit with courier.
 * @param {string} orderId
 * @param {Object} [payload] { reason, rto_courier_cost_minor }
 * @returns {Promise<Object>} Updated order details
 */
export async function initiateOrderRto(orderId, payload = {}) {
  return request(`/admin/orders/${encodeURIComponent(orderId)}/rto`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

/**
 * Record per-line physical receipt of an RTO parcel in quarantine.
 * @param {string} orderId
 * @returns {Promise<Object>} Updated order details
 */
export async function receiveOrderRto(orderId, lines) {
  return request(`/admin/orders/${encodeURIComponent(orderId)}/rto-received`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ lines }),
  });
}

/**
 * Record physical condition inspection and restock an RTO parcel.
 * @param {string} orderId
 * @param {Object} payload { lines: [{order_line_id, sellable_quantity, damaged_quantity}], notes }
 * @returns {Promise<Object>} Updated order details
 */
export async function inspectAndRestockRtoOrder(orderId, { lines, notes = '' }) {
  return request(`/admin/orders/${encodeURIComponent(orderId)}/rto-inspect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ lines, notes: notes || undefined }),
  });
}

export async function previewLegacyShipmentStock(shipmentId) {
  return request(`/admin/shipments/${encodeURIComponent(shipmentId)}/stock-reconciliation`);
}

export async function reconcileLegacyShipmentStock(shipmentId, payload) {
  return request(`/admin/shipments/${encodeURIComponent(shipmentId)}/stock-reconciliation`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}



/**
 * Fetch all registered suppliers.
 * @returns {Promise<{ suppliers: Array, total: number }>}
 */
export async function fetchAdminSuppliers() {
  return request('/admin/suppliers');
}

export async function fetchAdminCatalogVariants() {
  return request('/admin/catalog/variants');
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
 * Fetch supplier agreement terms.
 * @param {string} supplierId
 */
export async function fetchSupplierAgreement(supplierId) {
  return request(`/admin/suppliers/${encodeURIComponent(supplierId)}/agreement`);
}

/**
 * Update supplier agreement terms.
 * @param {string} supplierId
 * @param {Object} payload { payable_trigger, payment_terms_days, notes }
 */
export async function updateSupplierAgreement(supplierId, payload) {
  return request(`/admin/suppliers/${encodeURIComponent(supplierId)}/agreement`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

/**
 * Fetch supplier ledger entries and summary.
 * @param {string} supplierId
 * @param {number} page
 * @param {number} pageSize
 */
export async function fetchSupplierLedger(supplierId, page = 1, pageSize = 50) {
  return request(`/admin/suppliers/${encodeURIComponent(supplierId)}/ledger?page=${page}&page_size=${pageSize}`);
}

/**
 * Fetch real-time supplier liability and ledger summary.
 * @param {string} supplierId
 */
export async function fetchSupplierLedgerSummary(supplierId) {
  return request(`/admin/suppliers/${encodeURIComponent(supplierId)}/ledger/summary`);
}

/**
 * Manually post an approved supplier charge.
 * @param {string} supplierId
 * @param {Object} payload { amount_minor, reference, effective_date, notes }
 */
export async function postSupplierManualCharge(supplierId, payload) {
  return request(`/admin/suppliers/${encodeURIComponent(supplierId)}/ledger/charge`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

/**
 * Manually post an acknowledged vendor credit note.
 * @param {string} supplierId
 * @param {Object} payload { amount_minor, reference, effective_date, notes }
 */
export async function postSupplierCreditNote(supplierId, payload) {
  return request(`/admin/suppliers/${encodeURIComponent(supplierId)}/ledger/credit-note`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

/**
 * Immutably reverse a posted ledger entry.
 * @param {string} supplierId
 * @param {string} entryId
 * @param {string} reason
 */
export async function reverseSupplierLedgerEntry(arg1, arg2, arg3) {
  let supplierId = null;
  let entryId = null;
  let reason = '';
  if (arg3 !== undefined && arg3 !== null) {
    if (typeof arg2 === 'string' && typeof arg3 === 'string') {
      supplierId = arg1;
      entryId = arg2;
      reason = arg3;
    } else {
      entryId = arg1;
      reason = arg2;
      supplierId = arg3;
    }
  } else {
    entryId = arg1;
    reason = arg2;
  }
  const url = supplierId
    ? `/admin/suppliers/${encodeURIComponent(supplierId)}/ledger/${encodeURIComponent(entryId)}/reverse`
    : `/admin/suppliers/ledger/${encodeURIComponent(entryId)}/reverse`;
  return request(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason }),
  });
}

/**
 * Preview opening balance calculation.
 * @param {string} supplierId
 * @param {Object} payload { amount_minor, direction, as_of_date, reference, notes }
 */
export async function previewSupplierOpeningBalance(supplierId, payload) {
  return request(`/admin/suppliers/${encodeURIComponent(supplierId)}/ledger/opening-balance/preview`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

/**
 * Commit opening balance entry.
 * @param {string} supplierId
 * @param {Object} payload { amount_minor, direction, as_of_date, reference, notes }
 */
export async function applySupplierOpeningBalance(supplierId, payload) {
  return request(`/admin/suppliers/${encodeURIComponent(supplierId)}/ledger/opening-balance`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

/**
 * Record a supplier payment and allocate against charges (VF2).
 * @param {string} supplierId
 * @param {Object} payload { amount_minor, payment_method, reference, effective_date, notes, auto_allocate_fifo, allocations }
 */
export async function postSupplierPayment(supplierId, payload) {
  return request(`/admin/suppliers/${encodeURIComponent(supplierId)}/ledger/payment`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

/**
 * Disburse an unallocated advance payment to a supplier (VF2).
 * @param {string} supplierId
 * @param {Object} payload { amount_minor, payment_method, reference, effective_date, notes }
 */
export async function postSupplierAdvance(supplierId, payload) {
  return request(`/admin/suppliers/${encodeURIComponent(supplierId)}/ledger/advance`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

/**
 * Allocate unallocated payment/advance funds against a charge (VF2).
 * @param {string} supplierId
 * @param {string} paymentId
 * @param {Object} payload { charge_entry_id, amount_minor }
 */
export async function allocateSupplierPayment(supplierId, paymentId, payload) {
  return request(`/admin/suppliers/${encodeURIComponent(supplierId)}/ledger/payments/${encodeURIComponent(paymentId)}/allocate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

/**
 * Record cash refund received from a supplier (VF2).
 * @param {string} supplierId
 * @param {Object} payload { amount_minor, refund_method, reference, effective_date, notes }
 */
export async function postSupplierRefund(supplierId, payload) {
  return request(`/admin/suppliers/${encodeURIComponent(supplierId)}/ledger/refund`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

/**
 * Get unpaid charges and unallocated advances for allocation (VF2).
 * @param {string} supplierId
 */
export async function fetchSupplierUnpaidAndAdvances(supplierId) {
  return request(`/admin/suppliers/${encodeURIComponent(supplierId)}/ledger/unpaid-and-advances`);
}

/**
 * Get supplier period statement with opening, movement, and closing reconciliation (VF2).
 * @param {string} supplierId
 * @param {string} startDate
 * @param {string} endDate
 */
export async function fetchSupplierStatement(supplierId, startDate, endDate) {
  return request(`/admin/suppliers/${encodeURIComponent(supplierId)}/statement?start_date=${encodeURIComponent(startDate)}&end_date=${encodeURIComponent(endDate)}`);
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

export async function fetchAdminShipmentSettlement(shipmentId) {
  return request(`/admin/shipments/${encodeURIComponent(shipmentId)}/settlement`);
}

export async function recordAdminRefundExecution(returnId, payload) {
  return request(`/admin/returns/${encodeURIComponent(returnId)}/refund-executions`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
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

export async function dispatchAdminReplacement(returnId, payload) {
  return request(`/admin/returns/${encodeURIComponent(returnId)}/dispatch-replacement`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  });
}

export async function inspectAdminShipmentRto(shipmentId, payload) {
  return request(`/admin/shipments/${encodeURIComponent(shipmentId)}/inspect-rto`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  });
}

export async function receiveAdminReturn(returnId, receivedQuantity) {
  return request(`/admin/returns/${encodeURIComponent(returnId)}/receive`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ received_quantity: receivedQuantity }),
  });
}

export async function inspectAdminReturn(returnId, payload) {
  return request(`/admin/returns/${encodeURIComponent(returnId)}/inspect`, {
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

/**
 * Record a new business expense.
 * @param {Object} payload { category, amount_minor, incurred_date, paid_date, payee, reference, payment_method, linked_shipment_id, linked_return_id, linked_courier_settlement_id, notes }
 */
export async function createBusinessExpense(payload) {
  return request('/admin/expenses', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

/**
 * Fetch list of business expenses with filters.
 * @param {Object} params { start_date, end_date, category, payment_method, is_paid, limit, offset }
 */
export async function fetchBusinessExpenses(params = {}) {
  const query = new URLSearchParams();
  for (const [key, val] of Object.entries(params)) {
    if (val !== undefined && val !== null && val !== '') {
      query.append(key, val);
    }
  }
  const qStr = query.toString();
  return request(`/admin/expenses${qStr ? `?${qStr}` : ''}`);
}

/**
 * Fetch business expense summary aggregates and category breakdown.
 * @param {Object} params { start_date, end_date }
 */
export async function fetchBusinessExpenseSummary(params = {}) {
  const query = new URLSearchParams();
  for (const [key, val] of Object.entries(params)) {
    if (val !== undefined && val !== null && val !== '') {
      query.append(key, val);
    }
  }
  const qStr = query.toString();
  return request(`/admin/expenses/summary${qStr ? `?${qStr}` : ''}`);
}

/**
 * Fetch period financial statement, P&L, operating results, and cash reconciliation.
 * @param {Object} params { start_date, end_date, timezone }
 */
export async function fetchPeriodFinancialReport(params = {}) {
  const query = new URLSearchParams();
  for (const [key, val] of Object.entries(params)) {
    if (val !== undefined && val !== null && val !== '') {
      query.append(key, val);
    }
  }
  const qStr = query.toString();
  return request(`/admin/reports/period${qStr ? `?${qStr}` : ''}`);
}

/**
 * Fetch per-order economics list with line-item margins and supplier costs.
 * @param {Object} params { start_date, end_date, order_id, status, search, limit, offset }
 */
export async function fetchOrderEconomics(params = {}) {
  const query = new URLSearchParams();
  for (const [key, val] of Object.entries(params)) {
    if (val !== undefined && val !== null && val !== '') {
      query.append(key, val);
    }
  }
  const qStr = query.toString();
  return request(`/admin/reports/orders${qStr ? `?${qStr}` : ''}`);
}

/**
 * Get CSV export URL for order economics.
 * @param {Object} params { start_date, end_date }
 */
export function getOrderEconomicsCsvUrl(params = {}) {
  const query = new URLSearchParams();
  for (const [key, val] of Object.entries(params)) {
    if (val !== undefined && val !== null && val !== '') {
      query.append(key, val);
    }
  }
  const qStr = query.toString();
  return `${API_BASE}/admin/reports/orders/export${qStr ? `?${qStr}` : ''}`;
}

/**
 * Get CSV export URL for period financial statement.
 * @param {Object} params { start_date, end_date }
 */
export function getPeriodReportCsvUrl(params = {}) {
  const query = new URLSearchParams();
  for (const [key, val] of Object.entries(params)) {
    if (val !== undefined && val !== null && val !== '') {
      query.append(key, val);
    }
  }
  const qStr = query.toString();
  return `${API_BASE}/admin/reports/period/export${qStr ? `?${qStr}` : ''}`;
}

// ── Vendor Stock Portal APIs (VS2-VS3) ─────────────────────────────────────────

/**
 * Fetch assigned stock variants for the logged-in vendor.
 * @param {Object} params { page, limit, search }
 */
export async function fetchVendorStock(params = {}) {
  const query = new URLSearchParams();
  for (const [key, val] of Object.entries(params)) {
    if (val !== undefined && val !== null && val !== '') {
      query.append(key, val);
    }
  }
  const qStr = query.toString();
  return request(`/vendor/stock${qStr ? `?${qStr}` : ''}`);
}

/**
 * Update physical count for a variant assigned to this vendor.
 * @param {number} variantId
 * @param {Object} body { counted_quantity, expected_version, reason, note, request_ref }
 */
export async function updateVendorStockCount(variantId, body) {
  return request(`/vendor/stock/${variantId}/count`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

/**
 * Explicitly report a stock shortage for a variant.
 * @param {number} variantId
 * @param {Object} body { reported_count, note }
 */
export async function reportVendorShortage(variantId, body) {
  return request(`/vendor/stock/${variantId}/shortage`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

/**
 * Fetch recent audit update history for variants assigned to this vendor.
 * @param {number} limit
 */
export async function fetchVendorStockHistory(limit = 30) {
  return request(`/vendor/stock/history?limit=${encodeURIComponent(limit)}`);
}

// ── Owner Administration of Vendor Users & Shortages ──────────────────────────

/**
 * Fetch provisioned vendor user accounts for a supplier.
 * @param {string} supplierId UUID
 */
export async function fetchSupplierVendorUsers(supplierId) {
  return request(`/admin/suppliers/${supplierId}/users`);
}

/**
 * Provision a new stock login for a supplier.
 * @param {string} supplierId UUID
 * @param {Object} body { username, password, allow_short_local }
 */
export async function provisionVendorUser(supplierId, body) {
  return request(`/admin/suppliers/${supplierId}/users`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

/**
 * Reset password for a vendor user account.
 * @param {string} vendorUserId UUID
 * @param {Object} body { password, allow_short_local }
 */
export async function resetVendorPassword(vendorUserId, body) {
  return request(`/admin/vendor-users/${vendorUserId}/reset-password`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

/**
 * Toggle active status of a vendor user account.
 * @param {string} vendorUserId UUID
 * @param {boolean} isActive
 */
export async function toggleVendorUserStatus(vendorUserId, isActive) {
  return request(`/admin/vendor-users/${vendorUserId}/toggle-status`, {
    method: 'POST',
    body: JSON.stringify({ is_active: isActive }),
  });
}

/**
 * Fetch open or all shortages for owner review.
 * @param {string|null} vendorId Optional filter
 */
export async function fetchShortages(vendorId = null) {
  const q = vendorId ? `?vendor_id=${encodeURIComponent(vendorId)}` : '';
  return request(`/admin/shortages${q}`);
}

/**
 * Resolve or cancel a reported stock shortage.
 * @param {string} shortageId UUID
 * @param {Object} body { resolution_action, resolution_note }
 */
export async function resolveShortage(shortageId, body) {
  return request(`/admin/shortages/${shortageId}/resolve`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

// ── VF6: Store Settings & Owner Preferences ──────────────────────────────────

/**
 * Fetch public store settings (branding, announcement bar, published policies, theme tokens).
 */
export async function fetchPublicStoreSettings() {
  return request('/store/settings');
}

/**
 * Fetch admin store settings (full configuration, draft policies, thresholds, version).
 */
export async function fetchAdminStoreSettings() {
  return request('/admin/settings');
}

/**
 * Update store settings with validation and audit log generation.
 * @param {Object} payload
 */
export async function updateAdminStoreSettings(payload) {
  return request('/admin/settings', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

/**
 * Publish or unpublish a legal policy (delivery, return, terms, privacy).
 * @param {string} policyType 'delivery' | 'return' | 'terms' | 'privacy'
 * @param {boolean} publish
 */
export async function publishStorePolicy(policyType, publish) {
  return request(`/admin/settings/policies/${encodeURIComponent(policyType)}/publish`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ publish }),
  });
}

/**
 * Fetch chronological audit logs of store settings changes.
 * @param {number} [limit=50]
 */
export async function fetchSettingsAuditLogs(limit = 50) {
  return request(`/admin/settings/audit-logs?limit=${encodeURIComponent(limit)}`);
}

/**
 * Fetch personal interface preferences for the authenticated owner.
 */
export async function fetchAdminPreferences() {
  return request('/admin/preferences');
}

/**
 * Update personal interface preferences.
 * @param {Object} payload { theme, table_density, default_date_range, nav_order, dashboard_layout }
 */
export async function updateAdminPreferences(payload) {
  return request('/admin/preferences', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

/**
 * Reset interface preferences to factory defaults.
 */
export async function resetAdminPreferences() {
  return request('/admin/preferences/reset', {
    method: 'POST',
  });
}








