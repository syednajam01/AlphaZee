import { createOverlay } from '../utils/overlay.js';
import { createBrandLogo } from './BrandLogo.js';
import { cart } from '../utils/cart.js';
import { capabilities, CHECKOUT_UNAVAILABLE } from '../utils/capabilities.js';
import { storeConfig } from '../data/store-config.js';
import { formatPkr } from '../utils/money.js';
import { escapeHtml, createSafeImageElement } from '../utils/dom.js';
import { fetchCheckoutQuote, submitOrder, uploadReceipt, validateCoupon, recoverPendingOrder, getPendingCheckoutAttempt, ApiError } from '../utils/api.js';
import { getStoredUtmParams } from '../utils/utm.js';

export function createCheckoutView(onClose) {
  const modal = document.createElement('div');
  modal.className = 'modal-container';
  modal.id = 'checkout-modal';
  modal.setAttribute('role', 'dialog');
  modal.setAttribute('aria-modal', 'true');
  modal.setAttribute('aria-label', 'AlphaZee Store Checkout');

  modal.innerHTML = `
    <div class="drawer-backdrop" style="z-index: 1;"></div>
    <div class="modal-content checkout-modal-content" style="z-index: 2;">
      <!-- Checkout Header -->
      <div class="checkout-header">
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
      <div id="checkout-body-content" class="checkout-body">
        <!-- Error Banner Container -->
        <div id="checkout-error-banner" role="alert" aria-live="assertive" class="checkout-error-banner" style="display: none;"></div>

        <form id="checkout-form" class="checkout-layout-grid" novalidate>
          <!-- Left Column: Shipping & Payment (approx 58%) -->
          <div class="checkout-col-main">
            <section class="checkout-section">
              <h2 class="checkout-section-title">Shipping & Contact Information</h2>
              <p id="checkout-capability-message" role="status" class="checkout-capability-notice"></p>
              
              <div class="checkout-form-fields">
                <div class="form-row-2">
                  <div class="form-group" style="margin-bottom: 0;">
                    <label for="input-customer-name" class="form-label">Full Name <span class="required-star">*</span></label>
                    <input type="text" id="input-customer-name" name="name" autocomplete="name" required placeholder="Zainab Ahmed" class="form-input" />
                    <span id="error-customer-name" class="form-error" style="display: none;"></span>
                  </div>
                  <div class="form-group" style="margin-bottom: 0;">
                    <label for="input-customer-phone" class="form-label">Pakistan Mobile Number <span class="required-star">*</span></label>
                    <input type="tel" id="input-customer-phone" name="tel" autocomplete="tel" required placeholder="0300-1234567" class="form-input" />
                    <span id="error-customer-phone" class="form-error" style="display: none;"></span>
                  </div>
                </div>

                <div class="form-group" style="margin-bottom: 0;">
                  <label for="input-customer-email" class="form-label">Email Address <span class="form-label-optional">(Optional)</span></label>
                  <input type="email" id="input-customer-email" name="email" autocomplete="email" placeholder="zainab@example.com" class="form-input" />
                </div>

                <div class="form-group" style="margin-bottom: 0;">
                  <label for="input-shipping-address-1" class="form-label">Delivery Address <span class="required-star">*</span></label>
                  <input type="text" id="input-shipping-address-1" name="street-address" autocomplete="street-address" required placeholder="House / Apartment #, Street address" class="form-input" />
                  <span id="error-shipping-address-1" class="form-error" style="display: none;"></span>
                </div>

                <div class="form-row-3">
                  <div class="form-group" style="margin-bottom: 0;">
                    <label for="input-shipping-city" class="form-label">City <span class="required-star">*</span></label>
                    <input type="text" id="input-shipping-city" name="address-level2" autocomplete="address-level2" required placeholder="Karachi" class="form-input" />
                    <span id="error-shipping-city" class="form-error" style="display: none;"></span>
                  </div>
                  <div class="form-group" style="margin-bottom: 0;">
                    <label for="input-shipping-province" class="form-label">Province <span class="required-star">*</span></label>
                    <input type="text" id="input-shipping-province" name="address-level1" autocomplete="address-level1" required placeholder="Sindh" class="form-input" />
                    <span id="error-shipping-province" class="form-error" style="display: none;"></span>
                  </div>
                  <div class="form-group" style="margin-bottom: 0;">
                    <label for="input-shipping-postal" class="form-label">Postal Code <span class="form-label-optional">(Optional)</span></label>
                    <input type="text" id="input-shipping-postal" name="postal-code" autocomplete="postal-code" placeholder="75600" class="form-input" />
                  </div>
                </div>

                <div class="form-group" style="margin-bottom: 0;">
                  <label for="input-customer-notes" class="form-label">Special Delivery Instructions <span class="form-label-optional">(Optional)</span></label>
                  <textarea id="input-customer-notes" name="notes" rows="2" placeholder="e.g. Please deliver between 2 PM and 6 PM" class="form-textarea"></textarea>
                </div>
              </div>
            </section>

            <!-- Payment Method Selection -->
            <section class="checkout-section">
              <h2 class="checkout-section-title">Select Payment Method</h2>
              <div class="payment-methods-grid">
                <label id="label-method-cod" class="payment-method-card is-selected">
                  <input type="radio" name="payment_method" value="cod" checked class="payment-method-radio" />
                  <div class="payment-method-content">
                    <div class="payment-method-name">Cash on Delivery (COD)</div>
                    <div class="payment-method-desc">Pay with cash upon courier delivery. Please have exact cash ready.</div>
                  </div>
                </label>
                <label id="label-method-bank" class="payment-method-card">
                  <input type="radio" name="payment_method" value="bank_transfer" class="payment-method-radio" />
                  <div class="payment-method-content">
                    <div class="payment-method-name">Online Bank Transfer</div>
                    <div class="payment-method-desc">Official Meezan Bank account details sent after supplier confirmation. 4-hour window applies.</div>
                  </div>
                </label>
              </div>
            </section>
          </div>

          <!-- Right Column: Order Summary & Place Order (approx 42%) -->
          <div class="checkout-col-summary">
            <div class="checkout-summary-card">
              <h2 class="checkout-summary-title">Order Summary</h2>
              <div id="checkout-items-list" class="checkout-items-list"></div>
              <p id="checkout-catalog-status" role="status" aria-live="polite" style="font-size: 0.75rem; color: var(--color-text-muted); margin: 0;"></p>

              <!-- Promo Code Box -->
              <div class="checkout-promo-box">
                <label for="input-promo-code" class="checkout-promo-label">
                  Have a Promo / Voucher Code?
                </label>
                <div class="checkout-promo-input-row">
                  <input type="text" id="input-promo-code" placeholder="e.g. LAUNCH10" class="form-input checkout-promo-input" />
                  <button type="button" id="btn-apply-coupon" class="btn btn-secondary checkout-promo-btn">
                    Apply
                  </button>
                </div>
                <div id="coupon-feedback-msg" class="checkout-promo-feedback" style="display: none; font-size: 0.75rem; margin-top: 6px; font-weight: 600;"></div>
              </div>

              <!-- Price Breakdown -->
              <div class="checkout-totals-block">
                <div class="checkout-total-row">
                  <span>Subtotal</span>
                  <span id="checkout-subtotal" class="price-tabular font-medium">PKR 0</span>
                </div>
                <div id="checkout-discount-row" class="checkout-total-row checkout-discount-row" style="display: none;">
                  <span id="checkout-discount-label">Promotional Discount</span>
                  <span id="checkout-discount-amount" class="price-tabular font-medium">- PKR 0</span>
                </div>
                <div class="checkout-total-row">
                  <span>Estimated Delivery (${escapeHtml(storeConfig.shippingInfo.standardTime)})</span>
                  <span id="checkout-shipping-label" class="checkout-free-shipping">Calculated before confirmation</span>
                </div>
                <div class="checkout-total-row checkout-grand-total">
                  <span>Total Payable</span>
                  <span id="checkout-total" class="price-tabular">PKR 0</span>
                </div>
              </div>

              <button 
                type="submit" 
                class="btn btn-primary btn-place-order" 
                id="btn-place-order">
                Place Order
              </button>

              <div class="checkout-security-notes">
                <span>🔒 Direct Owner Verified Fulfillment</span>
                <span>${escapeHtml(storeConfig.shippingInfo.returnPolicy)}.</span>
              </div>
            </div>
          </div>
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
  let appliedCouponCartSignature = null;
  const cartSignature = state => JSON.stringify(state.items.map(item =>
    [item.id || item.variant_id, item.quantity, item.price_minor]));

  // Handle radio styling toggle
  const form = modal.querySelector('#checkout-form');
  const radCod = modal.querySelector('input[value="cod"]');
  const radBank = modal.querySelector('input[value="bank_transfer"]');
  const labelCod = modal.querySelector('#label-method-cod');
  const labelBank = modal.querySelector('#label-method-bank');

  function updateRadioStyle() {
    if (radCod.checked) {
      labelCod.classList.add('is-selected');
      labelBank.classList.remove('is-selected');
    } else {
      labelBank.classList.add('is-selected');
      labelCod.classList.remove('is-selected');
    }
  }

  radCod.addEventListener('change', updateRadioStyle);
  radBank.addEventListener('change', updateRadioStyle);

  // Field validation helpers
  function clearFieldError(input, errorId) {
    input.removeAttribute('aria-invalid');
    input.style.borderColor = '';
    const errEl = modal.querySelector(errorId);
    if (errEl) {
      errEl.textContent = '';
      errEl.style.display = 'none';
    }
  }

  ['#input-customer-name', '#input-customer-phone', '#input-shipping-address-1', '#input-shipping-city', '#input-shipping-province'].forEach(selector => {
    const el = modal.querySelector(selector);
    el?.addEventListener('input', () => {
      const errSelector = selector.replace('#input-', '#error-');
      clearFieldError(el, errSelector);
    });
  });

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
    if (appliedCoupon && appliedCouponCartSignature !== cartSignature(state)) {
      appliedCoupon = null;
      appliedCouponCartSignature = null;
      const feedback = modal.querySelector('#coupon-feedback-msg');
      if (feedback) {
        feedback.style.color = '#B45309';
        feedback.textContent = 'Cart changed. Apply the coupon again to verify its current discount.';
        feedback.style.display = 'block';
      }
    }
    const availability = capabilities.getState();
    const bankAvailable = availability.paymentMethods?.includes('bank_transfer') === true;
    labelBank.hidden = !bankAvailable;
    labelBank.style.display = bankAvailable ? 'flex' : 'none';
    radBank.disabled = !bankAvailable;
    if (!bankAvailable && radBank.checked) {
      radCod.checked = true;
      updateRadioStyle();
    }
    const capabilityMessage = modal.querySelector('#checkout-capability-message');
    if (capabilityMessage) capabilityMessage.textContent = availability.checkoutEnabled
      ? 'SAMPLE / TEST checkout. No real orders.' : CHECKOUT_UNAVAILABLE;
    const itemsList = modal.querySelector('#checkout-items-list');
    const subtotalEl = modal.querySelector('#checkout-subtotal');
    const totalEl = modal.querySelector('#checkout-total');
    const discountRow = modal.querySelector('#checkout-discount-row');
    const discountAmountEl = modal.querySelector('#checkout-discount-amount');
    const discountLabelEl = modal.querySelector('#checkout-discount-label');
    const placeBtn = modal.querySelector('#btn-place-order');
    const catalogStatus = modal.querySelector('#checkout-catalog-status');
    if (catalogStatus) catalogStatus.textContent = state.isReconciling ? 'Checking current catalog prices and availability…'
      : state.hasUnavailable ? 'Some items are unavailable or could not be verified. Review your cart before ordering.' : '';

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
        placeBtn.disabled = !availability.checkoutEnabled || state.isReconciling || state.hasUnavailable;
        placeBtn.style.opacity = '1';
      }
      itemsList.innerHTML = state.items.map(item => {
        const itemTotal = formatPkr(item.price_minor * item.quantity);
        const metaParts = [];
        if (item.size) metaParts.push(`Size: ${escapeHtml(item.size)}`);
        if (item.color) metaParts.push(`Color: ${escapeHtml(item.color)}`);

        return `
          <div class="checkout-item-row" data-variant-id="${item.variant_id}">
            <span data-checkout-media="${item.variant_id}"></span>
            <div class="checkout-item-details">
              <div class="checkout-item-title">${escapeHtml(item.title)} <span style="font-weight: 400; color: var(--color-text-muted);">× ${item.quantity}</span></div>
              <div class="checkout-item-meta">${metaParts.join(' • ')}</div>
            </div>
            <div class="checkout-item-line-total price-tabular">${itemTotal}</div>
          </div>
        `;
      }).join('');
      state.items.forEach(item => {
        const slot = itemsList.querySelector(`[data-checkout-media="${item.variant_id}"]`);
        if (slot) {
          slot.appendChild(
            createSafeImageElement({
              src: item.image_url,
              alt: item.title,
              className: 'checkout-item-image checkout-item-img',
              width: 48,
              height: 64,
            })
          );
        }
      });
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

    const errorBanner = modal.querySelector('#checkout-error-banner');
    const cartState = cart.getState();
    if (cartState.isReconciling || cartState.hasUnavailable) {
      errorBanner.textContent = 'Review your cart: prices and availability must be verified before ordering.';
      errorBanner.style.display = 'block';
      return;
    }
    const rawSubtotalMinor = cartState.items.reduce((acc, it) => acc + (it.price_minor * it.quantity), 0);

    btnApplyCoupon.disabled = true;
    btnApplyCoupon.textContent = 'Checking...';
    couponFeedback.style.display = 'none';

    try {
      const res = await validateCoupon(code, rawSubtotalMinor, 0);
      appliedCoupon = res;
      appliedCouponCartSignature = cartSignature(cartState);
      couponFeedback.style.color = '#15803D';
      couponFeedback.textContent = `✓ ${res.message} (${res.discount_amount.formatted} off)`;
      couponFeedback.style.display = 'block';
      renderCartState(cart.getState());
    } catch (err) {
      appliedCoupon = null;
      appliedCouponCartSignature = null;
      couponFeedback.style.color = '#DC2626';
      couponFeedback.textContent = err.message || 'Invalid coupon code.';
      couponFeedback.style.display = 'block';
      renderCartState(cart.getState());
    } finally {
      btnApplyCoupon.disabled = false;
      btnApplyCoupon.textContent = 'Apply';
    }
  });

  let confirmedQuote = null;
  // Form submit handler with inline field-level validation
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (recovering) return;
    const errorBanner = modal.querySelector('#checkout-error-banner');
    const placeBtn = modal.querySelector('#btn-place-order');
    errorBanner.style.display = 'none';

    if (!capabilities.getState().checkoutEnabled) {
      errorBanner.textContent = CHECKOUT_UNAVAILABLE;
      errorBanner.style.display = 'block';
      return;
    }

    const cartState = cart.getState();
    if (cartState.items.length === 0) {
      errorBanner.textContent = 'Your cart is empty. Please add items before placing an order.';
      errorBanner.style.display = 'block';
      return;
    }

    // Inline field validation
    const nameInput = modal.querySelector('#input-customer-name');
    const phoneInput = modal.querySelector('#input-customer-phone');
    const addressInput = modal.querySelector('#input-shipping-address-1');
    const cityInput = modal.querySelector('#input-shipping-city');
    const provinceInput = modal.querySelector('#input-shipping-province');

    const customerName = (nameInput.value || '').trim();
    const customerPhone = (phoneInput.value || '').trim();
    const customerEmail = (modal.querySelector('#input-customer-email')?.value || '').trim() || null;
    const address1 = (addressInput.value || '').trim();
    const city = (cityInput.value || '').trim();
    const province = (provinceInput.value || '').trim();
    const postal = (modal.querySelector('#input-shipping-postal')?.value || '').trim() || null;
    const notes = (modal.querySelector('#input-customer-notes')?.value || '').trim() || null;
    const paymentMethod = modal.querySelector('input[name="payment_method"]:checked')?.value || 'cod';

    let hasValidationError = false;
    let firstInvalidField = null;

    function setFieldError(input, errorId, message) {
      input.setAttribute('aria-invalid', 'true');
      input.style.borderColor = 'var(--color-error)';
      const errEl = modal.querySelector(errorId);
      if (errEl) {
        errEl.textContent = message;
        errEl.style.display = 'block';
      }
      hasValidationError = true;
      if (!firstInvalidField) firstInvalidField = input;
    }

    // Validate name
    if (!customerName || customerName.length < 2) {
      setFieldError(nameInput, '#error-customer-name', 'Please enter your full name.');
    } else {
      clearFieldError(nameInput, '#error-customer-name');
    }

    // Validate phone: Pakistan pattern
    const pkPhoneRegex = /^((\+92)|(0092)|(92)|(0))?3[0-9]{2}[-\s]?[0-9]{7}$/;
    if (!customerPhone) {
      setFieldError(phoneInput, '#error-customer-phone', 'Please enter your mobile number.');
    } else if (!pkPhoneRegex.test(customerPhone.replace(/\s+/g, ''))) {
      setFieldError(phoneInput, '#error-customer-phone', 'Please enter a valid Pakistan phone (e.g. 0300-1234567).');
    } else {
      clearFieldError(phoneInput, '#error-customer-phone');
    }

    // Validate delivery address
    if (!address1 || address1.length < 5) {
      setFieldError(addressInput, '#error-shipping-address-1', 'Please enter your full delivery address.');
    } else {
      clearFieldError(addressInput, '#error-shipping-address-1');
    }

    // Validate city
    if (!city) {
      setFieldError(cityInput, '#error-shipping-city', 'Please enter your city.');
    } else {
      clearFieldError(cityInput, '#error-shipping-city');
    }

    // Validate province
    if (!province) {
      setFieldError(provinceInput, '#error-shipping-province', 'Please enter your province.');
    } else {
      clearFieldError(provinceInput, '#error-shipping-province');
    }

    if (hasValidationError) {
      errorBanner.textContent = 'Please review the highlighted fields before placing your order.';
      errorBanner.style.display = 'block';
      firstInvalidField?.focus();
      return;
    }

    if (!capabilities.getState().paymentMethods.includes(paymentMethod)) {
      errorBanner.textContent = 'This payment method is unavailable. Choose Cash on Delivery.';
      errorBanner.style.display = 'block';
      return;
    }

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
      const quote = await fetchCheckoutQuote({ items: itemsPayload, shipping_city: city, shipping_province: province, coupon_code: orderPayload.coupon_code });
      const signature = JSON.stringify([orderPayload, quote]);
      modal.querySelector('#checkout-shipping-label').textContent = formatPkr(quote.shipping_fee_minor);
      modal.querySelector('#checkout-total').textContent = formatPkr(quote.total_minor);
      modal.querySelector('#checkout-subtotal').textContent = formatPkr(quote.subtotal_minor);
      if (confirmedQuote !== signature) {
        confirmedQuote = signature;
        errorBanner.textContent = `Order total: ${formatPkr(quote.total_minor)}, including delivery ${formatPkr(quote.shipping_fee_minor)}. Review and confirm to place your order.`;
        errorBanner.style.display = 'block';
        placeBtn.disabled = false;
        placeBtn.textContent = `Confirm order ? ${formatPkr(quote.total_minor)}`;
        return;
      }
      orderPayload.expected_total_minor = quote.total_minor;
      const order = await submitOrder(orderPayload);
      // Clear shopping cart on confirmed order placement
      cart.clear();
      appliedCoupon = null;
      appliedCouponCartSignature = null;
      renderOrderConfirmation(order);
    } catch (err) {
      placeBtn.disabled = !capabilities.getState().checkoutEnabled;
      placeBtn.textContent = 'Place Order';
      errorBanner.textContent = err.message || 'Failed to place order. Please check your details and try again.';
      errorBanner.style.display = 'block';
    }
  });

  let savedCheckoutContent = null;
  function renderOrderConfirmation(order) {
    const bodyContent = modal.querySelector('#checkout-body-content');
    savedCheckoutContent = Array.from(bodyContent.childNodes);
    const badge = modal.querySelector('#checkout-badge');
    if (badge) {
      badge.textContent = 'Order Placed';
      badge.className = 'badge badge-accent';
    }

    const isBank = order.payment_method === 'bank_transfer';
    const bankHtml = isBank && !order.payment_instructions_sent_at ? `
      <div style="background: #FFFBEB; border: 1px solid #FDE68A; border-radius: var(--radius-sm); padding: 16px; margin: 20px 0; font-size: 0.8125rem;">
        <strong>Awaiting supplier confirmation and payment instructions</strong>
        <p>Your order has been placed. Do not transfer funds until AlphaZee sends your official instructions. The four-hour payment window starts only after that handoff.</p>
        <p>Track your order for updates or contact AlphaZee using your order number.</p>
      </div>
    ` : isBank && order.bank_instructions ? `
      <div style="background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: var(--radius-sm); padding: 16px; margin: 20px 0;">
        <h3 style="font-size: 0.9375rem; font-weight: 700; color: #166534; margin-bottom: 8px;">
          Bank Transfer Payment Instructions
        </h3>
        <p style="font-size: 0.8125rem; color: #15803D; margin-bottom: 12px; line-height: 1.5;">
          Please transfer <strong>${order.total.formatted}</strong> to the official AlphaZee account below. Your payment will be verified by the owner before dispatch.
        </p>
        <div style="font-size: 0.8125rem; font-family: monospace; background: #FFFFFF; border: 1px solid #DCFCE7; border-radius: var(--radius-sm); padding: 12px; line-height: 1.6; color: #14532D;">
          <div><strong>Bank:</strong> ${escapeHtml(order.bank_instructions.bank_name)}</div>
          <div><strong>Title:</strong> ${escapeHtml(order.bank_instructions.account_title)}</div>
          <div><strong>Account #:</strong> ${escapeHtml(order.bank_instructions.account_number)}</div>
          <div><strong>IBAN:</strong> ${escapeHtml(order.bank_instructions.iban)}</div>
        </div>

        ${order.payment_deadline_at ? `
          <div style="margin-top: 10px; font-size: 0.75rem; color: #15803D; font-weight: 600;">
            <strong>Payment deadline:</strong> ${escapeHtml(new Date(order.payment_deadline_at).toLocaleString())}. Expired transfers are reviewed by the owner before any stock is released.
          </div>
        ` : ''}

        <div style="margin-top: 16px;">
          <h4 style="font-size: 0.8125rem; font-weight: 700; color: #166534; margin-bottom: 6px;">
            Upload Proof of Payment (Receipt Screenshot)
          </h4>
          <form id="receipt-upload-form" style="display: flex; flex-direction: column; gap: 8px;">
            <input type="url" id="receipt-url-input" required placeholder="https://storage.alphazee.pk/receipts/proof.png" class="form-input" style="font-size: 0.8125rem;" />
            <input type="text" id="receipt-ref-input" placeholder="Bank Transaction Reference / ID (Optional)" class="form-input" style="font-size: 0.8125rem;" />
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
        <span style="font-weight: 600;" class="price-tabular">${line.line_total.formatted}</span>
      </div>
    `).join('');

    const discountHtml = order.discount_amount && order.discount_amount.minor > 0 ? `
      <div style="display: flex; justify-content: space-between; font-size: 0.875rem; padding: 4px 0; color: var(--color-accent); font-weight: 600;">
        <span>Discount (${escapeHtml(order.coupon_code || 'Promo')})</span>
        <span class="price-tabular">- ${order.discount_amount.formatted}</span>
      </div>
    ` : '';

    bodyContent.innerHTML = `
      <div style="text-align: center; padding: 12px 0 20px 0;">
        <div style="width: 56px; height: 56px; border-radius: 50%; background: rgba(20, 92, 68, 0.1); color: var(--color-accent); display: flex; align-items: center; justify-content: center; margin: 0 auto 12px auto;">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
        </div>
        <h2 style="font-family: var(--font-family-serif); font-size: 1.5rem; font-weight: 500; margin-bottom: 4px;">Thank You for Your Order!</h2>
        <div style="font-size: 1rem; font-weight: 700; color: var(--color-accent); letter-spacing: 0.5px;">
          Order #${escapeHtml(order.order_number)}
        </div>
        <p style="font-size: 0.875rem; color: var(--color-text-muted); margin-top: 4px;">
          Confirmation recorded for <strong>${escapeHtml(order.customer_phone)}</strong>.
        </p>

        <!-- Access Code Guidance Box -->
        <div class="checkout-access-box">
          <span class="checkout-access-badge">Private Access Code</span>
          <p class="checkout-access-instructions">
            Save this private access code to track order status, review delivery updates, and request returns across any device. It is shown only here. If misplaced, contact AlphaZee verified support.
          </p>
          <div class="checkout-access-display">
            <code id="checkout-access-code" class="access-code-val">${escapeHtml(order.access_code || '')}</code>
            <button type="button" class="btn btn-secondary btn-copy-code" id="btn-copy-access-code">
              Copy Code
            </button>
          </div>
          <div id="copy-code-feedback" style="display: none; font-size: 0.75rem; color: var(--color-accent); font-weight: 600; margin-top: 6px;">
            ✓ Access code copied to clipboard
          </div>
        </div>
      </div>

      <div style="background: var(--color-bg); border-radius: var(--radius-btn); padding: 16px;">
        <div style="font-size: 0.8125rem; font-weight: 700; text-transform: uppercase; color: var(--color-text-muted); margin-bottom: 8px;">Order Details</div>
        ${linesHtml}
        ${discountHtml}
        <div style="display: flex; justify-content: space-between; font-size: 1rem; font-weight: 700; border-top: 1px solid var(--color-border); padding-top: 10px; margin-top: 10px;">
          <span>Total Amount</span>
          <span class="price-tabular">${order.total.formatted}</span>
        </div>
      </div>

      ${bankHtml}

      <div style="text-align: center; margin-top: 24px;">
        <button type="button" class="btn btn-secondary" id="btn-finish-checkout" style="min-width: 180px;">
          Continue Shopping
        </button>
      </div>
    `;

    // Wire copy code button
    const copyBtn = modal.querySelector('#btn-copy-access-code');
    const feedback = modal.querySelector('#copy-code-feedback');
    copyBtn?.addEventListener('click', async () => {
      try {
        if (navigator?.clipboard?.writeText) {
          await navigator.clipboard.writeText(order.access_code || '');
        } else {
          throw new Error('Clipboard API unavailable');
        }
      } catch {
        const codeEl = modal.querySelector('#checkout-access-code');
        if (codeEl) {
          const range = document.createRange();
          range.selectNodeContents(codeEl);
          const sel = window.getSelection();
          sel?.removeAllRanges();
          sel?.addRange(range);
        }
      } finally {
        if (feedback) feedback.style.display = 'block';
        copyBtn.textContent = 'Copied!';
        setTimeout(() => {
          copyBtn.textContent = 'Copy Code';
          if (feedback) feedback.style.display = 'none';
        }, 3000);
      }
    });

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

  let recovering = false;
  function open() {
    if (savedCheckoutContent) {
      modal.querySelector('#checkout-body-content').replaceChildren(...savedCheckoutContent);
      savedCheckoutContent = null;
      form.reset();
      modal.querySelector('#btn-place-order').textContent = 'Place Order';
      modal.querySelector('#checkout-error-banner').style.display = 'none';
      modal.querySelector('#checkout-badge').textContent = 'Secure Checkout';
      updateRadioStyle();
    }
    overlay.open();
    cart.reconcileWithApi();
    renderCartState(cart.getState());
    capabilities.refresh().then(async () => {
      if (modal.hidden || !capabilities.getState().checkoutEnabled || !getPendingCheckoutAttempt() || recovering) return;
      recovering = true;
      modal.querySelector('#btn-place-order').disabled = true;
      const errorBanner = modal.querySelector('#checkout-error-banner');
      errorBanner.textContent = 'Checking your previous order submission...';
      errorBanner.style.display = 'block';
      try {
        const pending = getPendingCheckoutAttempt();
        const order = await recoverPendingOrder();
        if (modal.hidden || !order) return;
        const currentItems = cart.getState().items.map(i => [i.variant_id, i.quantity]).sort();
        const submittedItems = pending.payload.items.map(i => [i.variant_id, i.quantity]).sort();
        if (JSON.stringify(currentItems) === JSON.stringify(submittedItems)) cart.clear();
        appliedCoupon = null;
        renderOrderConfirmation(order);
      } catch (error) {
        errorBanner.textContent = `Previous submission could not be confirmed: ${error.message}`;
        errorBanner.style.display = 'block';
        renderCartState(cart.getState());
      } finally {
        recovering = false;
      }
    });
  }

  function close() {
    overlay.close();
  }

  const overlay = createOverlay({ element: modal, onClose: () => onClose?.() });

  modal.querySelector('.drawer-backdrop').addEventListener('click', close);
  modal.querySelector('#checkout-close-btn').addEventListener('click', close);
  capabilities.subscribe(() => renderCartState(cart.getState()));

  return {
    element: modal,
    open,
    close
  };
}

