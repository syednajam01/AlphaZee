import { createBrandLogo } from './BrandLogo.js';
import { cart } from '../utils/cart.js';
import { storeConfig } from '../data/store-config.js';
import { formatPkr } from '../utils/money.js';
import { escapeHtml } from '../utils/dom.js';
import { submitOrder, uploadReceipt, validateCoupon, ApiError } from '../utils/api.js';
import { getStoredUtmParams } from '../utils/utm.js';

export function createCheckoutView(onClose) {
  const modal = document.createElement('div');
  modal.className = 'modal-container';
  modal.id = 'checkout-modal';
  modal.setAttribute('role', 'dialog');
  modal.setAttribute('aria-modal', 'true');
  modal.setAttribute('aria-label', 'AlphaZee Store Checkout');

  modal.innerHTML = `
    <div class="drawer-backdrop is-open" style="z-index: 1;"></div>
    <div class="modal-content" style="z-index: 2; max-width: 680px; padding: 0; overflow: hidden;">
      <!-- Checkout Header -->
      <div class="checkout-header" style="display: flex; align-items: center; justify-content: space-between; padding: 16px 24px; border-bottom: 1px solid var(--color-border); background: var(--color-surface);">
        <div id="checkout-logo-slot"></div>
        <div style="display: flex; align-items: center; gap: 12px;">
          <span class="badge badge-accent" id="checkout-badge" style="font-weight: 600;">
            Secure Checkout
          </span>
          <button class="btn-icon" id="checkout-close-btn" aria-label="Return to store">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
      </div>

      <!-- Checkout Body Container -->
      <div id="checkout-body-content" style="padding: 24px; max-height: 75vh; overflow-y: auto;">
        <!-- Error Banner Container -->
        <div id="checkout-error-banner" style="display: none; padding: 12px 16px; background-color: #FEF2F2; border: 1px solid #FCA5A5; border-left: 4px solid #DC2626; border-radius: var(--radius-sm); margin-bottom: 20px; font-size: 0.875rem; color: #991B1B;">
        </div>

        <h2 style="font-size: 1.125rem; font-weight: 700; margin-bottom: 14px;">Order Summary</h2>
        <div id="checkout-items-list" style="margin-bottom: 20px;"></div>

        <!-- Promo Code Box -->
        <div style="margin-bottom: 20px; padding: 14px; background: #F8FAFC; border: 1px dashed var(--color-border); border-radius: var(--radius-btn);">
          <label for="input-promo-code" style="font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; display: block; margin-bottom: 6px; color: var(--color-text-muted);">
            Have a Promo / Voucher Code?
          </label>
          <div style="display: flex; gap: 8px;">
            <input type="text" id="input-promo-code" placeholder="e.g. LAUNCH10" style="flex: 1; padding: 8px 12px; text-transform: uppercase; font-weight: 600; border: 1px solid var(--color-border); border-radius: var(--radius-btn); font-size: 0.875rem;" />
            <button type="button" id="btn-apply-coupon" class="btn btn-secondary" style="padding: 8px 16px; font-size: 0.8125rem; font-weight: 600;">
              Apply
            </button>
          </div>
          <div id="coupon-feedback-msg" style="display: none; font-size: 0.75rem; margin-top: 6px; font-weight: 600;"></div>
        </div>

        <h2 style="font-size: 1.125rem; font-weight: 700; margin-bottom: 14px;">Shipping & Contact Information</h2>
        <form id="checkout-form" style="display: flex; flex-direction: column; gap: 14px;">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
            <div>
              <label for="input-customer-name" style="font-size: 0.75rem; font-weight: 600; display: block; margin-bottom: 4px;">Full Name *</label>
              <input type="text" id="input-customer-name" required placeholder="Zainab Ahmed" style="width: 100%; padding: 10px 14px; border: 1px solid var(--color-border); border-radius: var(--radius-btn); font-size: 0.875rem;" />
            </div>
            <div>
              <label for="input-customer-phone" style="font-size: 0.75rem; font-weight: 600; display: block; margin-bottom: 4px;">Pakistan Mobile Number *</label>
              <input type="tel" id="input-customer-phone" required placeholder="0300-1234567" style="width: 100%; padding: 10px 14px; border: 1px solid var(--color-border); border-radius: var(--radius-btn); font-size: 0.875rem;" />
            </div>
          </div>

          <div>
            <label for="input-customer-email" style="font-size: 0.75rem; font-weight: 600; display: block; margin-bottom: 4px;">Email Address (Optional)</label>
            <input type="email" id="input-customer-email" placeholder="zainab@example.com" style="width: 100%; padding: 10px 14px; border: 1px solid var(--color-border); border-radius: var(--radius-btn); font-size: 0.875rem;" />
          </div>

          <div>
            <label for="input-shipping-address-1" style="font-size: 0.75rem; font-weight: 600; display: block; margin-bottom: 4px;">Delivery Address *</label>
            <input type="text" id="input-shipping-address-1" required placeholder="House / Apartment #, Street address" style="width: 100%; padding: 10px 14px; border: 1px solid var(--color-border); border-radius: var(--radius-btn); font-size: 0.875rem;" />
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px;">
            <div>
              <label for="input-shipping-city" style="font-size: 0.75rem; font-weight: 600; display: block; margin-bottom: 4px;">City *</label>
              <input type="text" id="input-shipping-city" required placeholder="Karachi" style="width: 100%; padding: 10px 14px; border: 1px solid var(--color-border); border-radius: var(--radius-btn); font-size: 0.875rem;" />
            </div>
            <div>
              <label for="input-shipping-province" style="font-size: 0.75rem; font-weight: 600; display: block; margin-bottom: 4px;">Province *</label>
              <input type="text" id="input-shipping-province" required placeholder="Sindh" style="width: 100%; padding: 10px 14px; border: 1px solid var(--color-border); border-radius: var(--radius-btn); font-size: 0.875rem;" />
            </div>
            <div>
              <label for="input-shipping-postal" style="font-size: 0.75rem; font-weight: 600; display: block; margin-bottom: 4px;">Postal Code</label>
              <input type="text" id="input-shipping-postal" placeholder="75600" style="width: 100%; padding: 10px 14px; border: 1px solid var(--color-border); border-radius: var(--radius-btn); font-size: 0.875rem;" />
            </div>
          </div>

          <div>
            <label for="input-customer-notes" style="font-size: 0.75rem; font-weight: 600; display: block; margin-bottom: 4px;">Special Delivery Instructions (Optional)</label>
            <textarea id="input-customer-notes" rows="2" placeholder="e.g. Please deliver between 2 PM and 6 PM" style="width: 100%; padding: 10px 14px; border: 1px solid var(--color-border); border-radius: var(--radius-btn); font-size: 0.875rem; resize: vertical;"></textarea>
          </div>

          <!-- Payment Method Selection -->
          <div style="margin-top: 6px;">
            <label style="font-size: 0.75rem; font-weight: 600; display: block; margin-bottom: 6px;">Select Payment Method *</label>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
              <label id="label-method-cod" style="padding: 12px; border: 2px solid var(--color-accent); border-radius: var(--radius-btn); background: rgba(20, 92, 68, 0.05); font-size: 0.8125rem; cursor: pointer; display: flex; align-items: flex-start; gap: 8px;">
                <input type="radio" name="payment_method" value="cod" checked style="margin-top: 2px;" />
                <div>
                  <strong>Cash on Delivery (COD)</strong>
                  <div style="font-size: 0.7rem; color: var(--color-text-muted);">Pay in cash when order arrives</div>
                </div>
              </label>
              <label id="label-method-bank" style="padding: 12px; border: 2px solid var(--color-border); border-radius: var(--radius-btn); background: #FAFAFA; font-size: 0.8125rem; cursor: pointer; display: flex; align-items: flex-start; gap: 8px;">
                <input type="radio" name="payment_method" value="bank_transfer" style="margin-top: 2px;" />
                <div>
                  <strong>Bank Transfer</strong>
                  <div style="font-size: 0.7rem; color: var(--color-text-muted);">Meezan Bank (Verified prior to dispatch)</div>
                </div>
              </label>
            </div>
          </div>

          <div style="padding: 16px; background-color: var(--color-bg); border-radius: var(--radius-btn); margin-top: 8px;">
            <div style="display: flex; justify-content: space-between; font-size: 0.875rem; margin-bottom: 6px;">
              <span>Subtotal</span>
              <span id="checkout-subtotal" style="font-weight: 600;">PKR 0</span>
            </div>
            <div id="checkout-discount-row" style="display: none; justify-content: space-between; font-size: 0.875rem; margin-bottom: 6px; color: var(--color-accent); font-weight: 600;">
              <span id="checkout-discount-label">Promotional Discount</span>
              <span id="checkout-discount-amount">- PKR 0</span>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 0.875rem; margin-bottom: 8px; color: var(--color-text-muted);">
              <span>Estimated Delivery (${escapeHtml(storeConfig.shippingInfo.standardTime)})</span>
              <span id="checkout-shipping-label" style="font-weight: 500; color: var(--color-accent);">Free Delivery</span>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 1rem; font-weight: 700; border-top: 1px solid var(--color-border); padding-top: 8px;">
              <span>Total Payable</span>
              <span id="checkout-total">PKR 0</span>
            </div>
          </div>

          <button 
            type="submit" 
            class="btn btn-primary" 
            id="btn-place-order" 
            style="width: 100%; min-height: 48px; margin-top: 8px; font-weight: 600;">
            Place Order
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

  // Active coupon state
  let appliedCoupon = null;

  // Handle radio styling toggle
  const form = modal.querySelector('#checkout-form');
  const radCod = modal.querySelector('input[value="cod"]');
  const radBank = modal.querySelector('input[value="bank_transfer"]');
  const labelCod = modal.querySelector('#label-method-cod');
  const labelBank = modal.querySelector('#label-method-bank');

  function updateRadioStyle() {
    if (radCod.checked) {
      labelCod.style.borderColor = 'var(--color-accent)';
      labelCod.style.background = 'rgba(20, 92, 68, 0.05)';
      labelBank.style.borderColor = 'var(--color-border)';
      labelBank.style.background = '#FAFAFA';
    } else {
      labelBank.style.borderColor = 'var(--color-accent)';
      labelBank.style.background = 'rgba(20, 92, 68, 0.05)';
      labelCod.style.borderColor = 'var(--color-border)';
      labelCod.style.background = '#FAFAFA';
    }
  }

  radCod.addEventListener('change', updateRadioStyle);
  radBank.addEventListener('change', updateRadioStyle);

  function calculateTotals(subtotalMinor) {
    let discountMinor = 0;
    if (appliedCoupon) {
      discountMinor = appliedCoupon.discount_amount?.minor || 0;
    }
    const payableMinor = Math.max(0, subtotalMinor - discountMinor);
    return {
      subtotalFormatted: formatPkr(subtotalMinor),
      discountFormatted: formatPkr(discountMinor),
      payableFormatted: formatPkr(payableMinor),
      discountMinor,
    };
  }

  function renderCartState(state) {
    const itemsList = modal.querySelector('#checkout-items-list');
    const subtotalEl = modal.querySelector('#checkout-subtotal');
    const totalEl = modal.querySelector('#checkout-total');
    const discountRow = modal.querySelector('#checkout-discount-row');
    const discountAmountEl = modal.querySelector('#checkout-discount-amount');
    const discountLabelEl = modal.querySelector('#checkout-discount-label');
    const placeBtn = modal.querySelector('#btn-place-order');

    const rawSubtotalMinor = state.items.reduce((acc, it) => acc + (it.price_minor * it.quantity), 0);
    const totals = calculateTotals(rawSubtotalMinor);

    if (subtotalEl && totalEl) {
      subtotalEl.textContent = totals.subtotalFormatted;
      totalEl.textContent = totals.payableFormatted;
    }

    if (discountRow && discountAmountEl) {
      if (totals.discountMinor > 0) {
        discountRow.style.display = 'flex';
        discountLabelEl.textContent = `Promo Code (${appliedCoupon.code})`;
        discountAmountEl.textContent = `- ${totals.discountFormatted}`;
      } else {
        discountRow.style.display = 'none';
      }
    }

    if (!itemsList) return;

    if (state.items.length === 0) {
      itemsList.innerHTML = '<p style="color: var(--color-text-muted); font-size: 0.875rem;">Your cart is empty.</p>';
      if (placeBtn) {
        placeBtn.disabled = true;
        placeBtn.style.opacity = '0.6';
      }
    } else {
      if (placeBtn) {
        placeBtn.disabled = false;
        placeBtn.style.opacity = '1';
      }
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

  cart.subscribe(renderCartState);

  // Coupon apply button handler
  const btnApplyCoupon = modal.querySelector('#btn-apply-coupon');
  const promoInput = modal.querySelector('#input-promo-code');
  const couponFeedback = modal.querySelector('#coupon-feedback-msg');

  btnApplyCoupon?.addEventListener('click', async () => {
    const code = promoInput.value.trim();
    if (!code) return;

    const cartState = cart.getState();
    const rawSubtotalMinor = cartState.items.reduce((acc, it) => acc + (it.price_minor * it.quantity), 0);

    btnApplyCoupon.disabled = true;
    btnApplyCoupon.textContent = 'Checking...';
    couponFeedback.style.display = 'none';

    try {
      const res = await validateCoupon(code, rawSubtotalMinor, 0);
      appliedCoupon = res;
      couponFeedback.style.color = '#15803D';
      couponFeedback.textContent = `✓ ${res.message} (${res.discount_amount.formatted} off)`;
      couponFeedback.style.display = 'block';
      renderCartState(cart.getState());
    } catch (err) {
      appliedCoupon = null;
      couponFeedback.style.color = '#DC2626';
      couponFeedback.textContent = err.message || 'Invalid coupon code.';
      couponFeedback.style.display = 'block';
      renderCartState(cart.getState());
    } finally {
      btnApplyCoupon.disabled = false;
      btnApplyCoupon.textContent = 'Apply';
    }
  });

  // Form submit handler
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const errorBanner = modal.querySelector('#checkout-error-banner');
    const placeBtn = modal.querySelector('#btn-place-order');
    errorBanner.style.display = 'none';

    const cartState = cart.getState();
    if (cartState.items.length === 0) {
      errorBanner.textContent = 'Your cart is empty. Please add items before placing an order.';
      errorBanner.style.display = 'block';
      return;
    }

    const customerName = modal.querySelector('#input-customer-name').value.trim();
    const customerPhone = modal.querySelector('#input-customer-phone').value.trim();
    const customerEmail = modal.querySelector('#input-customer-email').value.trim() || null;
    const address1 = modal.querySelector('#input-shipping-address-1').value.trim();
    const city = modal.querySelector('#input-shipping-city').value.trim();
    const province = modal.querySelector('#input-shipping-province').value.trim();
    const postal = modal.querySelector('#input-shipping-postal').value.trim() || null;
    const notes = modal.querySelector('#input-customer-notes').value.trim() || null;
    const paymentMethod = modal.querySelector('input[name="payment_method"]:checked')?.value || 'cod';

    const itemsPayload = cartState.items.map(i => ({
      variant_id: i.id || i.variant_id,
      quantity: i.quantity,
    }));

    // Capture marketing attribution
    const utm = getStoredUtmParams();

    const orderPayload = {
      customer_name: customerName,
      customer_phone: customerPhone,
      customer_email: customerEmail,
      shipping_address_line1: address1,
      shipping_city: city,
      shipping_province: province,
      shipping_postal_code: postal,
      payment_method: paymentMethod,
      coupon_code: appliedCoupon ? appliedCoupon.code : null,
      utm_source: utm.utm_source,
      utm_medium: utm.utm_medium,
      utm_campaign: utm.utm_campaign,
      customer_notes: notes,
      items: itemsPayload,
    };

    placeBtn.disabled = true;
    placeBtn.textContent = 'Processing Order...';

    try {
      const order = await submitOrder(orderPayload);
      // Clear shopping cart on confirmed order placement
      cart.clear();
      appliedCoupon = null;
      renderOrderConfirmation(order);
    } catch (err) {
      placeBtn.disabled = false;
      placeBtn.textContent = 'Place Order';
      errorBanner.textContent = err.message || 'Failed to place order. Please check your details and try again.';
      errorBanner.style.display = 'block';
    }
  });

  function renderOrderConfirmation(order) {
    const bodyContent = modal.querySelector('#checkout-body-content');
    const badge = modal.querySelector('#checkout-badge');
    if (badge) {
      badge.textContent = 'Order Confirmed';
      badge.className = 'badge badge-accent';
    }

    const isBank = order.payment_method === 'bank_transfer';
    const bankHtml = isBank ? `
      <div style="background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: var(--radius-sm); padding: 16px; margin: 20px 0;">
        <h3 style="font-size: 0.9375rem; font-weight: 700; color: #166534; margin-bottom: 8px;">
          Bank Transfer Payment Instructions
        </h3>
        <p style="font-size: 0.8125rem; color: #15803D; margin-bottom: 12px; line-height: 1.5;">
          Please transfer <strong>${order.total.formatted}</strong> to the official AlphaZee account below. Your payment will be verified by the owner before dispatch.
        </p>
        <div style="font-size: 0.8125rem; font-family: monospace; background: #FFFFFF; border: 1px solid #DCFCE7; border-radius: var(--radius-sm); padding: 12px; line-height: 1.6; color: #14532D;">
          <div><strong>Bank:</strong> ${escapeHtml(order.bank_instructions?.bank_name || 'Meezan Bank Ltd.')}</div>
          <div><strong>Title:</strong> ${escapeHtml(order.bank_instructions?.account_title || 'AlphaZee Private Limited')}</div>
          <div><strong>Account #:</strong> ${escapeHtml(order.bank_instructions?.account_number || '01020304050607')}</div>
          <div><strong>IBAN:</strong> ${escapeHtml(order.bank_instructions?.iban || 'PK00MEZN0001020304050607')}</div>
        </div>

        <div style="margin-top: 16px;">
          <h4 style="font-size: 0.8125rem; font-weight: 700; color: #166534; margin-bottom: 6px;">
            Upload Proof of Payment (Receipt Screenshot)
          </h4>
          <form id="receipt-upload-form" style="display: flex; flex-direction: column; gap: 8px;">
            <input type="url" id="receipt-url-input" required placeholder="https://storage.alphazee.pk/receipts/proof.png" style="width: 100%; padding: 8px 12px; border: 1px solid #86EFAC; border-radius: var(--radius-btn); font-size: 0.8125rem;" />
            <input type="text" id="receipt-ref-input" placeholder="Bank Transaction Reference / ID (Optional)" style="width: 100%; padding: 8px 12px; border: 1px solid #86EFAC; border-radius: var(--radius-btn); font-size: 0.8125rem;" />
            <button type="submit" id="btn-upload-receipt" class="btn btn-primary" style="align-self: flex-start; padding: 8px 16px; font-size: 0.8125rem;">
              Submit Receipt Proof
            </button>
            <div id="receipt-status-msg" style="display: none; font-size: 0.75rem; font-weight: 600; margin-top: 4px;"></div>
          </form>
        </div>
      </div>
    ` : `
      <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: var(--radius-sm); padding: 16px; margin: 20px 0; font-size: 0.875rem;">
        <strong>Cash on Delivery (COD)</strong>
        <p style="color: var(--color-text-muted); font-size: 0.8125rem; margin: 4px 0 0 0;">
          Please keep exact cash ready (${order.total.formatted}) for payment upon courier delivery.
        </p>
      </div>
    `;

    const linesHtml = order.lines.map(line => `
      <div style="display: flex; justify-content: space-between; font-size: 0.875rem; padding: 6px 0;">
        <span>${escapeHtml(line.product_title)} (${escapeHtml(line.size || '')} ${escapeHtml(line.color || '')}) × ${line.quantity}</span>
        <span style="font-weight: 600;">${line.line_total.formatted}</span>
      </div>
    `).join('');

    const discountHtml = order.discount_amount && order.discount_amount.minor > 0 ? `
      <div style="display: flex; justify-content: space-between; font-size: 0.875rem; padding: 4px 0; color: var(--color-accent); font-weight: 600;">
        <span>Discount (${escapeHtml(order.coupon_code || 'Promo')})</span>
        <span>- ${order.discount_amount.formatted}</span>
      </div>
    ` : '';

    bodyContent.innerHTML = `
      <div style="text-align: center; padding: 12px 0 20px 0;">
        <div style="width: 56px; height: 56px; border-radius: 50%; background: rgba(20, 92, 68, 0.1); color: var(--color-accent); display: flex; align-items: center; justify-content: center; margin: 0 auto 12px auto;">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
        </div>
        <h2 style="font-size: 1.375rem; font-weight: 800; margin-bottom: 4px;">Thank You for Your Order!</h2>
        <div style="font-size: 0.9375rem; font-weight: 600; color: var(--color-accent); letter-spacing: 0.5px;">
          Order #${escapeHtml(order.order_number)}
        </div>
        <p style="font-size: 0.8125rem; color: var(--color-text-muted); margin-top: 4px;">
          A confirmation has been recorded for <strong>${escapeHtml(order.customer_phone)}</strong>.
        </p>
      </div>

      <div style="background: var(--color-bg); border-radius: var(--radius-btn); padding: 16px;">
        <div style="font-size: 0.8125rem; font-weight: 700; text-transform: uppercase; color: var(--color-text-muted); margin-bottom: 8px;">Order Details</div>
        ${linesHtml}
        ${discountHtml}
        <div style="display: flex; justify-content: space-between; font-size: 1rem; font-weight: 700; border-top: 1px solid var(--color-border); padding-top: 10px; margin-top: 10px;">
          <span>Total Amount</span>
          <span>${order.total.formatted}</span>
        </div>
      </div>

      ${bankHtml}

      <div style="text-align: center; margin-top: 24px;">
        <button type="button" class="btn btn-secondary" id="btn-finish-checkout" style="min-width: 180px;">
          Continue Shopping
        </button>
      </div>
    `;

    modal.querySelector('#btn-finish-checkout')?.addEventListener('click', close);

    // If Bank Transfer, wire receipt upload handler
    if (isBank) {
      const receiptForm = modal.querySelector('#receipt-upload-form');
      const receiptBtn = modal.querySelector('#btn-upload-receipt');
      const statusMsg = modal.querySelector('#receipt-status-msg');

      receiptForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const imageUrl = modal.querySelector('#receipt-url-input').value.trim();
        const ref = modal.querySelector('#receipt-ref-input').value.trim() || null;

        receiptBtn.disabled = true;
        receiptBtn.textContent = 'Uploading...';
        statusMsg.style.display = 'none';

        try {
          await uploadReceipt(order.order_number, {
            customer_phone: order.customer_phone,
            receipt_image_url: imageUrl,
            bank_reference: ref,
          });
          statusMsg.style.color = '#15803D';
          statusMsg.textContent = 'Receipt uploaded successfully! Owner will verify funds before dispatch.';
          statusMsg.style.display = 'block';
          receiptBtn.textContent = 'Uploaded';
        } catch (uploadErr) {
          receiptBtn.disabled = false;
          receiptBtn.textContent = 'Submit Receipt Proof';
          statusMsg.style.color = '#DC2626';
          statusMsg.textContent = uploadErr.message || 'Failed to submit receipt.';
          statusMsg.style.display = 'block';
        }
      });
    }
  }

  function open() {
    modal.classList.add('is-open');
    document.body.style.overflow = 'hidden';
    renderCartState(cart.getState());
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
