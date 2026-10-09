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
 * @returns {Promise<Array>}
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
 * @returns {Promise<{ products: Array, total: number, page: number, page_size: number, collection_id: string|null }>}
 */
export async function fetchProducts({ collectionId = null, page = 1, pageSize = 20 } = {}) {
  const query = new URLSearchParams();
  if (collectionId && collectionId !== 'all') {
    query.set('collection_id', collectionId);
  }
  query.set('page', String(page));
  query.set('page_size', String(pageSize));
  return request(`/products?${query.toString()}`);
}

/**
 * Fetch active products featured in the hero carousel.
 * @returns {Promise<Array>}
 */
export async function fetchHeroProducts() {
  return request('/products/hero');
}

/**
 * Fetch product detail by slug with variants.
 * @param {string} slug
 * @returns {Promise<Object>}
 */
export async function fetchProductBySlug(slug) {
  return request(`/products/${encodeURIComponent(slug)}`);
}
