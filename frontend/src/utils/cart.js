import { formatPkr, extractPriceMinor } from './money.js';
import { fetchProductBySlug } from './api.js';

const STORAGE_KEY = 'alphazee_cart_v2';
const LEGACY_STORAGE_KEY = 'alphazee_cart_v1';
const MAX_QUANTITY_PER_ITEM = 99;

/**
 * Validate and sanitize a raw stored cart item object.
 * Returns null if the item cannot be safely coerced to a valid CartItem.
 */
function validateCartItem(raw) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;

  // Strictly validate variant_id: must be a positive safe integer or string of digits
  let variantId = null;
  if (typeof raw.variant_id === 'number' && Number.isSafeInteger(raw.variant_id) && raw.variant_id > 0) {
    variantId = raw.variant_id;
  } else if (typeof raw.variant_id === 'string') {
    const trimmed = raw.variant_id.trim();
    if (/^\d+$/.test(trimmed)) {
      const parsed = Number(trimmed);
      if (Number.isSafeInteger(parsed) && parsed > 0) {
        variantId = parsed;
      }
    }
  }
  if (variantId === null) return null;

  const quantity = Number.isSafeInteger(raw.quantity) && raw.quantity > 0
    ? Math.min(raw.quantity, MAX_QUANTITY_PER_ITEM)
    : 1;

  // Validate price: must resolve to a valid non-negative integer minor unit
  const priceMinor = extractPriceMinor(raw.price_minor ?? raw.price);
  if (priceMinor === null) {
    return null;
  }

  const title = typeof raw.title === 'string' && raw.title.trim() ? raw.title.trim() : 'AlphaZee Essential';
  const productId = typeof raw.product_id === 'string' ? raw.product_id : (typeof raw.id === 'string' ? raw.id : '');
  const slug = typeof raw.slug === 'string' ? raw.slug : '';
  const sku = typeof raw.sku === 'string' ? raw.sku : '';
  const size = raw.size ? String(raw.size) : (raw.options?.size ? String(raw.options.size) : null);
  const color = raw.color ? String(raw.color) : (raw.options?.color ? String(raw.options.color) : null);
  const imageUrl = typeof raw.image_url === 'string' ? raw.image_url : (typeof raw.image === 'string' ? raw.image : '');
  const isAvailable = raw.is_available === false ? false : (raw.availability === 'unverified' ? false : true);
  const availability = raw.availability || (isAvailable ? 'available' : 'unavailable');

  return {
    variant_id: variantId,
    product_id: productId,
    slug,
    sku,
    title,
    size,
    color,
    price_minor: priceMinor,
    image_url: imageUrl,
    quantity,
    is_available: isAvailable,
    availability,
  };
}

class CartStore {
  constructor() {
    this.storageKey = STORAGE_KEY;
    this.memoryFallback = [];
    this.items = this.load();
    this.listeners = new Set();
    this.isReconciling = false;
  }

  /**
   * Safely load cart from localStorage with v1 migration and strict validation.
   */
  load() {
    try {
      // Check for legacy v1 storage and clean up safely
      if (typeof window !== 'undefined' && window.localStorage) {
        if (localStorage.getItem(LEGACY_STORAGE_KEY)) {
          try {
            localStorage.removeItem(LEGACY_STORAGE_KEY);
          } catch {
            // Ignore storage removal errors
          }
        }
      }

      const rawJson = typeof window !== 'undefined' && window.localStorage
        ? localStorage.getItem(this.storageKey)
        : null;

      if (!rawJson) return [];

      const parsed = JSON.parse(rawJson);
      if (!Array.isArray(parsed)) return [];

      const validItems = [];
      for (const entry of parsed) {
        const item = validateCartItem(entry);
        if (item) {
          validItems.push(item);
        }
      }
      return validItems;
    } catch (err) {
      console.warn('[CartStore] Failed to parse stored cart; starting fresh.', err);
      return [];
    }
  }

