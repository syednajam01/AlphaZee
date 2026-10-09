import { createBrandLogo } from './BrandLogo.js';
import { cart } from '../utils/cart.js';
import { storeConfig } from '../data/store-config.js';
import { formatPkr } from '../utils/money.js';
import { escapeHtml } from '../utils/dom.js';

export function createCheckoutView(onClose) {
  const modal = document.createElement('div');
  modal.className = 'modal-container';
  modal.id = 'checkout-modal';
  modal.setAttribute('role', 'dialog');
  modal.setAttribute('aria-modal', 'true');
  modal.setAttribute('aria-label', 'AlphaZee Checkout Preview');

  modal.innerHTML = `
    <div class="drawer-backdrop is-open" style="z-index: 1;"></div>
    <div class="modal-content" style="z-index: 2; max-width: 680px; padding: 0; overflow: hidden;">
      <!-- Checkout Header -->
      <div class="checkout-header" style="display: flex; align-items: center; justify-content: space-between; padding: 16px 24px; border-bottom: 1px solid var(--color-border); background: var(--color-surface);">
        <div id="checkout-logo-slot"></div>
        <div style="display: flex; align-items: center; gap: 12px;">
          <span class="badge badge-neutral" style="font-weight: 600;">
            Preview Mode
          </span>
          <button class="btn-icon" id="checkout-close-btn" aria-label="Return to store">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
      </div>

      <!-- Checkout Body -->
      <div style="padding: 24px; max-height: 75vh; overflow-y: auto;">
        <!-- Prototype Notice Banner -->
        <div style="padding: 14px 16px; background-color: #F8F9FA; border: 1px solid var(--color-border); border-left: 4px solid var(--color-accent); border-radius: var(--radius-sm); margin-bottom: 20px;">
          <div style="font-size: 0.875rem; font-weight: 700; color: var(--color-text); margin-bottom: 4px;">
            Catalog Preview Notice
          </div>
          <p style="font-size: 0.8125rem; color: var(--color-text-muted); line-height: 1.5; margin: 0;">
            Checkout is currently in preview mode while backend database schemas and order operations are being finalized. Real order submission is disabled; your cart contents remain saved.
          </p>
        </div>

        <h2 style="font-size: 1.125rem; font-weight: 700; margin-bottom: 14px;">Order Summary</h2>
        <div id="checkout-items-list" style="margin-bottom: 20px;"></div>

        <h2 style="font-size: 1.125rem; font-weight: 700; margin-bottom: 14px;">Shipping & Payment (Preview)</h2>
        <form id="checkout-form" style="display: flex; flex-direction: column; gap: 14px;" onsubmit="event.preventDefault();">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
            <div>
              <label style="font-size: 0.75rem; font-weight: 600; display: block; margin-bottom: 4px;">Recipient Name</label>
              <input type="text" placeholder="Syed Ali" disabled style="width: 100%; padding: 10px 14px; border: 1px solid var(--color-border); border-radius: var(--radius-btn); font-size: 0.875rem; background: #FAFAFA;" />
            </div>
            <div>
              <label style="font-size: 0.75rem; font-weight: 600; display: block; margin-bottom: 4px;">Phone Number (for COD)</label>
              <input type="tel" placeholder="0300 1234567" disabled style="width: 100%; padding: 10px 14px; border: 1px solid var(--color-border); border-radius: var(--radius-btn); font-size: 0.875rem; background: #FAFAFA;" />
            </div>
          </div>

          <div>
            <label style="font-size: 0.75rem; font-weight: 600; display: block; margin-bottom: 4px;">Delivery Address</label>
            <input type="text" placeholder="Street address, City" disabled style="width: 100%; padding: 10px 14px; border: 1px solid var(--color-border); border-radius: var(--radius-btn); font-size: 0.875rem; background: #FAFAFA;" />
          </div>

          <!-- Planned Payment Methods -->
          <div style="margin-top: 6px;">
            <label style="font-size: 0.75rem; font-weight: 600; display: block; margin-bottom: 6px;">Planned Launch Payment Options</label>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
              <div style="padding: 10px 12px; border: 1px solid var(--color-accent); border-radius: var(--radius-btn); background: rgba(20, 92, 68, 0.05); font-size: 0.8125rem;">
                <strong>Cash on Delivery (COD)</strong>
                <div style="font-size: 0.7rem; color: var(--color-text-muted);">Pay upon delivery across Pakistan</div>
              </div>
              <div style="padding: 10px 12px; border: 1px solid var(--color-border); border-radius: var(--radius-btn); background: #FAFAFA; font-size: 0.8125rem;">
                <strong>Bank Transfer</strong>
                <div style="font-size: 0.7rem; color: var(--color-text-muted);">Verified prior to order dispatch</div>
              </div>
            </div>
          </div>

          <div style="padding: 16px; background-color: var(--color-bg); border-radius: var(--radius-btn); margin-top: 8px;">
            <div style="display: flex; justify-content: space-between; font-size: 0.875rem; margin-bottom: 6px;">
              <span>Subtotal</span>
              <span id="checkout-subtotal" style="font-weight: 600;">PKR 0</span>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 0.875rem; margin-bottom: 8px; color: var(--color-text-muted);">
              <span>Estimated Delivery (${escapeHtml(storeConfig.shippingInfo.standardTime)})</span>
              <span>Calculated at checkout</span>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 1rem; font-weight: 700; border-top: 1px solid var(--color-border); padding-top: 8px;">
              <span>Total Payable</span>
              <span id="checkout-total">PKR 0</span>
            </div>
          </div>

          <button 
            type="button" 
            class="btn btn-secondary" 
            id="btn-place-order" 
            disabled 
            style="width: 100%; min-height: 48px; margin-top: 8px; opacity: 0.7; cursor: not-allowed;">
            Order Submission Disabled (Launch Preview)
          </button>
        </form>
      </div>
    </div>
  `;

  // Mount Wordmark in Checkout Header
  const logoSlot = modal.querySelector('#checkout-logo-slot');
  if (logoSlot) {
    const wordmarkLogo = createBrandLogo({
      variant: 'wordmark',
      surface: 'light',
      width: 120,
      ariaLabel: 'AlphaZee home',
    });
    logoSlot.appendChild(wordmarkLogo);
  }

  function render(state) {
    const itemsList = modal.querySelector('#checkout-items-list');
    const subtotalEl = modal.querySelector('#checkout-subtotal');
    const totalEl = modal.querySelector('#checkout-total');

    subtotalEl.textContent = state.formattedTotal;
    totalEl.textContent = state.formattedTotal;

    if (state.items.length === 0) {
      itemsList.innerHTML = '<p style="color: var(--color-text-muted); font-size: 0.875rem;">Your cart is empty.</p>';
    } else {
      itemsList.innerHTML = state.items.map(item => {
        const itemTotal = formatPkr(item.price_minor * item.quantity);
        const metaParts = [];
        if (item.size) metaParts.push(`Size: ${escapeHtml(item.size)}`);
        if (item.color) metaParts.push(`Color: ${escapeHtml(item.color)}`);

        return `
          <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.875rem; padding: 8px 0; border-bottom: 1px solid var(--color-border-subtle);">
            <div>
              <strong>${escapeHtml(item.title)}</strong> × ${item.quantity}
              <div style="font-size: 0.75rem; color: var(--color-text-muted);">
                ${metaParts.join(' • ')}
              </div>
            </div>
            <div style="font-weight: 600;">${itemTotal}</div>
          </div>
        `;
      }).join('');
    }
  }

  cart.subscribe(render);

  function open() {
    modal.classList.add('is-open');
    document.body.style.overflow = 'hidden';
  }

  function close() {
    modal.classList.remove('is-open');
    document.body.style.overflow = '';
    if (onClose) onClose();
  }

  modal.querySelector('.drawer-backdrop').addEventListener('click', close);
  modal.querySelector('#checkout-close-btn').addEventListener('click', close);

  return {
    element: modal,
    open,
    close
  };
}
