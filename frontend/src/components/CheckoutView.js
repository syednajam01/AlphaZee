import { createBrandLogo } from './BrandLogo.js';
import { cart } from '../utils/cart.js';
import { storeConfig } from '../data/store-config.js';

export function createCheckoutView(onClose) {
  const modal = document.createElement('div');
  modal.className = 'modal-container';
  modal.id = 'checkout-modal';
  modal.setAttribute('role', 'dialog');
  modal.setAttribute('aria-modal', 'true');
  modal.setAttribute('aria-label', 'AlphaZee Checkout');

  modal.innerHTML = `
    <div class="drawer-backdrop is-open" style="z-index: 1;"></div>
    <div class="modal-content" style="z-index: 2; max-width: 680px; padding: 0; overflow: hidden;">
      <!-- Checkout Header: Wordmark with minimal navigation -->
      <div class="checkout-header" style="display: flex; align-items: center; justify-content: space-between; padding: 16px 24px; border-bottom: 1px solid var(--color-border); background: var(--color-surface);">
        <div id="checkout-logo-slot"></div>
        <div style="display: flex; align-items: center; gap: 12px;">
          <span style="font-size: 0.75rem; color: #137333; font-weight: 600; display: flex; align-items: center; gap: 4px;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
              <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
            </svg>
            Encrypted 256-bit Checkout
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
        <h2 style="font-size: 1.25rem; font-weight: 700; margin-bottom: 16px;">Order Summary & Customer Details</h2>
        
        <div id="checkout-items-list" style="margin-bottom: 20px;"></div>

        <form id="checkout-form" style="display: flex; flex-direction: column; gap: 14px;" onsubmit="event.preventDefault();">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
            <div>
              <label style="font-size: 0.75rem; font-weight: 600; display: block; margin-bottom: 4px;">First Name</label>
              <input type="text" required placeholder="Syed" style="width: 100%; padding: 10px 14px; border: 1px solid var(--color-border); border-radius: var(--radius-btn); font-size: 0.875rem;" />
            </div>
            <div>
              <label style="font-size: 0.75rem; font-weight: 600; display: block; margin-bottom: 4px;">Last Name</label>
              <input type="text" required placeholder="Ali" style="width: 100%; padding: 10px 14px; border: 1px solid var(--color-border); border-radius: var(--radius-btn); font-size: 0.875rem;" />
            </div>
          </div>

          <div>
            <label style="font-size: 0.75rem; font-weight: 600; display: block; margin-bottom: 4px;">Shipping Address</label>
            <input type="text" required placeholder="Street address, Apartment / Suite" style="width: 100%; padding: 10px 14px; border: 1px solid var(--color-border); border-radius: var(--radius-btn); font-size: 0.875rem;" />
          </div>

          <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 12px;">
            <div>
              <label style="font-size: 0.75rem; font-weight: 600; display: block; margin-bottom: 4px;">City</label>
              <input type="text" required placeholder="Karachi / Lahore / Islamabad" style="width: 100%; padding: 10px 14px; border: 1px solid var(--color-border); border-radius: var(--radius-btn); font-size: 0.875rem;" />
            </div>
            <div>
              <label style="font-size: 0.75rem; font-weight: 600; display: block; margin-bottom: 4px;">Phone</label>
              <input type="tel" required placeholder="0300 1234567" style="width: 100%; padding: 10px 14px; border: 1px solid var(--color-border); border-radius: var(--radius-btn); font-size: 0.875rem;" />
            </div>
          </div>

          <div style="padding: 16px; background-color: var(--color-bg); border-radius: var(--radius-btn); margin-top: 8px;">
            <div style="display: flex; justify-content: space-between; font-size: 0.875rem; margin-bottom: 6px;">
              <span>Subtotal</span>
              <span id="checkout-subtotal" style="font-weight: 600;">PKR 0</span>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 0.875rem; margin-bottom: 8px; color: var(--color-text-muted);">
              <span>Shipping (${storeConfig.shippingInfo.standardTime})</span>
              <span>Calculated</span>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 1rem; font-weight: 700; border-top: 1px solid var(--color-border); padding-top: 8px;">
              <span>Total Payable</span>
              <span id="checkout-total">PKR 0</span>
            </div>
          </div>

          <button type="submit" class="btn btn-primary" id="btn-place-order" style="width: 100%; min-height: 48px; margin-top: 8px;">
            Confirm Order via WhatsApp / Transfer
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
      width: 120, // 110–135px
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
      itemsList.innerHTML = state.items.map(item => `
        <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.875rem; padding: 6px 0; border-bottom: 1px solid var(--color-border-subtle);">
          <div>
            <strong>${item.title}</strong> × ${item.quantity}
            <div style="font-size: 0.75rem; color: var(--color-text-muted);">
              ${item.options?.size ? `Size: ${item.options.size}` : ''}
              ${item.options?.color ? ` • ${item.options.color}` : ''}
            </div>
          </div>
          <div style="font-weight: 600;">PKR ${(item.price * item.quantity).toLocaleString()}</div>
        </div>
      `).join('');
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

  modal.querySelector('#checkout-form').addEventListener('submit', () => {
    alert('Thank you! Your AlphaZee order has been placed.');
    cart.clear();
    close();
  });

  return {
    element: modal,
    open,
    close
  };
}
