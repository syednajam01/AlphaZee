import { createOverlay } from '../utils/overlay.js';
import { cart } from '../utils/cart.js';
import { capabilities, CHECKOUT_UNAVAILABLE } from '../utils/capabilities.js';
import { storeConfig } from '../data/store-config.js';
import { formatPkr } from '../utils/money.js';
import { escapeHtml, sanitizeMediaUrl, createSafeImageElement } from '../utils/dom.js';

export function createCartDrawer(onCheckout, onExplore) {
  const backdrop = document.createElement('div');
  backdrop.className = 'drawer-backdrop';
  backdrop.id = 'cart-drawer-backdrop';

  const drawer = document.createElement('div');
  drawer.className = 'drawer';
  drawer.id = 'cart-drawer';
  drawer.setAttribute('role', 'dialog');
  drawer.setAttribute('aria-label', 'Shopping Cart');

  drawer.innerHTML = `
    <div class="drawer-header">
      <div style="display: flex; align-items: center; gap: 8px;">
        <h2 class="drawer-title">Shopping Cart</h2>
        <span class="badge badge-neutral" id="cart-item-count-badge">0 items</span>
      </div>
      <button class="btn-icon" id="cart-close-btn" aria-label="Close cart">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </button>
    </div>

    <div class="drawer-body" id="cart-items-container">
      <!-- Dynamic cart items -->
    </div>

    <div class="drawer-footer" id="cart-footer">
      <div id="cart-availability-alert" style="display: none; margin-bottom: 12px; padding: 10px 12px; background: var(--color-error-bg); border: 1px solid rgba(180, 35, 24, 0.3); border-radius: var(--radius-sm); font-size: 0.75rem; color: var(--color-error);">
        Some items in your cart are currently out of stock or unavailable. Please adjust before checkout.
      </div>
      <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px;">
        <span style="font-weight: 500;">Subtotal</span>
        <span style="font-size: 1.25rem; font-weight: 700;" class="price-tabular" id="cart-subtotal">PKR 0</span>
      </div>
      <p class="cart-delivery-note">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink: 0;">
          <rect x="1" y="3" width="15" height="13"></rect>
          <polygon points="16 8 20 8 23 11 23 16 16 16 16 8"></polygon>
          <circle cx="5.5" cy="18.5" r="2.5"></circle>
          <circle cx="18.5" cy="18.5" r="2.5"></circle>
        </svg>
        <span>Free nationwide delivery across Pakistan (${escapeHtml(storeConfig.shippingInfo.standardTime)}).</span>
      </p>
      <p id="checkout-availability" role="status" class="cart-sample-notice"></p>
      <button class="btn btn-primary" id="btn-checkout" disabled style="width: 100%; min-height: 48px;">
        Proceed to Checkout
      </button>
    </div>
  `;

  function render(state) {
    const itemsContainer = drawer.querySelector('#cart-items-container');
    const badge = drawer.querySelector('#cart-item-count-badge');
    const subtotal = drawer.querySelector('#cart-subtotal');
    const footer = drawer.querySelector('#cart-footer');
    const alertBox = drawer.querySelector('#cart-availability-alert');
    const checkoutBtn = drawer.querySelector('#btn-checkout');

    badge.textContent = `${state.count} ${state.count === 1 ? 'item' : 'items'}`;
    subtotal.textContent = state.formattedTotal;

    if (state.items.length === 0) {
      itemsContainer.innerHTML = `
        <div class="drawer-empty-state">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin: 0 auto 16px; opacity: 0.35;">
            <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"></path>
            <line x1="3" y1="6" x2="21" y2="6"></line>
            <path d="M16 10a4 4 0 0 1-8 0"></path>
          </svg>
          <h3 class="drawer-empty-title">Your shopping bag is empty</h3>
          <p class="drawer-empty-desc">Discover our latest pieces, crafted for everyday comfort and clean silhouettes.</p>
          <button type="button" class="btn btn-secondary" id="btn-cart-explore" style="min-width: 160px;">
            Explore Collection
          </button>
        </div>
      `;
      footer.style.opacity = '0.5';
      checkoutBtn.disabled = true;
      alertBox.style.display = 'none';

      itemsContainer.querySelector('#btn-cart-explore')?.addEventListener('click', () => {
        close();
        if (onExplore) {
          onExplore();
        } else {
          document.getElementById('featured')?.scrollIntoView({ behavior: 'smooth' });
        }
      });
    } else {
      footer.style.opacity = '1';

      if (state.isReconciling) {
        alertBox.style.display = 'block';
        alertBox.textContent = 'Verifying live catalog prices and availability...';
        checkoutBtn.disabled = true;
        checkoutBtn.textContent = 'Verifying Cart...';
        checkoutBtn.classList.remove('btn-primary');
        checkoutBtn.classList.add('btn-secondary');
      } else if (state.hasUnavailable || state.hasUnverified) {
        alertBox.style.display = 'block';
        alertBox.textContent = state.hasUnverified
          ? 'Some items have unverified availability due to a network connection issue.'
          : 'Some items in your cart are currently out of stock or unavailable. Please adjust before checkout.';
        checkoutBtn.disabled = true;
        checkoutBtn.textContent = state.hasUnverified ? 'Availability Unverified' : 'Unavailable Items in Cart';
        checkoutBtn.classList.remove('btn-primary');
        checkoutBtn.classList.add('btn-secondary');
      } else {
        alertBox.style.display = 'none';
        checkoutBtn.disabled = false;
        checkoutBtn.textContent = 'Proceed to Checkout';
        checkoutBtn.classList.add('btn-primary');
        checkoutBtn.classList.remove('btn-secondary');
      }

      itemsContainer.innerHTML = state.items.map(item => {
        const safeTitle = escapeHtml(item.title);
        const formattedItemPrice = formatPkr(item.price_minor);
        const metaParts = [];
        if (item.size) metaParts.push(`Size: ${escapeHtml(item.size)}`);
        if (item.color) metaParts.push(`Color: ${escapeHtml(item.color)}`);

        return `
          <div class="cart-item" data-variant-id="${escapeHtml(String(item.variant_id))}">
            <div class="cart-item-info">
              <div class="cart-item-title">${safeTitle}</div>
              <div class="cart-item-meta">${metaParts.join(' • ')}</div>
              ${!item.is_available ? `
                <span class="badge ${item.availability === 'unverified' ? 'badge-neutral' : 'badge-out-of-stock'}" style="margin: 4px 0; align-self: flex-start; font-size: 0.7rem;">
                  ${item.availability === 'unverified' ? 'Availability Unverified (Offline)' : 'Currently Unavailable'}
                </span>
              ` : ''}
              <div class="cart-item-price price-tabular">${formattedItemPrice}</div>
              <div style="display: flex; align-items: center; justify-content: space-between; margin-top: 8px;">
                <div class="cart-qty-ctrl">
                  <button class="cart-qty-btn btn-qty-dec" aria-label="Decrease quantity of ${safeTitle}">−</button>
                  <span class="cart-qty-num price-tabular">${item.quantity}</span>
                  <button class="cart-qty-btn btn-qty-inc" aria-label="Increase quantity of ${safeTitle}">+</button>
                </div>
                <button class="btn-remove-item" type="button" aria-label="Remove ${safeTitle} from cart">
                  Remove
                </button>
              </div>
            </div>
          </div>
        `;
      }).join('');

      // Prepend safe image elements via DOM properties
      state.items.forEach(item => {
        const itemEl = itemsContainer.querySelector(`[data-variant-id="${String(item.variant_id)}"]`);
        if (itemEl) {
          const img = createSafeImageElement({
            src: item.image_url,
            alt: item.title || 'Cart item',
            className: 'cart-item-img',
          });
          itemEl.prepend(img);
        }
      });

      // Add quantity & remove listeners
      itemsContainer.querySelectorAll('.cart-item').forEach(el => {
        const variantId = el.dataset.variantId;
        el.querySelector('.btn-qty-dec').addEventListener('click', () => cart.updateQuantity(variantId, -1));
        el.querySelector('.btn-qty-inc').addEventListener('click', () => cart.updateQuantity(variantId, 1));
        el.querySelector('.btn-remove-item').addEventListener('click', () => cart.removeItem(variantId));
      });
    }
  }

  function renderWithCapabilities(state) {
    render(state);
    const availability = capabilities.getState();
    drawer.querySelector('#checkout-availability').textContent = availability.checkoutEnabled
      ? 'SAMPLE / TEST checkout. No real orders.' : CHECKOUT_UNAVAILABLE;
    if (!availability.checkoutEnabled) {
      const button = drawer.querySelector('#btn-checkout');
      button.disabled = true;
      button.textContent = 'Checkout unavailable';
    }
  }
  cart.subscribe(renderWithCapabilities);
  capabilities.subscribe(() => renderWithCapabilities(cart.getState()));

  function open() {
    capabilities.refresh();
    overlay.open();
    // Reconcile with API in background when drawer is opened
    cart.reconcileWithApi();
  }

  function close() {
    overlay.close();
  }

  const overlay = createOverlay({ element: drawer, backdrop });

  backdrop.addEventListener('click', close);
  drawer.querySelector('#cart-close-btn').addEventListener('click', close);

  drawer.querySelector('#btn-checkout').addEventListener('click', () => {
    if (!capabilities.getState().checkoutEnabled) return;
    close();
    if (onCheckout) {
      onCheckout();
    }
  });

  return {
    backdrop,
    drawer,
    open,
    close
  };
}