  /**
   * Persist current state to localStorage with in-memory fallback.
   */
  save() {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        localStorage.setItem(this.storageKey, JSON.stringify(this.items));
      }
    } catch (err) {
      console.warn('[CartStore] Failed to persist cart to localStorage, using in-memory state.', err);
      this.memoryFallback = [...this.items];
    }
    this.notify();
  }

  subscribe(listener) {
    this.listeners.add(listener);
    listener(this.getState());
    return () => this.listeners.delete(listener);
  }

  notify() {
    const state = this.getState();
    this.listeners.forEach((fn) => {
      try {
        fn(state);
      } catch (err) {
        console.error('[CartStore] Error in subscriber listener', err);
      }
    });
  }

  getState() {
    const count = this.items.reduce((sum, item) => {
      const q = (typeof item.quantity === 'number' && Number.isSafeInteger(item.quantity) && item.quantity > 0) ? item.quantity : 0;
      return sum + q;
    }, 0);
    const totalMinor = this.items.reduce((sum, item) => {
      const price = (typeof item.price_minor === 'number' && Number.isSafeInteger(item.price_minor) && item.price_minor >= 0) ? item.price_minor : 0;
      const q = (typeof item.quantity === 'number' && Number.isSafeInteger(item.quantity) && item.quantity > 0) ? item.quantity : 0;
      return sum + (price * q);
    }, 0);
    const hasUnavailable = this.items.some(
      item => !item.is_available || extractPriceMinor(item.price_minor) === null
    );
    const hasUnverified = this.items.some(item => item.availability === 'unverified');

    return {
      items: [...this.items],
      count,
      total_minor: Math.max(0, totalMinor),
      formattedTotal: formatPkr(Math.max(0, totalMinor)),
      hasUnavailable,
      hasUnverified,
      isReconciling: Boolean(this.isReconciling),
    };
  }

  /**
   * Add or increment an item in the cart.
   * Keyed strictly by variant_id.
   */
  addItem(itemData, options = {}, quantity = 1) {
    if (typeof quantity !== 'number' || !Number.isSafeInteger(quantity) || quantity <= 0) {
      console.warn('[CartStore] Refusing to add invalid cart item quantity:', quantity);
      return false;
    }
    const parsedQty = Math.min(quantity, MAX_QUANTITY_PER_ITEM);
    const raw = {
      ...itemData,
      ...options,
      quantity: parsedQty,
    };

    const valid = validateCartItem(raw);
    if (!valid) {
      console.warn('[CartStore] Refusing to add invalid cart item:', itemData);
      return false;
    }

    const existingIndex = this.items.findIndex(
      (item) => String(item.variant_id) === String(valid.variant_id)
    );

    if (existingIndex > -1) {
      const newQty = Math.min(this.items[existingIndex].quantity + valid.quantity, MAX_QUANTITY_PER_ITEM);
      this.items[existingIndex].quantity = newQty;
      // Update price/availability if newer data provided
      this.items[existingIndex].price_minor = valid.price_minor;
      this.items[existingIndex].is_available = valid.is_available;
      this.items[existingIndex].availability = valid.availability;
    } else {
      this.items.push(valid);
    }

    this.save();
    return true;
  }

  updateQuantity(variantId, delta) {
    if (typeof delta !== 'number' || !Number.isInteger(delta)) {
      console.warn('[CartStore] Rejected non-integer quantity delta:', delta);
      return;
    }
    const itemIndex = this.items.findIndex(
      (item) => String(item.variant_id) === String(variantId)
    );

    if (itemIndex > -1) {
      const updated = this.items[itemIndex].quantity + delta;
      if (updated <= 0) {
        this.items.splice(itemIndex, 1);
      } else {
        this.items[itemIndex].quantity = Math.min(updated, MAX_QUANTITY_PER_ITEM);
      }
      this.save();
    }
  }

  removeItem(variantId) {
    this.items = this.items.filter(
      (item) => String(item.variant_id) !== String(variantId)
    );
    this.save();
  }

  clear() {
    this.items = [];
    this.save();
  }

  /**
   * Reconcile prices and availability against live API data.
   * Only called on cart drawer open or explicit check — never on every quantity click.
   */
  async reconcileWithApi() {
    if (this.items.length === 0 || this.isReconciling) return;
    this.isReconciling = true;
    this.notify();

    try {
      // 1. Items without a slug cannot be verified against the catalog — mark unverified immediately
      for (const item of this.items) {
        if (!item.slug || typeof item.slug !== 'string' || !item.slug.trim()) {
          item.is_available = false;
          item.availability = 'unverified';
        }
      }

      // 2. Find all distinct valid product slugs to check
      const slugsToCheck = [
        ...new Set(
          this.items
            .map((i) => i.slug)
            .filter((s) => typeof s === 'string' && s.trim())
        ),
      ];

      for (const slug of slugsToCheck) {
        try {
          const product = await fetchProductBySlug(slug);
          if (!product || !Array.isArray(product.variants)) {
            // Malformed product payload: mark matching items unverified
            for (const item of this.items) {
              if (item.slug === slug) {
                item.is_available = false;
                item.availability = 'unverified';
              }
            }
            continue;
          }

          for (const item of this.items) {
            if (item.slug === slug) {
              const liveVariant = product.variants.find(
                (v) => String(v.id) === String(item.variant_id)
              );

              if (liveVariant) {
                const liveMinor = extractPriceMinor(liveVariant.price ?? liveVariant.price_minor);
                const hasValidPrice = liveMinor !== null;
                if (hasValidPrice) {
                  item.price_minor = liveMinor;
                }
                const isAvailable = hasValidPrice && liveVariant.availability === 'available' && liveVariant.is_active !== false;
                item.is_available = isAvailable;
                item.availability = isAvailable ? 'available' : (!hasValidPrice ? 'unavailable' : (liveVariant.availability || 'unavailable'));
              } else {
                // Variant no longer exists in active catalog
                item.is_available = false;
                item.availability = 'unavailable';
              }
            }
          }
        } catch (err) {
          // If product is 404 (deactivated or deleted), mark all items for this product as unavailable
          if (err && (err.status === 404 || err.message?.includes('404'))) {
            for (const item of this.items) {
              if (item.slug === slug) {
                item.is_available = false;
                item.availability = 'unavailable';
              }
            }
          } else {
            // Network failure or offline: preserve item in cart but mark availability as unverified
            for (const item of this.items) {
              if (item.slug === slug) {
                item.is_available = false;
                item.availability = 'unverified';
              }
            }
          }
        }
      }

      this.save();
    } finally {
      this.isReconciling = false;
      this.notify();
    }
  }
}

export const cart = new CartStore();
