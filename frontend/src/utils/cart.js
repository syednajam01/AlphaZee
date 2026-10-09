import { formatPkr } from './money.js';
import { fetchProductBySlug } from './api.js';

const STORAGE_KEY = 'alphazee_cart_v2';
const LEGACY_STORAGE_KEY = 'alphazee_cart_v1';
const MAX_QUANTITY_PER_ITEM = 99;

/**
 * Validate and sanitize a raw stored cart item object.
 * Returns null if the item cannot be safely coerced to a valid CartItem.
 */
function validateCartItem(raw) {
  if (!raw || typeof raw !== 'object') return null;

  const variantId = raw.variant_id !== undefined && raw.variant_id !== null ? raw.variant_id : null;
  if (variantId === null || variantId === '') return null;

  const quantity = Number.isInteger(raw.quantity) && raw.quantity > 0
    ? Math.min(raw.quantity, MAX_QUANTITY_PER_ITEM)
    : 1;

  const priceMinor = typeof raw.price_minor === 'number' && Number.isInteger(raw.price_minor) && raw.price_minor >= 0
    ? raw.price_minor
    : (typeof raw.price === 'number' && raw.price >= 0 ? Math.round(raw.price * 100) : 0);

  const title = typeof raw.title === 'string' && raw.title.trim() ? raw.title.trim() : 'AlphaZee Essential';
  const productId = typeof raw.product_id === 'string' ? raw.product_id : (typeof raw.id === 'string' ? raw.id : '');
  const slug = typeof raw.slug === 'string' ? raw.slug : '';
  const sku = typeof raw.sku === 'string' ? raw.sku : '';
  const size = raw.size ? String(raw.size) : (raw.options?.size ? String(raw.options.size) : null);
  const color = raw.color ? String(raw.color) : (raw.options?.color ? String(raw.options.color) : null);
  const imageUrl = typeof raw.image_url === 'string' ? raw.image_url : (typeof raw.image === 'string' ? raw.image : '');
  const isAvailable = raw.is_available !== false;

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
    const count = this.items.reduce((sum, item) => sum + item.quantity, 0);
    const totalMinor = this.items.reduce((sum, item) => sum + (item.price_minor * item.quantity), 0);
    const hasUnavailable = this.items.some(item => !item.is_available);

    return {
      items: [...this.items],
      count,
      total_minor: totalMinor,
      formattedTotal: formatPkr(totalMinor),
      hasUnavailable,
      isReconciling: this.isReconciling,
    };
  }

  /**
   * Add or increment an item in the cart.
   * Keyed strictly by variant_id.
   */
  addItem(itemData, options = {}, quantity = 1) {
    const parsedQty = Number.isInteger(quantity) && quantity > 0 ? quantity : 1;
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
    } else {
      this.items.push(valid);
    }

    this.save();
    return true;
  }

  updateQuantity(variantId, delta) {
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
      // Find all distinct product slugs to check
      const slugsToCheck = [...new Set(this.items.map(i => i.slug).filter(Boolean))];

      for (const slug of slugsToCheck) {
        try {
          const product = await fetchProductBySlug(slug);
          if (!product || !Array.isArray(product.variants)) continue;

          for (const item of this.items) {
            if (item.slug === slug) {
              const liveVariant = product.variants.find(
                (v) => String(v.id) === String(item.variant_id)
              );

              if (liveVariant) {
                item.price_minor = liveVariant.price_minor;
                item.is_available = liveVariant.availability === 'available' && liveVariant.is_active;
              } else {
                // Variant no longer exists in active catalog
                item.is_available = false;
              }
            }
          }
        } catch {
          // If a single product fetch fails, keep cached values without crashing
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
