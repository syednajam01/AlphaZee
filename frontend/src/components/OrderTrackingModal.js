import { createOverlay } from '../utils/overlay.js';
import { createBrandLogo } from './BrandLogo.js';
import { fetchOrderStatus, fetchExchangeOptions, uploadReceipt, requestOrderReturn, ApiError } from '../utils/api.js';
import { escapeHtml } from '../utils/dom.js';
import { formatPkr } from '../utils/money.js';

export function createOrderTrackingModal(onClose) {
  const modal = document.createElement('div');
  modal.className = 'modal-container';
  modal.id = 'tracking-modal';
  modal.setAttribute('role', 'dialog');
  modal.setAttribute('aria-modal', 'true');
  modal.setAttribute('aria-label', 'AlphaZee Order Tracking');

  modal.innerHTML = `
    <div class="drawer-backdrop" style="z-index: 1;"></div>
    <div class="modal-content" style="z-index: 2; max-width: 620px; padding: 0; overflow: hidden;">
      <!-- Header -->
      <div style="display: flex; align-items: center; justify-content: space-between; padding: 16px 24px; border-bottom: 1px solid var(--color-border); background: var(--color-surface);">
        <div id="tracking-logo-slot"></div>
        <div style="display: flex; align-items: center; gap: 12px;">
          <span class="badge badge-neutral" style="font-weight: 600;">Track Order</span>
          <button class="btn-icon" id="tracking-close-btn" aria-label="Close tracking">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
      </div>

      <!-- Content -->
      <div id="tracking-content-area" style="padding: 24px; max-height: 75vh; overflow-y: auto;">
        <form id="tracking-search-form" style="display: flex; flex-direction: column; gap: 14px; margin-bottom: 20px;">
          <p style="font-size: 0.875rem; color: var(--color-text-muted); margin: 0 0 4px 0;">
            Enter your order number and private access code. If you lost the code, contact the store for verified recovery.
          </p>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
            <div>
              <label for="tracking-order-num" style="font-size: 0.75rem; font-weight: 600; display: block; margin-bottom: 4px;">Order Number *</label>
              <input type="text" id="tracking-order-num" required placeholder="AZ-20261011-A1B2C3" style="width: 100%; padding: 10px 14px; border: 1px solid var(--color-border); border-radius: var(--radius-btn); font-size: 0.875rem;" />
            </div>
            <div>
              <label for="tracking-code" style="font-size: 0.75rem; font-weight: 600; display: block; margin-bottom: 4px;">Access Code</label>
              <input type="password" id="tracking-code" autocomplete="off" placeholder="Private code (or use this device's session)" style="width: 100%; padding: 10px 14px; border: 1px solid var(--color-border); border-radius: var(--radius-btn); font-size: 0.875rem;" />
            </div>
          </div>

          <div id="tracking-error-banner" style="display: none; padding: 10px 14px; background-color: #FEF2F2; border: 1px solid #FCA5A5; border-left: 4px solid #DC2626; border-radius: var(--radius-sm); font-size: 0.8125rem; color: #991B1B;"></div>

          <button type="submit" id="btn-search-order" class="btn btn-primary" style="align-self: flex-start; min-height: 40px; padding: 0 20px;">
            Lookup Order
          </button>
        </form>

        <div id="tracking-results-area" style="display: none;"></div>
      </div>
    </div>
  `;

  // Mount logo
  const logoSlot = modal.querySelector('#tracking-logo-slot');
  if (logoSlot) {
    const wordmark = createBrandLogo({ variant: 'wordmark', surface: 'light', width: 110, ariaLabel: 'AlphaZee' });
    logoSlot.appendChild(wordmark);
  }

  const searchForm = modal.querySelector('#tracking-search-form');
  const errorBanner = modal.querySelector('#tracking-error-banner');
  const searchBtn = modal.querySelector('#btn-search-order');
  const resultsArea = modal.querySelector('#tracking-results-area');

  searchForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorBanner.style.display = 'none';
    resultsArea.style.display = 'none';

    const orderNum = (modal.querySelector('#tracking-order-num')?.value || '').trim();
    const code = (modal.querySelector('#tracking-code')?.value || '').trim();

    if (!orderNum) return;

    searchBtn.disabled = true;
    searchBtn.textContent = 'Searching...';

    try {
      const order = await fetchOrderStatus(orderNum, code);
      modal.querySelector('#tracking-code').value = '';
      searchBtn.disabled = false;
      searchBtn.textContent = 'Lookup Order';
      renderOrderDetails(order);
    } catch (err) {
      searchBtn.disabled = false;
      searchBtn.textContent = 'Lookup Order';
      errorBanner.textContent = err.message || 'Order access unavailable. Check your code or contact the store.';
      errorBanner.style.display = 'block';
    }
  });

  function renderOrderDetails(order) {
    resultsArea.style.display = 'block';

    const statusBadgeClass = {
      placed: 'badge-neutral',
      confirmed: 'badge-accent',
      dispatched: 'badge-accent',
      delivered: 'badge-accent',
      cancelled: 'badge-neutral',
    }[order.order_status] || 'badge-neutral';

    const paymentBadgeClass = {
      pending: 'badge-neutral',
      verified: 'badge-accent',
      failed: 'badge-neutral',
    }[order.payment_status] || 'badge-neutral';

    const linesHtml = order.lines.filter(l => l.fulfillment_kind === 'original').map(l => `
      <div style="display: flex; justify-content: space-between; font-size: 0.875rem; padding: 6px 0; border-bottom: 1px solid var(--color-border-subtle);">
        <div>
          <strong>${escapeHtml(l.product_title)}</strong> × ${l.quantity}
          <div style="font-size: 0.75rem; color: var(--color-text-muted);">
            ${[l.size ? `Size: ${escapeHtml(l.size)}` : '', l.color ? `Color: ${escapeHtml(l.color)}` : ''].filter(Boolean).join(' • ')}
          </div>
        </div>
        <div style="font-weight: 600;">${l.line_total.formatted}</div>
      </div>
    `).join('');
    const replacementHtml = order.lines.filter(l => l.fulfillment_kind === 'replacement').map(l => `
      <div style="font-size: .8125rem; padding: 8px; background: #F0FDF4; margin-top: 6px;">
        Replacement: ${escapeHtml(l.product_title)} (${escapeHtml(l.size || l.color || l.variant_sku)}) × ${l.quantity}
      </div>
    `).join('');

    const discountHtml = order.discount_amount && order.discount_amount.minor > 0 ? `
      <div style="display: flex; justify-content: space-between; font-size: 0.875rem; padding: 4px 0; color: var(--color-accent); font-weight: 600;">
        <span>Promotional Discount (${escapeHtml(order.coupon_code || 'Voucher')})</span>
        <span>- ${order.discount_amount.formatted}</span>
      </div>
    ` : '';

    const isBankPending = order.payment_method === 'bank_transfer' && order.payment_status === 'pending';
    const uploadReceiptHtml = isBankPending && !order.payment_instructions_sent_at ? `
      <div style="background: #FFFBEB; border: 1px solid #FDE68A; border-radius: var(--radius-sm); padding: 14px; margin-top: 16px; font-size: 0.8125rem;">
        Awaiting supplier confirmation and official payment instructions. Do not send funds yet.
      </div>
    ` : isBankPending && order.bank_instructions ? `
      <div style="background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: var(--radius-sm); padding: 14px; margin-top: 16px;">
        <div style="font-size: 0.8125rem; font-weight: 700; color: #166534; margin-bottom: 4px;">
          Pending Bank Transfer Verification
        </div>
        <div style="font-size: 0.75rem; color: #166534; margin-bottom: 8px;">
          <strong>Bank:</strong> ${escapeHtml(order.bank_instructions.bank_name)}<br>
          <strong>Account title:</strong> ${escapeHtml(order.bank_instructions.account_title)}<br>
          <strong>Account number:</strong> ${escapeHtml(order.bank_instructions.account_number)}<br>
          <strong>IBAN:</strong> ${escapeHtml(order.bank_instructions.iban)}
          ${order.payment_deadline_at ? `<br><strong>Payment deadline:</strong> ${escapeHtml(new Date(order.payment_deadline_at).toLocaleString())}` : ''}
        </div>
        ${order.payment_review_status === 'required' ? '<p>Your transfer is under owner review. Reserved stock remains held until the funds check is complete.</p>' : ''}
        <p style="font-size: 0.75rem; color: #15803D; margin: 0 0 10px 0;">
          If you haven't uploaded proof of payment yet, please provide the screenshot URL below:
        </p>
        <form id="track-receipt-form" style="display: flex; flex-direction: column; gap: 8px;">
          <input type="url" id="track-receipt-url" required placeholder="https://storage.alphazee.pk/receipts/proof.png" style="width: 100%; padding: 8px 12px; border: 1px solid #86EFAC; border-radius: var(--radius-btn); font-size: 0.8125rem;" />
          <input type="text" id="track-receipt-ref" placeholder="Bank Reference (Optional)" style="width: 100%; padding: 8px 12px; border: 1px solid #86EFAC; border-radius: var(--radius-btn); font-size: 0.8125rem;" />
          <button type="submit" id="btn-track-upload" class="btn btn-primary" style="align-self: flex-start; padding: 6px 14px; font-size: 0.8125rem;">
            Submit Payment Proof
          </button>
          <div id="track-receipt-status" style="display: none; font-size: 0.75rem; font-weight: 600;"></div>
        </form>
      </div>
    ` : '';

    const returnsListHtml = order.returns && order.returns.length > 0 ? `
      <div style="background: #FFFBEB; border: 1px solid #FDE68A; border-radius: var(--radius-sm); padding: 14px; margin-top: 14px;">
        <div style="font-size: 0.8125rem; font-weight: 700; color: #92400E; margin-bottom: 6px;">Return & Exchange Requests</div>
        ${order.returns.map(r => `
          <div style="font-size: 0.75rem; padding: 6px 0; border-bottom: 1px solid #FEF3C7; color: #78350F;">
            <div style="display: flex; justify-content: space-between;">
              <strong>Type: ${escapeHtml(r.return_type)}</strong>
              <span class="badge ${r.status === 'completed' ? 'badge-accent' : 'badge-neutral'}" style="text-transform: capitalize; font-size: 0.65rem;">
                ${escapeHtml(r.status)}
              </span>
            </div>
            <div>Reason: ${escapeHtml(r.reason)}</div>
            ${r.return_type === 'refund_bank_transfer' ? `<div>Refund paid: ${escapeHtml(r.refund_paid.formatted)} · Remaining: ${escapeHtml(r.refund_outstanding.formatted)}</div>` : ''}
            ${r.refund_executions?.map(payment => `<div>Paid ${escapeHtml(formatPkr(payment.amount_minor))} via ${escapeHtml(payment.channel)} · Ref: <code>${escapeHtml(payment.reference)}</code></div>`).join('') || ''}
          </div>
        `).join('')}
      </div>
    ` : '';

    resultsArea.innerHTML = `
      <div style="background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-card); padding: 16px;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
          <div>
            <div style="font-size: 0.75rem; text-transform: uppercase; color: var(--color-text-muted); font-weight: 700;">Order Number</div>
            <div style="font-size: 1.125rem; font-weight: 800; color: var(--color-accent);">${escapeHtml(order.order_number)}</div>
          </div>
          <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 4px;">
            <span class="badge ${statusBadgeClass}" style="text-transform: capitalize;">Order: ${escapeHtml(order.order_status)}</span>
            <span class="badge ${paymentBadgeClass}" style="text-transform: capitalize; font-size: 0.7rem;">Payment: ${escapeHtml(order.payment_status)}</span>
          </div>
        </div>

        ${(() => {
          const stepOrder = ['placed', 'confirmed', 'dispatched', 'delivered'];
          const currentStepIdx = stepOrder.indexOf(order.order_status);
          if (order.order_status === 'cancelled') {
            return `
              <div style="padding: 10px 14px; background: #FEF2F2; border: 1px solid #FCA5A5; border-radius: var(--radius-sm); color: #991B1B; font-weight: 600; font-size: 0.8125rem; margin: 12px 0;">
                This order has been cancelled.
              </div>
            `;
          }
          return `
            <div class="tracking-stepper" aria-label="Order status progression">
              <div class="tracking-step ${currentStepIdx > 0 ? 'is-done' : currentStepIdx === 0 ? 'is-active' : ''}">
                <div class="tracking-step-circle">${currentStepIdx > 0 ? '✓' : '1'}</div>
                <div class="tracking-step-label">Placed</div>
              </div>
              <div class="tracking-step ${currentStepIdx > 1 ? 'is-done' : currentStepIdx === 1 ? 'is-active' : ''}">
                <div class="tracking-step-circle">${currentStepIdx > 1 ? '✓' : '2'}</div>
                <div class="tracking-step-label">Confirmed</div>
              </div>
              <div class="tracking-step ${currentStepIdx > 2 ? 'is-done' : currentStepIdx === 2 ? 'is-active' : ''}">
                <div class="tracking-step-circle">${currentStepIdx > 2 ? '✓' : '3'}</div>
                <div class="tracking-step-label">Dispatched</div>
              </div>
              <div class="tracking-step ${currentStepIdx >= 3 ? 'is-done is-active' : ''}">
                <div class="tracking-step-circle">${currentStepIdx >= 3 ? '✓' : '4'}</div>
                <div class="tracking-step-label">Delivered</div>
              </div>
            </div>
          `;
        })()}

        <div style="font-size: 0.8125rem; color: var(--color-text-muted); margin-bottom: 14px; line-height: 1.4;">
          <div><strong>Recipient:</strong> ${escapeHtml(order.customer_name)} (${escapeHtml(order.customer_phone)})</div>
          <div><strong>Destination:</strong> ${escapeHtml(order.shipping_address_line1)}, ${escapeHtml(order.shipping_city)}, ${escapeHtml(order.shipping_province)}</div>
          <div><strong>Payment Method:</strong> ${order.payment_method === 'cod' ? 'Cash on Delivery (COD)' : 'Bank Transfer'}</div>
        </div>

        <div style="font-size: 0.8125rem; font-weight: 700; text-transform: uppercase; color: var(--color-text-muted); margin-bottom: 6px;">Ordered Items</div>
        ${linesHtml}
        ${replacementHtml ? `<div style="font-size: .8125rem; font-weight: 700; margin-top: 12px;">Exchange replacements</div>${replacementHtml}` : ''}
        ${discountHtml}

        <div style="display: flex; justify-content: space-between; font-size: 1rem; font-weight: 700; margin-top: 10px; padding-top: 8px; border-top: 1px solid var(--color-border);">
          <span>Total Amount</span>
          <span class="price-tabular">${order.total.formatted}</span>
        </div>

        ${order.shipments?.map(shipment => `
          <div style="background: #F8FAFC; border: 1px solid var(--color-border); border-radius: var(--radius-sm); padding: 14px; margin-top: 14px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
              <span style="font-size: 0.8125rem; font-weight: 700; color: var(--color-text);">${shipment.replacement_return_id ? 'Replacement' : 'Original'} Courier Tracking</span>
              <span class="badge badge-accent" style="text-transform: capitalize; font-size: 0.7rem;">${escapeHtml(shipment.status)}</span>
            </div>
            <div style="font-size: 0.8125rem; color: var(--color-text-muted); line-height: 1.5;">
              <div><strong>Courier:</strong> ${escapeHtml(shipment.courier_name || shipment.courier_code)}</div>
              <div><strong>Tracking #:</strong> <span style="font-family: monospace; font-weight: 700; color: var(--color-accent);">${escapeHtml(shipment.tracking_number)}</span></div>
            </div>
            ${shipment.tracking_url ? `
              <a href="${escapeHtml(shipment.tracking_url)}" target="_blank" rel="noopener noreferrer" class="btn btn-secondary" style="display: inline-block; margin-top: 8px; padding: 4px 10px; font-size: 0.75rem; text-decoration: none;">
                Track on Courier Site ↗
              </a>
            ` : ''}
          </div>
        `).join('') || ''}

        ${uploadReceiptHtml}
        ${returnsListHtml}

        ${order.order_status === 'delivered' ? `<!-- Return / Size Exchange Trigger Form -->
        <div style="margin-top: 16px; border-top: 1px dashed var(--color-border); padding-top: 12px;">
          <button type="button" id="btn-toggle-return-form" class="btn btn-secondary" style="width: 100%; font-size: 0.8125rem; padding: 8px 12px;">
            Request Return
          </button>
          
          <div id="return-request-panel" style="display: none; margin-top: 12px; background: #F8FAFC; border: 1px solid var(--color-border); border-radius: var(--radius-sm); padding: 14px;">
            <h4 style="font-size: 0.8125rem; font-weight: 700; margin-bottom: 8px;">Submit Return Request</h4>
            <form id="form-submit-return" style="display: flex; flex-direction: column; gap: 8px;">
              <div>
                <label style="font-size: 0.75rem; font-weight: 600; display: block; margin-bottom: 2px;">Select Item</label>
                <select id="return-select-line" required style="width: 100%; padding: 6px 10px; font-size: 0.8125rem; border: 1px solid var(--color-border); border-radius: var(--radius-btn);">
                  ${order.lines.filter(l => l.fulfillment_kind === 'original').map(l => `<option value="${l.id}">${escapeHtml(l.product_title)} (${escapeHtml(l.size || '')})</option>`).join('')}
                </select>
              </div>
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                <div>
                  <label style="font-size: 0.75rem; font-weight: 600; display: block; margin-bottom: 2px;">Request Type</label>
                  <select id="return-select-type" style="width: 100%; padding: 6px 10px; font-size: 0.8125rem; border: 1px solid var(--color-border); border-radius: var(--radius-btn);">
                    <option value="refund_bank_transfer">Bank Refund</option>
                    <option value="size_exchange">Size Exchange</option>
                    <option value="store_credit">Store Credit</option>
                  </select>
                </div>
                <div>
                  <label style="font-size: 0.75rem; font-weight: 600; display: block; margin-bottom: 2px;">Reason</label>
                  <select id="return-select-reason" style="width: 100%; padding: 6px 10px; font-size: 0.8125rem; border: 1px solid var(--color-border); border-radius: var(--radius-btn);">
                    <option value="size_too_small">Size Too Small</option>
                    <option value="size_too_large">Size Too Large</option>
                    <option value="damaged_defective">Damaged / Defective</option>
                    <option value="not_as_described">Not As Described</option>
                    <option value="changed_mind">Changed Mind</option>
                  </select>
                </div>
              </div>
              <div id="return-exchange-options" style="display: none;">
                <label for="return-exchange-variant" style="font-size: 0.75rem; font-weight: 600;">Replacement variant</label>
                <select id="return-exchange-variant" style="width: 100%; padding: 6px 10px;"></select>
              </div>
              <div>
                <label for="return-quantity" style="font-size: 0.75rem; font-weight: 600; display: block; margin-bottom: 2px;">Quantity to return</label>
                <input id="return-quantity" type="number" min="1" max="${order.lines[0]?.quantity || 1}" value="1" required style="width: 100%; padding: 6px 10px; font-size: 0.8125rem; border: 1px solid var(--color-border); border-radius: var(--radius-btn);" />
              </div>
              <div>
                <label style="font-size: 0.75rem; font-weight: 600; display: block; margin-bottom: 2px;">Notes / Desired Replacement Size</label>
                <textarea id="return-notes" rows="2" placeholder="e.g. Please send Size L instead" style="width: 100%; padding: 6px 10px; font-size: 0.8125rem; border: 1px solid var(--color-border); border-radius: var(--radius-btn);"></textarea>
              </div>
              <button type="submit" id="btn-submit-return-req" class="btn btn-primary" style="align-self: flex-start; padding: 6px 14px; font-size: 0.8125rem;">
                Submit Return Request
              </button>
              <div id="return-req-msg" style="display: none; font-size: 0.75rem; font-weight: 600;"></div>
            </form>
          </div>
        </div>` : ''}
      </div>
    `;

    // Toggle return request form
    const toggleReturnBtn = resultsArea.querySelector('#btn-toggle-return-form');
    const returnPanel = resultsArea.querySelector('#return-request-panel');
    toggleReturnBtn?.addEventListener('click', () => {
      returnPanel.style.display = returnPanel.style.display === 'none' ? 'block' : 'none';
    });

    // Handle return request form submission
    const returnForm = resultsArea.querySelector('#form-submit-return');
    const refreshExchangeOptions = async () => {
      const exchange = resultsArea.querySelector('#return-select-type').value === 'size_exchange';
      const panel = resultsArea.querySelector('#return-exchange-options');
      panel.style.display = exchange ? 'block' : 'none';
      if (!exchange) return;
      const selector = resultsArea.querySelector('#return-exchange-variant');
      selector.replaceChildren();
      try {
        const options = await fetchExchangeOptions(order.order_number, resultsArea.querySelector('#return-select-line').value);
        for (const option of options) {
          const item = document.createElement('option');
          item.value = String(option.id);
          item.textContent = [option.size, option.color, option.sku].filter(Boolean).join(' / ');
          selector.appendChild(item);
        }
        if (!options.length) returnMsg.textContent = 'No replacement variants are available.';
      } catch (error) { returnMsg.textContent = error.message; returnMsg.style.display = 'block'; }
    };
    resultsArea.querySelector('#return-select-type')?.addEventListener('change', refreshExchangeOptions);
    resultsArea.querySelector('#return-select-line')?.addEventListener('change', (event) => {
      const selected = order.lines.find(line => line.id === event.target.value);
      const quantityInput = resultsArea.querySelector('#return-quantity');
      quantityInput.max = String(selected?.quantity || 1);
      if (Number(quantityInput.value) > Number(quantityInput.max)) quantityInput.value = quantityInput.max;
      refreshExchangeOptions();
    });
    const returnSubmitBtn = resultsArea.querySelector('#btn-submit-return-req');
    const returnMsg = resultsArea.querySelector('#return-req-msg');

    returnForm?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const lineId = resultsArea.querySelector('#return-select-line').value;
      const quantity = Number(resultsArea.querySelector('#return-quantity').value);
      const retType = resultsArea.querySelector('#return-select-type').value;
      const reason = resultsArea.querySelector('#return-select-reason').value;
      const notes = resultsArea.querySelector('#return-notes').value.trim() || null;
      const replacementVariant = Number(resultsArea.querySelector('#return-exchange-variant')?.value || 0);
      if (retType === 'size_exchange' && !replacementVariant) {
        returnMsg.textContent = 'Select an available replacement variant.';
        returnMsg.style.display = 'block';
        return;
      }

      returnSubmitBtn.disabled = true;
      returnSubmitBtn.textContent = 'Submitting...';
      returnMsg.style.display = 'none';

      try {
        await requestOrderReturn({
          quantity,
          order_id: order.id,
          order_line_id: lineId,
          return_type: retType,
          reason,
          customer_notes: notes,
          exchange_variant_id: retType === 'size_exchange' ? replacementVariant : null,
        });
        returnMsg.style.color = '#15803D';
        returnMsg.textContent = 'Return request submitted! Owner will review and coordinate pickup/exchange.';
        returnMsg.style.display = 'block';
        returnSubmitBtn.textContent = 'Submitted';
      } catch (err) {
        returnSubmitBtn.disabled = false;
        returnSubmitBtn.textContent = 'Submit Return Request';
        returnMsg.style.color = '#DC2626';
        returnMsg.textContent = err.message || 'Failed to submit return request.';
        returnMsg.style.display = 'block';
      }
    });

    if (isBankPending) {
      const receiptForm = resultsArea.querySelector('#track-receipt-form');
      const uploadBtn = resultsArea.querySelector('#btn-track-upload');
      const statusMsg = resultsArea.querySelector('#track-receipt-status');

      receiptForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const url = resultsArea.querySelector('#track-receipt-url').value.trim();
        const ref = resultsArea.querySelector('#track-receipt-ref').value.trim() || null;

        uploadBtn.disabled = true;
        uploadBtn.textContent = 'Uploading...';
        statusMsg.style.display = 'none';

        try {
          await uploadReceipt(order.order_number, {
            receipt_image_url: url,
            bank_reference: ref,
          });
          statusMsg.style.color = '#15803D';
          statusMsg.textContent = 'Receipt submitted! Owner will verify funds before dispatch.';
          statusMsg.style.display = 'block';
          uploadBtn.textContent = 'Submitted';
        } catch (uploadErr) {
          uploadBtn.disabled = false;
          uploadBtn.textContent = 'Submit Payment Proof';
          statusMsg.style.color = '#DC2626';
          statusMsg.textContent = uploadErr.message || 'Failed to submit receipt.';
          statusMsg.style.display = 'block';
        }
      });
    }
  }

  function open(prefillOrderNumber = '', prefillPhone = '') {
    overlay.open();
    if (prefillOrderNumber) {
      modal.querySelector('#tracking-order-num').value = prefillOrderNumber;
    }
    if (prefillPhone) {
      modal.querySelector('#tracking-phone').value = prefillPhone;
    }
    if (prefillOrderNumber && prefillPhone) {
      searchForm.dispatchEvent(new Event('submit'));
    }
  }

  function close() {
    overlay.close();
  }

  const overlay = createOverlay({ element: modal, onClose: () => onClose?.() });

  modal.querySelector('.drawer-backdrop').addEventListener('click', close);
  modal.querySelector('#tracking-close-btn').addEventListener('click', close);

  return {
    element: modal,
    open,
    close,
  };
}
