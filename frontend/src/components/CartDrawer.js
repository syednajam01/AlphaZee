import { cart } from '../utils/cart.js';
import { storeConfig } from '../data/store-config.js';
import { formatPkr } from '../utils/money.js';
import { escapeHtml, sanitizeMediaUrl } from '../utils/dom.js';

export function createCartDrawer(onCheckout) {
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
      <div id="cart-availability-alert" style="display: none; margin-bottom: 12px; padding: 10px 12px; background: #FFF5F5; border: 1px solid #FED7D7; border-radius: var(--radius-sm); font-size: 0.75rem; color: #C53030;">
        Some items in your cart are currently out of stock or unavailable. Please adjust before checkout.
      </div>
      <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px;">
        <span style="font-weight: 500;">Subtotal</span>
        <span style="font-size: 1.25rem; font-weight: 700;" id="cart-subtotal">PKR 0</span>
      </div>
      <p style="font-size: 0.75rem; color: var(--color-text-muted); margin-bottom: 16px;">
        Shipping calculated at checkout (${escapeHtml(storeConfig.shippingInfo.standardTime)}).
      </p>
      <button class="btn btn-primary" id="btn-checkout" style="width: 100%; min-height: 48px;">
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
        <div style="text-align: center; padding: 48px 16px; color: var(--color-text-muted);">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin: 0 auto 16px; opacity: 0.5;">
            <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"></path>
            <line x1="3" y1="6" x2="21" y2="6"></line>
            <path d="M16 10a4 4 0 0 1-8 0"></path>
          </svg>
          <p style="font-weight: 600; font-size: 1.125rem; color: var(--color-text); margin-bottom: 4px;">Your cart is empty</p>
          <p style="font-size: 0.875rem;">Discover our latest pieces and build your minimalist wardrobe.</p>
        </div>
      `;
      footer.style.opacity = '0.5';
      checkoutBtn.disabled = true;
      alertBox.style.display = 'none';
    } else {
      footer.style.opacity = '1';

      if (state.hasUnavailable) {
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
        const safeImage = sanitizeMediaUrl(item.image_url, 'https://images.unsplash.com/photo-1521572267360-ee0c2909d518?auto=format&fit=crop&w=800&q=80');
        const formattedItemPrice = formatPkr(item.price_minor);
        const metaParts = [];
        if (item.size) metaParts.push(`Size: ${escapeHtml(item.size)}`);
        if (item.color) metaParts.push(`Color: ${escapeHtml(item.color)}`);

        return `
          <div class="cart-item" data-variant-id="${escapeHtml(String(item.variant_id))}">
            <img src="${safeImage}" alt="${safeTitle}" class="cart-item-img" />
            <div class="cart-item-info">
              <div class="cart-item-title">${safeTitle}</div>
              <div class="cart-item-meta">${metaParts.join(' • ')}</div>
              ${!item.is_available ? `
                <span class="badge badge-neutral" style="color: ${item.availability === 'unverified' ? '#B45309' : '#C53030'}; background: ${item.availability === 'unverified' ? '#FEF3C7' : '#FFF5F5'}; font-size: 0.7rem; align-self: flex-start; margin: 4px 0;">
                  ${item.availability === 'unverified' ? 'Availability Unverified (Offline)' : 'Currently Unavailable'}
                </span>
              ` : ''}
              <div class="cart-item-price">${formattedItemPrice}</div>
              <div style="display: flex; align-items: center; justify-content: space-between; margin-top: 8px;">
                <div class="cart-qty-ctrl">
                  <button class="cart-qty-btn btn-qty-dec" aria-label="Decrease quantity">−</button>
                  <span class="cart-qty-num">${item.quantity}</span>
                  <button class="cart-qty-btn btn-qty-inc" aria-label="Increase quantity">+</button>
                </div>
                <button class="btn-remove-item" style="font-size: 0.75rem; color: #b3261e; text-decoration: underline; background: none; border: none; cursor: pointer;">
                  Remove
                </button>
              </div>
            </div>
          </div>
        `;
      }).join('');

      // Add quantity & remove listeners
      itemsContainer.querySelectorAll('.cart-item').forEach(el => {
        const variantId = el.dataset.variantId;
        el.querySelector('.btn-qty-dec').addEventListener('click', () => cart.updateQuantity(variantId, -1));
        el.querySelector('.btn-qty-inc').addEventListener('click', () => cart.updateQuantity(variantId, 1));
        el.querySelector('.btn-remove-item').addEventListener('click', () => cart.removeItem(variantId));
      });
    }
  }

  cart.subscribe(render);

  function open() {
    backdrop.classList.add('is-open');
    drawer.classList.add('is-open');
    document.body.style.overflow = 'hidden';
    // Reconcile with API in background when drawer is opened
    cart.reconcileWithApi();
  }

  function close() {
    backdrop.classList.remove('is-open');
    drawer.classList.remove('is-open');
    document.body.style.overflow = '';
  }

  backdrop.addEventListener('click', close);
  drawer.querySelector('#cart-close-btn').addEventListener('click', close);

  drawer.querySelector('#btn-checkout').addEventListener('click', () => {
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
