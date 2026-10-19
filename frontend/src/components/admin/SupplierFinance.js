import { escapeHtml } from '../../utils/dom.js';
import { formatPkr, parseCatalogPkr } from '../../utils/money.js';
import {
  fetchSupplierAgreement,
  updateSupplierAgreement,
  fetchSupplierLedger,
  fetchSupplierLedgerSummary,
  postSupplierManualCharge,
  postSupplierCreditNote,
  reverseSupplierLedgerEntry,
  previewSupplierOpeningBalance,
  applySupplierOpeningBalance,
  postSupplierPayment,
  postSupplierAdvance,
  allocateSupplierPayment,
  postSupplierRefund,
  fetchSupplierUnpaidAndAdvances,
  fetchSupplierStatement,
} from '../../utils/api.js';

export function createSupplierFinanceView(supplier, { onClose = () => {} } = {}) {
  const container = document.createElement('div');
  container.className = 'supplier-finance-modal modal-container is-open';
  container.id = 'supplier-finance-dialog';
  container.setAttribute('role', 'dialog');
  container.setAttribute('aria-modal', 'true');
  container.setAttribute('aria-label', `Supplier Finance: ${supplier.name}`);
  container.style.cssText = 'position: fixed; inset: 0; z-index: 1000; display: flex; align-items: center; justify-content: center; opacity: 1; visibility: visible;';

  container.innerHTML = `
    <div class="drawer-backdrop" style="position: fixed; inset: 0; background: rgba(0,0,0,0.75); z-index: 1001;"></div>
    <div class="modal-content" style="z-index: 1002; max-width: 1150px; width: 96%; max-height: 92vh; overflow-y: auto; background: #141715; color: #FFFFFF; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.15); padding: 24px; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.8); position: relative;">
      
      <!-- Header -->
      <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px solid rgba(255, 255, 255, 0.1); padding-bottom: 16px; margin-bottom: 20px;">
        <div>
          <div style="display: flex; align-items: center; gap: 10px;">
            <h2 style="font-size: 1.25rem; font-weight: 700; margin: 0;">${escapeHtml(supplier.name)}</h2>
            <span class="badge ${supplier.status === 'active' ? 'badge-accent' : 'badge-neutral'}" style="font-size: 0.7rem;">
              ${escapeHtml(supplier.status)}
            </span>
          </div>
          <p style="font-size: 0.8125rem; color: rgba(255, 255, 255, 0.6); margin: 4px 0 0 0;">
            Slug: <code>${escapeHtml(supplier.slug)}</code> &bull; Settlement Agreement, Disbursements & Immutable Ledger
          </p>
        </div>
        <button id="btn-close-finance" class="btn-icon" style="background: none; border: none; color: rgba(255, 255, 255, 0.7); font-size: 1.5rem; cursor: pointer; padding: 4px 8px;" aria-label="Close dialog">&times;</button>
      </div>

      <!-- Agreement Configuration Box -->
      <div style="background: #1B201D; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 16px; margin-bottom: 20px;">
        <h3 style="font-size: 0.9375rem; font-weight: 700; margin-top: 0; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
          <span>📋 Settlement Agreement Terms</span>
          <span style="font-size: 0.75rem; font-weight: 400; color: rgba(255, 255, 255, 0.5);">(Applies strictly to future order events)</span>
        </h3>
        <form id="agreement-form" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; align-items: end;">
          <div>
            <label style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); display: block; margin-bottom: 4px;">Payable Liability Trigger *</label>
            <select id="sel-payable-trigger" required style="width: 100%; padding: 8px; background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 6px; font-size: 0.8125rem;">
              <option value="manual">Manual only (no automatic order charges)</option>
              <option value="confirmed_pickup">Confirmed Pickup (vendor acceptance)</option>
              <option value="dispatch">Dispatch (handed to courier)</option>
              <option value="delivery">Delivery (successfully delivered to buyer)</option>
            </select>
          </div>
          <div>
            <label style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); display: block; margin-bottom: 4px;">Payment Terms (Days)</label>
            <input type="number" id="inp-payment-terms" min="0" max="365" value="0" style="width: 100%; padding: 8px; background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 6px; font-size: 0.8125rem;" />
          </div>
          <div style="grid-column: 1 / -1;">
            <label style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); display: block; margin-bottom: 4px;">Agreement Notes & Settlement Banking Details</label>
            <input type="text" id="inp-agreement-notes" placeholder="e.g. Bank: Meezan, Title: Vendor PK, IBAN: PK..., Net 14" style="width: 100%; padding: 8px; background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 6px; font-size: 0.8125rem;" />
          </div>
          <div>
            <button type="submit" id="btn-save-agreement" class="btn btn-primary" style="padding: 8px 16px; font-size: 0.8125rem;">
              Save Agreement Terms
            </button>
          </div>
          <div id="agreement-feedback" role="status" style="font-size: 0.75rem; color: #34D399; font-weight: 600;"></div>
        </form>
      </div>

      <!-- Financial KPI Summary Cards -->
      <div id="finance-kpi-cards" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin-bottom: 20px;">
        <div style="background: rgba(20, 92, 68, 0.25); border: 1px solid #145C44; border-radius: 8px; padding: 14px;">
          <div style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); text-transform: uppercase;">Outstanding Payable</div>
          <div id="kpi-outstanding" style="font-size: 1.375rem; font-weight: 700; color: #34D399; margin-top: 4px;">PKR 0</div>
          <div style="font-size: 0.7rem; color: rgba(255, 255, 255, 0.5); margin-top: 2px;">Net liability owed to vendor</div>
        </div>
        <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 14px;">
          <div style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); text-transform: uppercase;">Total Charges</div>
          <div id="kpi-charges" style="font-size: 1.125rem; font-weight: 700; color: #FFFFFF; margin-top: 4px;">PKR 0</div>
          <div style="font-size: 0.7rem; color: rgba(255, 255, 255, 0.5); margin-top: 2px;">Order costs & manual charges</div>
        </div>
        <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 14px;">
          <div style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); text-transform: uppercase;">Credit Notes</div>
          <div id="kpi-credits" style="font-size: 1.125rem; font-weight: 700; color: #F87171; margin-top: 4px;">PKR 0</div>
          <div style="font-size: 0.7rem; color: rgba(255, 255, 255, 0.5); margin-top: 2px;">Discounts & supplier allowances</div>
        </div>
        <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 14px;">
          <div style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); text-transform: uppercase;">Total Payments</div>
          <div id="kpi-payments" style="font-size: 1.125rem; font-weight: 700; color: #60A5FA; margin-top: 4px;">PKR 0</div>
          <div style="font-size: 0.7rem; color: rgba(255, 255, 255, 0.5); margin-top: 2px;">Disbursements made to vendor</div>
        </div>
        <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 14px;">
          <div style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); text-transform: uppercase;">Unallocated Advances</div>
          <div id="kpi-advances" style="font-size: 1.125rem; font-weight: 700; color: #FBBF24; margin-top: 4px;">PKR 0</div>
          <div style="font-size: 0.7rem; color: rgba(255, 255, 255, 0.5); margin-top: 2px;">Vendor prepaid cash buffer</div>
        </div>
      </div>

      <!-- Action Buttons Bar -->
      <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; align-items: center; justify-content: space-between;">
        <div style="display: flex; flex-wrap: wrap; gap: 8px;">
          <button id="btn-open-payment-modal" class="btn btn-primary" style="font-size: 0.8125rem; padding: 6px 14px; border-radius: 6px; font-weight: 700;">
            + Record Payment
          </button>
          <button id="btn-open-advance-modal" class="btn" style="background: rgba(251, 191, 36, 0.15); color: #FBBF24; font-size: 0.8125rem; padding: 6px 12px; border-radius: 6px; border: 1px solid rgba(251, 191, 36, 0.3);">
            + Disburse Advance
          </button>
          <button id="btn-open-refund-modal" class="btn" style="background: rgba(96, 165, 250, 0.15); color: #60A5FA; font-size: 0.8125rem; padding: 6px 12px; border-radius: 6px; border: 1px solid rgba(96, 165, 250, 0.3);">
            + Supplier Refund
          </button>
          <button id="btn-open-charge-modal" class="btn" style="background: rgba(255, 255, 255, 0.1); color: #FFF; font-size: 0.8125rem; padding: 6px 12px; border-radius: 6px; border: 1px solid rgba(255, 255, 255, 0.2);">
            + Manual Charge
          </button>
          <button id="btn-open-credit-modal" class="btn" style="background: rgba(255, 255, 255, 0.1); color: #FFF; font-size: 0.8125rem; padding: 6px 12px; border-radius: 6px; border: 1px solid rgba(255, 255, 255, 0.2);">
            + Credit Note
          </button>
          <button id="btn-open-opening-balance-modal" class="btn" style="background: rgba(255, 255, 255, 0.1); color: #FFF; font-size: 0.8125rem; padding: 6px 12px; border-radius: 6px; border: 1px solid rgba(255, 255, 255, 0.2);">
            ⚖ Apply Opening Balance
          </button>
        </div>
        <div style="display: flex; gap: 8px;">
          <button id="btn-open-statement-modal" class="btn" style="background: #1E293B; color: #38BDF8; font-size: 0.8125rem; padding: 6px 12px; border-radius: 6px; border: 1px solid rgba(56, 189, 248, 0.3);">
            📜 Period Statement
          </button>
          <button id="btn-refresh-ledger" class="btn-icon" style="background: none; border: 1px solid rgba(255, 255, 255, 0.15); color: #FFF; padding: 6px 10px; border-radius: 6px; font-size: 0.75rem; cursor: pointer;">
            ↻ Refresh
          </button>
        </div>
      </div>

      <!-- Ledger Table -->
      <div style="overflow-x: auto; background: #0E100F; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px;">
        <table style="width: 100%; border-collapse: collapse; font-size: 0.8125rem; text-align: left;">
          <thead>
            <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.12); color: rgba(255, 255, 255, 0.5); font-size: 0.75rem; text-transform: uppercase;">
              <th style="padding: 10px 12px;">Date</th>
              <th style="padding: 10px 12px;">Reference</th>
              <th style="padding: 10px 12px;">Type</th>
              <th style="padding: 10px 12px;">Direction</th>
              <th style="padding: 10px 12px; text-align: right;">Amount (PKR)</th>
              <th style="padding: 10px 12px; text-align: right;">Allocated</th>
              <th style="padding: 10px 12px;">Status</th>
              <th style="padding: 10px 12px; text-align: center;">Action</th>
            </tr>
          </thead>
          <tbody id="ledger-table-body">
            <tr><td colspan="8" style="padding: 24px; text-align: center; color: rgba(255,255,255,0.4);">Loading ledger entries...</td></tr>
          </tbody>
        </table>
      </div>

      <!-- Action Modals Container -->
      <div id="sub-modal-container"></div>
    </div>
  `;

  // Attach Close handler
  container.querySelector('#btn-close-finance')?.addEventListener('click', () => {
    container.remove();
    onClose();
  });
  container.querySelector('.drawer-backdrop')?.addEventListener('click', () => {
    container.remove();
    onClose();
  });

  // State
  let currentSummary = null;

  async function loadData() {
    try {
      const [agRes, sumRes, ledgerRes] = await Promise.all([
        fetchSupplierAgreement(supplier.id),
        fetchSupplierLedgerSummary(supplier.id),
        fetchSupplierLedger(supplier.id, 1, 100),
      ]);

      // Populate agreement form
      const triggerSel = container.querySelector('#sel-payable-trigger');
      if (triggerSel) triggerSel.value = agRes.payable_trigger || 'manual';
      const termsInp = container.querySelector('#inp-payment-terms');
      if (termsInp) termsInp.value = agRes.payment_terms_days || 0;
      const notesInp = container.querySelector('#inp-agreement-notes');
      if (notesInp) notesInp.value = agRes.notes || '';

      // Populate KPIs
      currentSummary = sumRes;
      container.querySelector('#kpi-outstanding').textContent = formatPkr(sumRes.outstanding_payable_minor);
      container.querySelector('#kpi-charges').textContent = formatPkr(sumRes.total_charges_minor);
      container.querySelector('#kpi-credits').textContent = formatPkr(sumRes.total_credits_minor);
      container.querySelector('#kpi-payments').textContent = formatPkr(sumRes.total_payments_minor);
      const advKpi = container.querySelector('#kpi-advances');
      if (advKpi) advKpi.textContent = formatPkr(sumRes.unallocated_advances_minor || 0);

      // Populate Table
      renderLedgerRows(ledgerRes.entries || []);
    } catch (err) {
      console.error('Failed to load supplier finance:', err);
      const tbody = container.querySelector('#ledger-table-body');
      if (tbody) tbody.innerHTML = `<tr><td colspan="8" style="padding: 20px; text-align: center; color: #F87171;">Failed to load finance data: ${escapeHtml(err.message || 'Error')}</td></tr>`;
    }
  }

  function renderLedgerRows(entries) {
    const tbody = container.querySelector('#ledger-table-body');
    if (!tbody) return;

    if (!entries.length) {
      tbody.innerHTML = `<tr><td colspan="8" style="padding: 24px; text-align: center; color: rgba(255,255,255,0.4);">No financial ledger entries recorded for this supplier yet.</td></tr>`;
      return;
    }

    tbody.innerHTML = entries.map(e => {
      const isReversed = e.status === 'reversed';
      const isAdjustment = e.entry_type === 'adjustment';
      const isCredit = e.direction === 'credit';
      const amountColor = isCredit ? '#34D399' : '#F87171';
      const sign = isCredit ? '+' : '-';

      const isPaymentOrAdvance = e.entry_type === 'payment' || e.entry_type === 'advance';
      const isChargeOrOB = e.entry_type === 'charge' || e.entry_type === 'opening_balance';

      let allocText = '—';
      if ((isPaymentOrAdvance || isChargeOrOB) && !isReversed) {
        allocText = `${formatPkr(e.allocated_amount_minor || 0)}`;
        if (e.unallocated_amount_minor && e.unallocated_amount_minor > 0) {
          allocText += ` <span style="font-size:0.65rem; color:#FBBF24;">(Rem: ${formatPkr(e.unallocated_amount_minor)})</span>`;
        }
      }

      const canAllocate = isPaymentOrAdvance && !isReversed && e.unallocated_amount_minor && e.unallocated_amount_minor > 0;

      return `
        <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.06); ${isReversed ? 'opacity: 0.5; text-decoration: line-through;' : ''}">
          <td style="padding: 10px 12px; font-family: monospace; color: rgba(255,255,255,0.8);">${escapeHtml(e.effective_date)}</td>
          <td style="padding: 10px 12px; font-weight: 600;">
            ${escapeHtml(e.reference)}
            ${e.notes ? `<div style="font-size: 0.7rem; color: rgba(255,255,255,0.5); font-weight: 400;">${escapeHtml(e.notes)}</div>` : ''}
          </td>
          <td style="padding: 10px 12px;">
            <span style="display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; font-family: monospace; background: rgba(255,255,255,0.08);">
              ${escapeHtml(e.entry_type)}
            </span>
          </td>
          <td style="padding: 10px 12px; text-transform: uppercase; font-size: 0.75rem; color: ${amountColor};">
            ${escapeHtml(e.direction)}
          </td>
          <td style="padding: 10px 12px; text-align: right; font-weight: 700; color: ${amountColor};">
            ${sign} ${formatPkr(e.amount_minor)}
          </td>
          <td style="padding: 10px 12px; text-align: right; font-size: 0.75rem; color: rgba(255,255,255,0.7);">
            ${allocText}
          </td>
          <td style="padding: 10px 12px;">
            <span class="badge ${isReversed ? 'badge-neutral' : 'badge-accent'}" style="font-size: 0.65rem;">
              ${escapeHtml(e.status)}
            </span>
          </td>
          <td style="padding: 10px 12px; text-align: center;">
            <div style="display: flex; gap: 4px; justify-content: center;">
              ${canAllocate ? `
                <button class="btn-allocate-entry" data-entry-id="${e.id}" data-ref="${escapeHtml(e.reference)}" data-avail="${e.unallocated_amount_minor}" style="background: rgba(251, 191, 36, 0.2); border: 1px solid #FBBF24; color: #FBBF24; padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; cursor: pointer;">
                  Allocate
                </button>
              ` : ''}
              ${!isReversed && !isAdjustment ? `
                <button class="btn-reverse-entry" data-entry-id="${e.id}" data-ref="${escapeHtml(e.reference)}" style="background: none; border: 1px solid rgba(248, 113, 113, 0.4); color: #F87171; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; cursor: pointer;">
                  Reverse
                </button>
              ` : '—'}
            </div>
          </td>
        </tr>
      `;
    }).join('');

    // Attach Reversal listeners
    tbody.querySelectorAll('.btn-reverse-entry').forEach(btn => {
      btn.addEventListener('click', () => {
        const entryId = btn.getAttribute('data-entry-id');
        const ref = btn.getAttribute('data-ref');
        openReverseModal(entryId, ref);
      });
    });

    // Attach Allocation listeners
    tbody.querySelectorAll('.btn-allocate-entry').forEach(btn => {
      btn.addEventListener('click', () => {
        const entryId = btn.getAttribute('data-entry-id');
        const ref = btn.getAttribute('data-ref');
        const avail = parseInt(btn.getAttribute('data-avail'), 10) || 0;
        openAllocateModal(entryId, ref, avail);
      });
    });
  }

  // Save Agreement Handler
  const agreementForm = container.querySelector('#agreement-form');
  agreementForm?.addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const btn = container.querySelector('#btn-save-agreement');
    const feedback = container.querySelector('#agreement-feedback');
    const trigger = container.querySelector('#sel-payable-trigger').value;
    const terms = parseInt(container.querySelector('#inp-payment-terms').value, 10) || 0;
    const notes = container.querySelector('#inp-agreement-notes').value.trim();

    btn.disabled = true;
    btn.textContent = 'Saving...';
    feedback.textContent = '';

    try {
      await updateSupplierAgreement(supplier.id, {
        payable_trigger: trigger,
        payment_terms_days: terms,
        notes: notes || undefined,
      });
      feedback.textContent = '✓ Agreement terms saved successfully';
      setTimeout(() => { feedback.textContent = ''; }, 3000);
      await loadData();
    } catch (err) {
      alert(`Failed to save agreement: ${err.message || 'Error'}`);
    } finally {
      btn.disabled = false;
      btn.textContent = 'Save Agreement Terms';
    }
  });

  // Reversal Modal
  function openReverseModal(entryId, ref) {
    const subContainer = container.querySelector('#sub-modal-container');
    if (!subContainer) return;

    subContainer.innerHTML = `
      <div class="drawer-backdrop" style="position: fixed; inset: 0; background: rgba(0,0,0,0.75); z-index: 1010;"></div>
      <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 1020; background: #1B201D; border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 8px; padding: 20px; width: 400px; max-width: 90%; box-shadow: 0 20px 40px rgba(0,0,0,0.8);">
        <h4 style="margin-top: 0; font-size: 1rem; color: #F87171;">Reverse Entry: ${escapeHtml(ref)}</h4>
        <p style="font-size: 0.75rem; color: rgba(255,255,255,0.7); margin-bottom: 12px;">
          This will immutably mark the entry as reversed and generate an opposing adjustment entry. Please state the audit reason.
        </p>
        <form id="reversal-form">
          <label style="font-size: 0.75rem; color: rgba(255,255,255,0.8); display: block; margin-bottom: 4px;">Reversal Reason *</label>
          <input type="text" id="reversal-reason" required placeholder="e.g. Invoiced wrong supplier account" style="width: 100%; padding: 8px; background: #111413; border: 1px solid rgba(255,255,255,0.2); color: #FFF; border-radius: 4px; font-size: 0.8125rem; margin-bottom: 14px;" />
          <div style="display: flex; justify-content: flex-end; gap: 8px;">
            <button type="button" id="btn-cancel-reversal" class="btn" style="background: none; border: 1px solid rgba(255,255,255,0.2); color: #FFF; font-size: 0.75rem; padding: 6px 12px; border-radius: 4px;">Cancel</button>
            <button type="submit" id="btn-confirm-reversal" class="btn" style="background: #F87171; color: #000; font-weight: 700; font-size: 0.75rem; padding: 6px 12px; border-radius: 4px;">Confirm Reversal</button>
          </div>
        </form>
      </div>
    `;

    subContainer.querySelector('#btn-cancel-reversal')?.addEventListener('click', () => { subContainer.innerHTML = ''; });
    subContainer.querySelector('.drawer-backdrop')?.addEventListener('click', () => { subContainer.innerHTML = ''; });

    subContainer.querySelector('#reversal-form')?.addEventListener('submit', async (ev) => {
      ev.preventDefault();
      const reason = subContainer.querySelector('#reversal-reason').value.trim();
      const btn = subContainer.querySelector('#btn-confirm-reversal');
      btn.disabled = true;
      btn.textContent = 'Reversing...';

      try {
        await reverseSupplierLedgerEntry(entryId, reason, supplier.id);
        subContainer.innerHTML = '';
        await loadData();
      } catch (err) {
        alert(`Failed to reverse entry: ${err.message || 'Error'}`);
        btn.disabled = false;
        btn.textContent = 'Confirm Reversal';
      }
    });
  }

  // VF2: Record Payment Modal
  container.querySelector('#btn-open-payment-modal')?.addEventListener('click', () => {
    openPaymentModal();
  });

  async function openPaymentModal() {
    const subContainer = container.querySelector('#sub-modal-container');
    if (!subContainer) return;

    const todayStr = new Date().toISOString().split('T')[0];
    let unpaidData = { unpaid_charges: [] };

    try {
      unpaidData = await fetchSupplierUnpaidAndAdvances(supplier.id);
    } catch (e) {
      console.warn('Could not fetch unpaid charges:', e);
    }

    subContainer.innerHTML = `
      <div class="drawer-backdrop" style="position: fixed; inset: 0; background: rgba(0,0,0,0.75); z-index: 1010;"></div>
      <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 1020; background: #1B201D; border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 8px; padding: 22px; width: 520px; max-width: 92%; box-shadow: 0 25px 50px rgba(0,0,0,0.85); max-height: 85vh; overflow-y: auto;">
        <h4 style="margin-top: 0; font-size: 1.05rem; color: #34D399;">💸 Record Supplier Payment</h4>
        <p style="font-size: 0.75rem; color: rgba(255,255,255,0.7); margin-bottom: 12px;">
          Records an actual cash/bank disbursement to the vendor. Allocates against charges and reduces payable liability.
        </p>
        <form id="payment-form" style="display: flex; flex-direction: column; gap: 10px;">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
            <div>
              <label style="font-size: 0.75rem; color: rgba(255,255,255,0.8); display: block; margin-bottom: 2px;">Payment Amount PKR *</label>
              <input type="number" id="payment-amount" required min="1" step="0.01" placeholder="e.g. 25000.00" style="width: 100%; padding: 8px; background: #111413; border: 1px solid rgba(255,255,255,0.2); color: #FFF; border-radius: 4px; font-size: 0.8125rem;" />
            </div>
            <div>
              <label style="font-size: 0.75rem; color: rgba(255,255,255,0.8); display: block; margin-bottom: 2px;">Method *</label>
              <select id="payment-method" required style="width: 100%; padding: 8px; background: #111413; border: 1px solid rgba(255,255,255,0.2); color: #FFF; border-radius: 4px; font-size: 0.8125rem;">
                <option value="bank_transfer">Bank Transfer (IBAN/Raast)</option>
                <option value="cash">Cash Voucher</option>
                <option value="cheque">Cheque</option>
                <option value="online">Online Payment</option>
              </select>
            </div>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
            <div>
              <label style="font-size: 0.75rem; color: rgba(255,255,255,0.8); display: block; margin-bottom: 2px;">Transfer Reference # *</label>
              <input type="text" id="payment-ref" required placeholder="e.g. HBL-TRX-98213" style="width: 100%; padding: 8px; background: #111413; border: 1px solid rgba(255,255,255,0.2); color: #FFF; border-radius: 4px; font-size: 0.8125rem;" />
            </div>
            <div>
              <label style="font-size: 0.75rem; color: rgba(255,255,255,0.8); display: block; margin-bottom: 2px;">Disbursement Date *</label>
              <input type="date" id="payment-date" required value="${todayStr}" style="width: 100%; padding: 8px; background: #111413; border: 1px solid rgba(255,255,255,0.2); color: #FFF; border-radius: 4px; font-size: 0.8125rem;" />
            </div>
          </div>
          <div>
            <label style="font-size: 0.75rem; color: rgba(255,255,255,0.8); display: block; margin-bottom: 2px;">Payment Notes / Banking Remarks</label>
            <input type="text" id="payment-notes" placeholder="e.g. Weekly vendor settlement" style="width: 100%; padding: 8px; background: #111413; border: 1px solid rgba(255,255,255,0.2); color: #FFF; border-radius: 4px; font-size: 0.8125rem;" />
          </div>

          <!-- Allocation Strategy -->
          <div style="background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 10px; margin-top: 4px;">
            <label style="display: flex; align-items: center; gap: 8px; font-size: 0.8125rem; font-weight: 600; cursor: pointer;">
              <input type="checkbox" id="payment-fifo-toggle" checked />
              <span>Auto-allocate to oldest unpaid charges (FIFO)</span>
            </label>
            <div id="fifo-hint" style="font-size: 0.7rem; color: rgba(255,255,255,0.5); margin-top: 4px; padding-left: 24px;">
              Payment will automatically extinguish charges in chronological order. Any remainder stays as an unallocated advance.
            </div>
          </div>

          <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 10px;">
            <button type="button" id="btn-cancel-payment" class="btn" style="background: none; border: 1px solid rgba(255,255,255,0.2); color: #FFF; font-size: 0.75rem; padding: 6px 12px; border-radius: 4px;">Cancel</button>
            <button type="submit" id="btn-save-payment" class="btn btn-primary" style="font-size: 0.75rem; padding: 6px 14px; border-radius: 4px;">Record Payment</button>
          </div>
        </form>
      </div>
    `;

    subContainer.querySelector('#btn-cancel-payment')?.addEventListener('click', () => { subContainer.innerHTML = ''; });
    subContainer.querySelector('.drawer-backdrop')?.addEventListener('click', () => { subContainer.innerHTML = ''; });

    subContainer.querySelector('#payment-form')?.addEventListener('submit', async (ev) => {
      ev.preventDefault();
      const amountPkr = subContainer.querySelector('#payment-amount').value;
      const method = subContainer.querySelector('#payment-method').value;
      const ref = subContainer.querySelector('#payment-ref').value.trim();
      const effDate = subContainer.querySelector('#payment-date').value;
      const notes = subContainer.querySelector('#payment-notes').value.trim();
      const fifo = subContainer.querySelector('#payment-fifo-toggle').checked;
      const btn = subContainer.querySelector('#btn-save-payment');

      const amountMinor = parseCatalogPkr(amountPkr);
      if (amountMinor === null || amountMinor <= 0) {
        alert('Please enter a valid positive payment amount in PKR.');
        return;
      }

      btn.disabled = true;
      btn.textContent = 'Recording...';

      try {
        await postSupplierPayment(supplier.id, {
          amount_minor: amountMinor,
          payment_method: method,
          reference: ref,
          effective_date: effDate,
          notes: notes || undefined,
          auto_allocate_fifo: fifo,
        });
        subContainer.innerHTML = '';
        await loadData();
      } catch (err) {
        alert(`Failed to record payment: ${err.message || 'Error'}`);
        btn.disabled = false;
        btn.textContent = 'Record Payment';
      }
    });
  }

  // VF2: Disburse Advance Modal
  container.querySelector('#btn-open-advance-modal')?.addEventListener('click', () => {
    openAdvanceModal();
  });

  function openAdvanceModal() {
    const subContainer = container.querySelector('#sub-modal-container');
    if (!subContainer) return;

    const todayStr = new Date().toISOString().split('T')[0];

    subContainer.innerHTML = `
      <div class="drawer-backdrop" style="position: fixed; inset: 0; background: rgba(0,0,0,0.75); z-index: 1010;"></div>
      <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 1020; background: #1B201D; border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 8px; padding: 22px; width: 460px; max-width: 92%; box-shadow: 0 25px 50px rgba(0,0,0,0.85);">
        <h4 style="margin-top: 0; font-size: 1.05rem; color: #FBBF24;">⚡ Disburse Supplier Advance</h4>
        <p style="font-size: 0.75rem; color: rgba(255,255,255,0.7); margin-bottom: 12px;">
          Records an unallocated upfront deposit or advance payment to the vendor before charges are incurred.
        </p>
        <form id="advance-form" style="display: flex; flex-direction: column; gap: 10px;">
          <div>
            <label style="font-size: 0.75rem; color: rgba(255,255,255,0.8); display: block; margin-bottom: 2px;">Advance Amount PKR *</label>
            <input type="number" id="advance-amount" required min="1" step="0.01" placeholder="e.g. 50000.00" style="width: 100%; padding: 8px; background: #111413; border: 1px solid rgba(255,255,255,0.2); color: #FFF; border-radius: 4px; font-size: 0.8125rem;" />
          </div>
          <div>
            <label style="font-size: 0.75rem; color: rgba(255,255,255,0.8); display: block; margin-bottom: 2px;">Disbursement Reference / Voucher *</label>
            <input type="text" id="advance-ref" required placeholder="e.g. ADV-FABRIC-001" style="width: 100%; padding: 8px; background: #111413; border: 1px solid rgba(255,255,255,0.2); color: #FFF; border-radius: 4px; font-size: 0.8125rem;" />
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
            <div>
              <label style="font-size: 0.75rem; color: rgba(255,255,255,0.8); display: block; margin-bottom: 2px;">Method *</label>
              <select id="advance-method" required style="width: 100%; padding: 8px; background: #111413; border: 1px solid rgba(255,255,255,0.2); color: #FFF; border-radius: 4px; font-size: 0.8125rem;">
                <option value="bank_transfer">Bank Transfer</option>
                <option value="cash">Cash Voucher</option>
                <option value="cheque">Cheque</option>
              </select>
            </div>
            <div>
              <label style="font-size: 0.75rem; color: rgba(255,255,255,0.8); display: block; margin-bottom: 2px;">Effective Date *</label>
              <input type="date" id="advance-date" required value="${todayStr}" style="width: 100%; padding: 8px; background: #111413; border: 1px solid rgba(255,255,255,0.2); color: #FFF; border-radius: 4px; font-size: 0.8125rem;" />
            </div>
          </div>
          <div>
            <label style="font-size: 0.75rem; color: rgba(255,255,255,0.8); display: block; margin-bottom: 2px;">Purpose / Notes</label>
            <input type="text" id="advance-notes" placeholder="e.g. Booking deposit for winter collection production" style="width: 100%; padding: 8px; background: #111413; border: 1px solid rgba(255,255,255,0.2); color: #FFF; border-radius: 4px; font-size: 0.8125rem;" />
          </div>
          <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 10px;">
            <button type="button" id="btn-cancel-advance" class="btn" style="background: none; border: 1px solid rgba(255,255,255,0.2); color: #FFF; font-size: 0.75rem; padding: 6px 12px; border-radius: 4px;">Cancel</button>
            <button type="submit" id="btn-save-advance" class="btn" style="background: #FBBF24; color: #000; font-weight: 700; font-size: 0.75rem; padding: 6px 14px; border-radius: 4px;">Disburse Advance</button>
          </div>
        </form>
      </div>
    `;

    subContainer.querySelector('#btn-cancel-advance')?.addEventListener('click', () => { subContainer.innerHTML = ''; });
    subContainer.querySelector('.drawer-backdrop')?.addEventListener('click', () => { subContainer.innerHTML = ''; });

    subContainer.querySelector('#advance-form')?.addEventListener('submit', async (ev) => {
      ev.preventDefault();
      const amountPkr = subContainer.querySelector('#advance-amount').value;
      const ref = subContainer.querySelector('#advance-ref').value.trim();
      const method = subContainer.querySelector('#advance-method').value;
      const effDate = subContainer.querySelector('#advance-date').value;
      const notes = subContainer.querySelector('#advance-notes').value.trim();
      const btn = subContainer.querySelector('#btn-save-advance');

      const amountMinor = parseCatalogPkr(amountPkr);
      if (amountMinor === null || amountMinor <= 0) {
        alert('Please enter a valid positive advance amount in PKR.');
        return;
      }

      btn.disabled = true;
      btn.textContent = 'Disbursing...';

      try {
        await postSupplierAdvance(supplier.id, {
          amount_minor: amountMinor,
          payment_method: method,
          reference: ref,
          effective_date: effDate,
          notes: notes || undefined,
        });
        subContainer.innerHTML = '';
        await loadData();
      } catch (err) {
        alert(`Failed to disburse advance: ${err.message || 'Error'}`);
        btn.disabled = false;
        btn.textContent = 'Disburse Advance';
      }
    });
  }

  // VF2: Supplier Refund Received Modal
  container.querySelector('#btn-open-refund-modal')?.addEventListener('click', () => {
    openRefundModal();
  });

  function openRefundModal() {
    const subContainer = container.querySelector('#sub-modal-container');
    if (!subContainer) return;

    const todayStr = new Date().toISOString().split('T')[0];

    subContainer.innerHTML = `
      <div class="drawer-backdrop" style="position: fixed; inset: 0; background: rgba(0,0,0,0.75); z-index: 1010;"></div>
      <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 1020; background: #1B201D; border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 8px; padding: 22px; width: 460px; max-width: 92%; box-shadow: 0 25px 50px rgba(0,0,0,0.85);">
        <h4 style="margin-top: 0; font-size: 1.05rem; color: #60A5FA;">📥 Record Supplier Cash Refund</h4>
        <p style="font-size: 0.75rem; color: rgba(255,255,255,0.7); margin-bottom: 12px;">
          Records actual funds refunded by the vendor to AlphaZee (e.g. cancelled order or defect cash refund).
        </p>
        <form id="refund-form" style="display: flex; flex-direction: column; gap: 10px;">
          <div>
            <label style="font-size: 0.75rem; color: rgba(255,255,255,0.8); display: block; margin-bottom: 2px;">Refund Amount PKR *</label>
            <input type="number" id="refund-amount" required min="1" step="0.01" placeholder="e.g. 10000.00" style="width: 100%; padding: 8px; background: #111413; border: 1px solid rgba(255,255,255,0.2); color: #FFF; border-radius: 4px; font-size: 0.8125rem;" />
          </div>
          <div>
            <label style="font-size: 0.75rem; color: rgba(255,255,255,0.8); display: block; margin-bottom: 2px;">Vendor Refund Voucher / Bank Ref *</label>
            <input type="text" id="refund-ref" required placeholder="e.g. VEND-REF-2026-99" style="width: 100%; padding: 8px; background: #111413; border: 1px solid rgba(255,255,255,0.2); color: #FFF; border-radius: 4px; font-size: 0.8125rem;" />
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
            <div>
              <label style="font-size: 0.75rem; color: rgba(255,255,255,0.8); display: block; margin-bottom: 2px;">Method *</label>
              <select id="refund-method" required style="width: 100%; padding: 8px; background: #111413; border: 1px solid rgba(255,255,255,0.2); color: #FFF; border-radius: 4px; font-size: 0.8125rem;">
                <option value="bank_transfer">Bank Transfer Received</option>
                <option value="cash">Cash Received</option>
                <option value="cheque">Cheque Cleared</option>
              </select>
            </div>
            <div>
              <label style="font-size: 0.75rem; color: rgba(255,255,255,0.8); display: block; margin-bottom: 2px;">Effective Date *</label>
              <input type="date" id="refund-date" required value="${todayStr}" style="width: 100%; padding: 8px; background: #111413; border: 1px solid rgba(255,255,255,0.2); color: #FFF; border-radius: 4px; font-size: 0.8125rem;" />
            </div>
          </div>
          <div>
            <label style="font-size: 0.75rem; color: rgba(255,255,255,0.8); display: block; margin-bottom: 2px;">Reason / Notes</label>
            <input type="text" id="refund-notes" placeholder="e.g. Defective roll refund transferred to Meezan account" style="width: 100%; padding: 8px; background: #111413; border: 1px solid rgba(255,255,255,0.2); color: #FFF; border-radius: 4px; font-size: 0.8125rem;" />
          </div>
          <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 10px;">
            <button type="button" id="btn-cancel-refund" class="btn" style="background: none; border: 1px solid rgba(255,255,255,0.2); color: #FFF; font-size: 0.75rem; padding: 6px 12px; border-radius: 4px;">Cancel</button>
            <button type="submit" id="btn-save-refund" class="btn" style="background: #60A5FA; color: #000; font-weight: 700; font-size: 0.75rem; padding: 6px 14px; border-radius: 4px;">Record Refund</button>
          </div>
        </form>
      </div>
    `;

    subContainer.querySelector('#btn-cancel-refund')?.addEventListener('click', () => { subContainer.innerHTML = ''; });
    subContainer.querySelector('.drawer-backdrop')?.addEventListener('click', () => { subContainer.innerHTML = ''; });

    subContainer.querySelector('#refund-form')?.addEventListener('submit', async (ev) => {
      ev.preventDefault();
      const amountPkr = subContainer.querySelector('#refund-amount').value;
      const ref = subContainer.querySelector('#refund-ref').value.trim();
      const method = subContainer.querySelector('#refund-method').value;
      const effDate = subContainer.querySelector('#refund-date').value;
      const notes = subContainer.querySelector('#refund-notes').value.trim();
      const btn = subContainer.querySelector('#btn-save-refund');

      const amountMinor = parseCatalogPkr(amountPkr);
      if (amountMinor === null || amountMinor <= 0) {
        alert('Please enter a valid positive refund amount in PKR.');
        return;
      }

      btn.disabled = true;
      btn.textContent = 'Recording...';

      try {
        await postSupplierRefund(supplier.id, {
          amount_minor: amountMinor,
          refund_method: method,
          reference: ref,
          effective_date: effDate,
          notes: notes || undefined,
        });
        subContainer.innerHTML = '';
        await loadData();
      } catch (err) {
        alert(`Failed to record refund: ${err.message || 'Error'}`);
        btn.disabled = false;
        btn.textContent = 'Record Refund';
      }
    });
  }

  // VF2: Allocate Payment/Advance to Charge Modal
  async function openAllocateModal(paymentId, ref, availMinor) {
    const subContainer = container.querySelector('#sub-modal-container');
    if (!subContainer) return;

    let unpaidCharges = [];
    try {
      const res = await fetchSupplierUnpaidAndAdvances(supplier.id);
      unpaidCharges = res.unpaid_charges || [];
    } catch (e) {
      console.warn('Could not fetch unpaid charges:', e);
    }

    if (!unpaidCharges.length) {
      alert('There are no open unpaid charges for this supplier to allocate against.');
      return;
    }

    subContainer.innerHTML = `
      <div class="drawer-backdrop" style="position: fixed; inset: 0; background: rgba(0,0,0,0.75); z-index: 1010;"></div>
      <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 1020; background: #1B201D; border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 8px; padding: 22px; width: 480px; max-width: 92%; box-shadow: 0 25px 50px rgba(0,0,0,0.85);">
        <h4 style="margin-top: 0; font-size: 1.05rem; color: #FBBF24;">🔗 Allocate Payment Funds: ${escapeHtml(ref)}</h4>
        <p style="font-size: 0.75rem; color: rgba(255,255,255,0.7); margin-bottom: 12px;">
          Available to allocate from this payment: <strong>${formatPkr(availMinor)}</strong>
        </p>
        <form id="allocate-form" style="display: flex; flex-direction: column; gap: 10px;">
          <div>
            <label style="font-size: 0.75rem; color: rgba(255,255,255,0.8); display: block; margin-bottom: 2px;">Select Charge to Settle *</label>
            <select id="sel-target-charge" required style="width: 100%; padding: 8px; background: #111413; border: 1px solid rgba(255,255,255,0.2); color: #FFF; border-radius: 4px; font-size: 0.8125rem;">
              ${unpaidCharges.map(c => `
                <option value="${c.id}" data-unpaid="${c.unpaid_amount_minor}">
                  ${escapeHtml(c.reference)} (${c.effective_date}) — Unpaid: ${formatPkr(c.unpaid_amount_minor)}
                </option>
              `).join('')}
            </select>
          </div>
          <div>
            <label style="font-size: 0.75rem; color: rgba(255,255,255,0.8); display: block; margin-bottom: 2px;">Allocation Amount PKR *</label>
            <input type="number" id="alloc-amount" required min="1" step="0.01" style="width: 100%; padding: 8px; background: #111413; border: 1px solid rgba(255,255,255,0.2); color: #FFF; border-radius: 4px; font-size: 0.8125rem;" />
          </div>
          <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 10px;">
            <button type="button" id="btn-cancel-alloc" class="btn" style="background: none; border: 1px solid rgba(255,255,255,0.2); color: #FFF; font-size: 0.75rem; padding: 6px 12px; border-radius: 4px;">Cancel</button>
            <button type="submit" id="btn-save-alloc" class="btn" style="background: #FBBF24; color: #000; font-weight: 700; font-size: 0.75rem; padding: 6px 14px; border-radius: 4px;">Commit Allocation</button>
          </div>
        </form>
      </div>
    `;

    subContainer.querySelector('#btn-cancel-alloc')?.addEventListener('click', () => { subContainer.innerHTML = ''; });
    subContainer.querySelector('.drawer-backdrop')?.addEventListener('click', () => { subContainer.innerHTML = ''; });

    subContainer.querySelector('#allocate-form')?.addEventListener('submit', async (ev) => {
      ev.preventDefault();
      const chargeId = subContainer.querySelector('#sel-target-charge').value;
      const amountPkr = subContainer.querySelector('#alloc-amount').value;
      const btn = subContainer.querySelector('#btn-save-alloc');

      const amountMinor = parseCatalogPkr(amountPkr);
      if (amountMinor === null || amountMinor <= 0) {
        alert('Please enter a valid positive allocation amount in PKR.');
        return;
      }
      if (amountMinor > availMinor) {
        alert(`Allocation amount cannot exceed available balance of ${formatPkr(availMinor)}.`);
        return;
      }

      btn.disabled = true;
      btn.textContent = 'Allocating...';

      try {
        await allocateSupplierPayment(supplier.id, paymentId, {
          charge_entry_id: chargeId,
          amount_minor: amountMinor,
        });
        subContainer.innerHTML = '';
        await loadData();
      } catch (err) {
        alert(`Failed to allocate: ${err.message || 'Error'}`);
        btn.disabled = false;
        btn.textContent = 'Commit Allocation';
      }
    });
  }

  // VF2: Period Statement Modal
  container.querySelector('#btn-open-statement-modal')?.addEventListener('click', () => {
    openStatementModal();
  });

  function openStatementModal() {
    const subContainer = container.querySelector('#sub-modal-container');
    if (!subContainer) return;

    const today = new Date();
    const firstDay = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().split('T')[0];
    const todayStr = today.toISOString().split('T')[0];

    subContainer.innerHTML = `
      <div class="drawer-backdrop" style="position: fixed; inset: 0; background: rgba(0,0,0,0.75); z-index: 1010;"></div>
      <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 1020; background: #141715; border: 1px solid rgba(255, 255, 255, 0.25); border-radius: 10px; padding: 24px; width: 900px; max-width: 95%; box-shadow: 0 30px 60px rgba(0,0,0,0.9); max-height: 90vh; overflow-y: auto;">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 12px; margin-bottom: 16px;">
          <div>
            <h3 style="margin: 0; font-size: 1.15rem; color: #38BDF8;">📜 Supplier Period Statement & Reconciliation</h3>
            <p style="margin: 4px 0 0 0; font-size: 0.75rem; color: rgba(255,255,255,0.6);">
              ${escapeHtml(supplier.name)} &bull; Exact Paisa Opening, Movement & Closing Balance Reconciliation
            </p>
          </div>
          <button id="btn-close-statement" class="btn-icon" style="background: none; border: none; color: #FFF; font-size: 1.3rem; cursor: pointer;">&times;</button>
        </div>

        <!-- Filter bar -->
        <div style="display: flex; flex-wrap: wrap; gap: 10px; align-items: flex-end; background: #1B201D; border-radius: 6px; padding: 12px; margin-bottom: 16px;">
          <div>
            <label style="font-size: 0.75rem; color: rgba(255,255,255,0.7); display: block; margin-bottom: 2px;">Start Date (Inclusive)</label>
            <input type="date" id="stmt-start-date" value="${firstDay}" style="padding: 6px 10px; background: #111413; border: 1px solid rgba(255,255,255,0.2); color: #FFF; border-radius: 4px; font-size: 0.8125rem;" />
          </div>
          <div>
            <label style="font-size: 0.75rem; color: rgba(255,255,255,0.7); display: block; margin-bottom: 2px;">End Date (Inclusive)</label>
            <input type="date" id="stmt-end-date" value="${todayStr}" style="padding: 6px 10px; background: #111413; border: 1px solid rgba(255,255,255,0.2); color: #FFF; border-radius: 4px; font-size: 0.8125rem;" />
          </div>
          <button id="btn-run-statement" class="btn btn-primary" style="font-size: 0.8125rem; padding: 7px 16px; border-radius: 4px;">
            Generate Statement
          </button>
        </div>

        <!-- Statement Output Container -->
        <div id="statement-output">
          <p style="text-align: center; color: rgba(255,255,255,0.5); padding: 20px;">Click "Generate Statement" to load period reconciliation.</p>
        </div>
      </div>
    `;

    subContainer.querySelector('#btn-close-statement')?.addEventListener('click', () => { subContainer.innerHTML = ''; });
    subContainer.querySelector('.drawer-backdrop')?.addEventListener('click', () => { subContainer.innerHTML = ''; });

    const btnRun = subContainer.querySelector('#btn-run-statement');
    btnRun?.addEventListener('click', async () => {
      const sDate = subContainer.querySelector('#stmt-start-date').value;
      const eDate = subContainer.querySelector('#stmt-end-date').value;
      const out = subContainer.querySelector('#statement-output');

      if (!sDate || !eDate) {
        alert('Please choose both start and end dates.');
        return;
      }

      btnRun.disabled = true;
      btnRun.textContent = 'Generating...';
      out.innerHTML = `<p style="text-align: center; color: rgba(255,255,255,0.5); padding: 20px;">Calculating balances and loading entries...</p>`;

      try {
        const stmt = await fetchSupplierStatement(supplier.id, sDate, eDate);

        const openBal = stmt.opening_payable_minor;
        const movement = stmt.net_movement_minor;
        const closeBal = stmt.closing_payable_minor;
        const isReconciled = (openBal + movement) === closeBal;

        out.innerHTML = `
          <!-- Summary Cards -->
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 8px; margin-bottom: 14px;">
            <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 10px;">
              <div style="font-size: 0.7rem; color: rgba(255,255,255,0.5); text-transform: uppercase;">Opening Payable</div>
              <div style="font-size: 1rem; font-weight: 700; color: #FFF; margin-top: 2px;">${formatPkr(openBal)}</div>
            </div>
            <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 10px;">
              <div style="font-size: 0.7rem; color: rgba(255,255,255,0.5); text-transform: uppercase;">Period Charges (+)</div>
              <div style="font-size: 1rem; font-weight: 700; color: #34D399; margin-top: 2px;">+ ${formatPkr(stmt.charges_in_period_minor)}</div>
            </div>
            <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 10px;">
              <div style="font-size: 0.7rem; color: rgba(255,255,255,0.5); text-transform: uppercase;">Vendor Refunds (+)</div>
              <div style="font-size: 1rem; font-weight: 700; color: #60A5FA; margin-top: 2px;">+ ${formatPkr(stmt.refunds_in_period_minor)}</div>
            </div>
            <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 10px;">
              <div style="font-size: 0.7rem; color: rgba(255,255,255,0.5); text-transform: uppercase;">Credit Notes (-)</div>
              <div style="font-size: 1rem; font-weight: 700; color: #F87171; margin-top: 2px;">- ${formatPkr(stmt.credits_in_period_minor)}</div>
            </div>
            <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 10px;">
              <div style="font-size: 0.7rem; color: rgba(255,255,255,0.5); text-transform: uppercase;">Payments Disbursed (-)</div>
              <div style="font-size: 1rem; font-weight: 700; color: #60A5FA; margin-top: 2px;">- ${formatPkr(stmt.payments_in_period_minor)}</div>
            </div>
            <div style="background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 6px; padding: 10px;">
              <div style="font-size: 0.7rem; color: #38BDF8; text-transform: uppercase; font-weight: 600;">Closing Payable</div>
              <div style="font-size: 1.1rem; font-weight: 700; color: #38BDF8; margin-top: 2px;">${formatPkr(closeBal)}</div>
            </div>
          </div>

          <!-- Proof Banner -->
          <div style="background: ${isReconciled ? 'rgba(52, 211, 153, 0.1)' : 'rgba(248, 113, 113, 0.1)'}; border: 1px solid ${isReconciled ? '#34D399' : '#F87171'}; border-radius: 6px; padding: 8px 14px; font-size: 0.75rem; margin-bottom: 14px; display: flex; align-items: center; justify-content: space-between;">
            <span>
              <strong>Accounting Proof:</strong> ${formatPkr(openBal)} (Opening) + (${formatPkr(movement)} Movement) = <strong>${formatPkr(closeBal)}</strong> (Closing Balance)
            </span>
            <span class="badge ${isReconciled ? 'badge-accent' : 'badge-danger'}" style="font-size: 0.65rem;">
              ${isReconciled ? '✓ RECONCILED' : 'DISCREPANCY'}
            </span>
          </div>

          <!-- Entries Table with Running Balance -->
          <div style="max-height: 400px; overflow-y: auto; border: 1px solid rgba(255,255,255,0.1); border-radius: 6px;">
            <table style="width: 100%; border-collapse: collapse; font-size: 0.75rem; text-align: left;">
              <thead style="background: #111413; position: sticky; top: 0; z-index: 2;">
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.1); color: rgba(255,255,255,0.5);">
                  <th style="padding: 8px 10px;">Date</th>
                  <th style="padding: 8px 10px;">Reference</th>
                  <th style="padding: 8px 10px;">Type</th>
                  <th style="padding: 8px 10px; text-align: right;">Amount</th>
                  <th style="padding: 8px 10px; text-align: right; color: #38BDF8;">Running Payable</th>
                </tr>
              </thead>
              <tbody>
                <tr style="background: rgba(255,255,255,0.02); font-weight: 600; border-bottom: 1px dashed rgba(255,255,255,0.1);">
                  <td style="padding: 6px 10px;">${escapeHtml(sDate)}</td>
                  <td style="padding: 6px 10px;" colspan="3">Opening Balance as of ${escapeHtml(sDate)}</td>
                  <td style="padding: 6px 10px; text-align: right; color: #38BDF8;">${formatPkr(openBal)}</td>
                </tr>
                ${stmt.entries.map(e => {
                  const isCredit = e.direction === 'credit';
                  const sign = isCredit ? '+' : '-';
                  const color = isCredit ? '#34D399' : '#F87171';
                  return `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.04);">
                      <td style="padding: 6px 10px; font-family: monospace;">${escapeHtml(e.effective_date)}</td>
                      <td style="padding: 6px 10px; font-weight: 600;">${escapeHtml(e.reference)}</td>
                      <td style="padding: 6px 10px;"><code>${escapeHtml(e.entry_type)}</code></td>
                      <td style="padding: 6px 10px; text-align: right; color: ${color}; font-weight: 700;">${sign} ${formatPkr(e.amount_minor)}</td>
                      <td style="padding: 6px 10px; text-align: right; font-weight: 700; color: #38BDF8;">${formatPkr(e.running_payable_minor)}</td>
                    </tr>
                  `;
                }).join('')}
              </tbody>
            </table>
          </div>
        `;
      } catch (err) {
        out.innerHTML = `<p style="text-align: center; color: #F87171; padding: 20px;">Failed to generate statement: ${escapeHtml(err.message || 'Error')}</p>`;
      } finally {
        btnRun.disabled = false;
        btnRun.textContent = 'Generate Statement';
      }
    });
  }

  // Manual Charge Modal
  container.querySelector('#btn-open-charge-modal')?.addEventListener('click', () => {
    openChargeModal();
  });

  function openChargeModal() {
    const subContainer = container.querySelector('#sub-modal-container');
    if (!subContainer) return;

    const todayStr = new Date().toISOString().split('T')[0];

    subContainer.innerHTML = `
      <div class="drawer-backdrop" style="position: fixed; inset: 0; background: rgba(0,0,0,0.75); z-index: 1010;"></div>
      <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 1020; background: #1B201D; border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 8px; padding: 20px; width: 440px; max-width: 90%; box-shadow: 0 20px 40px rgba(0,0,0,0.8);">
        <h4 style="margin-top: 0; font-size: 1rem; color: #34D399;">+ Post Manual Supplier Charge</h4>
        <p style="font-size: 0.75rem; color: rgba(255,255,255,0.7); margin-bottom: 12px;">
          Records an approved wholesale liability to the vendor (increases outstanding payable).
        </p>
        <form id="charge-form" style="display: flex; flex-direction: column; gap: 10px;">
          <div>
            <label style="font-size: 0.75rem; color: rgba(255,255,255,0.8); display: block; margin-bottom: 2px;">Amount PKR *</label>
            <input type="number" id="charge-amount" required min="1" step="0.01" placeholder="e.g. 15000.00" style="width: 100%; padding: 8px; background: #111413; border: 1px solid rgba(255,255,255,0.2); color: #FFF; border-radius: 4px; font-size: 0.8125rem;" />
          </div>
          <div>
            <label style="font-size: 0.75rem; color: rgba(255,255,255,0.8); display: block; margin-bottom: 2px;">Invoice / Reference # *</label>
            <input type="text" id="charge-ref" required placeholder="e.g. INV-2026-001" style="width: 100%; padding: 8px; background: #111413; border: 1px solid rgba(255,255,255,0.2); color: #FFF; border-radius: 4px; font-size: 0.8125rem;" />
          </div>
          <div>
            <label style="font-size: 0.75rem; color: rgba(255,255,255,0.8); display: block; margin-bottom: 2px;">Effective Date *</label>
            <input type="date" id="charge-date" required value="${todayStr}" style="width: 100%; padding: 8px; background: #111413; border: 1px solid rgba(255,255,255,0.2); color: #FFF; border-radius: 4px; font-size: 0.8125rem;" />
          </div>
          <div>
            <label style="font-size: 0.75rem; color: rgba(255,255,255,0.8); display: block; margin-bottom: 2px;">Description / Notes</label>
            <input type="text" id="charge-notes" placeholder="e.g. Off-catalog urgent fabric restock" style="width: 100%; padding: 8px; background: #111413; border: 1px solid rgba(255,255,255,0.2); color: #FFF; border-radius: 4px; font-size: 0.8125rem;" />
          </div>
          <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 10px;">
            <button type="button" id="btn-cancel-charge" class="btn" style="background: none; border: 1px solid rgba(255,255,255,0.2); color: #FFF; font-size: 0.75rem; padding: 6px 12px; border-radius: 4px;">Cancel</button>
            <button type="submit" id="btn-save-charge" class="btn btn-primary" style="font-size: 0.75rem; padding: 6px 12px; border-radius: 4px;">Post Charge</button>
          </div>
        </form>
      </div>
    `;

    subContainer.querySelector('#btn-cancel-charge')?.addEventListener('click', () => { subContainer.innerHTML = ''; });
    subContainer.querySelector('.drawer-backdrop')?.addEventListener('click', () => { subContainer.innerHTML = ''; });

    subContainer.querySelector('#charge-form')?.addEventListener('submit', async (ev) => {
      ev.preventDefault();
      const amountPkr = subContainer.querySelector('#charge-amount').value;
      const ref = subContainer.querySelector('#charge-ref').value.trim();
      const effDate = subContainer.querySelector('#charge-date').value;
      const notes = subContainer.querySelector('#charge-notes').value.trim();
      const btn = subContainer.querySelector('#btn-save-charge');

      const amountMinor = parseCatalogPkr(amountPkr);
      if (amountMinor === null || amountMinor <= 0) {
        alert('Please enter a valid positive amount in PKR.');
        return;
      }

      btn.disabled = true;
      btn.textContent = 'Posting...';

      try {
        await postSupplierManualCharge(supplier.id, {
          amount_minor: amountMinor,
          reference: ref,
          effective_date: effDate,
          notes: notes || undefined,
        });
        subContainer.innerHTML = '';
        await loadData();
      } catch (err) {
        alert(`Failed to post charge: ${err.message || 'Error'}`);
        btn.disabled = false;
        btn.textContent = 'Post Charge';
      }
    });
  }

  // Credit Note Modal
  container.querySelector('#btn-open-credit-modal')?.addEventListener('click', () => {
    openCreditModal();
  });

  function openCreditModal() {
    const subContainer = container.querySelector('#sub-modal-container');
    if (!subContainer) return;

    const todayStr = new Date().toISOString().split('T')[0];

    subContainer.innerHTML = `
      <div class="drawer-backdrop" style="position: fixed; inset: 0; background: rgba(0,0,0,0.75); z-index: 1010;"></div>
      <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 1020; background: #1B201D; border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 8px; padding: 20px; width: 440px; max-width: 90%; box-shadow: 0 20px 40px rgba(0,0,0,0.8);">
        <h4 style="margin-top: 0; font-size: 1rem; color: #F87171;">+ Post Supplier Credit Note</h4>
        <p style="font-size: 0.75rem; color: rgba(255,255,255,0.7); margin-bottom: 12px;">
          Records an approved discount or allowance from the vendor (decreases outstanding payable).
        </p>
        <form id="credit-form" style="display: flex; flex-direction: column; gap: 10px;">
          <div>
            <label style="font-size: 0.75rem; color: rgba(255,255,255,0.8); display: block; margin-bottom: 2px;">Credit Amount PKR *</label>
            <input type="number" id="credit-amount" required min="1" step="0.01" placeholder="e.g. 5000.00" style="width: 100%; padding: 8px; background: #111413; border: 1px solid rgba(255,255,255,0.2); color: #FFF; border-radius: 4px; font-size: 0.8125rem;" />
          </div>
          <div>
            <label style="font-size: 0.75rem; color: rgba(255,255,255,0.8); display: block; margin-bottom: 2px;">Credit Note / Reference # *</label>
            <input type="text" id="credit-ref" required placeholder="e.g. CN-2026-004" style="width: 100%; padding: 8px; background: #111413; border: 1px solid rgba(255,255,255,0.2); color: #FFF; border-radius: 4px; font-size: 0.8125rem;" />
          </div>
          <div>
            <label style="font-size: 0.75rem; color: rgba(255,255,255,0.8); display: block; margin-bottom: 2px;">Effective Date *</label>
            <input type="date" id="credit-date" required value="${todayStr}" style="width: 100%; padding: 8px; background: #111413; border: 1px solid rgba(255,255,255,0.2); color: #FFF; border-radius: 4px; font-size: 0.8125rem;" />
          </div>
          <div>
            <label style="font-size: 0.75rem; color: rgba(255,255,255,0.8); display: block; margin-bottom: 2px;">Reason / Notes</label>
            <input type="text" id="credit-notes" placeholder="e.g. Batch defect rebate agreed via WhatsApp" style="width: 100%; padding: 8px; background: #111413; border: 1px solid rgba(255,255,255,0.2); color: #FFF; border-radius: 4px; font-size: 0.8125rem;" />
          </div>
          <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 10px;">
            <button type="button" id="btn-cancel-credit" class="btn" style="background: none; border: 1px solid rgba(255,255,255,0.2); color: #FFF; font-size: 0.75rem; padding: 6px 12px; border-radius: 4px;">Cancel</button>
            <button type="submit" id="btn-save-credit" class="btn btn-primary" style="font-size: 0.75rem; padding: 6px 12px; border-radius: 4px;">Post Credit Note</button>
          </div>
        </form>
      </div>
    `;

    subContainer.querySelector('#btn-cancel-credit')?.addEventListener('click', () => { subContainer.innerHTML = ''; });
    subContainer.querySelector('.drawer-backdrop')?.addEventListener('click', () => { subContainer.innerHTML = ''; });

    subContainer.querySelector('#credit-form')?.addEventListener('submit', async (ev) => {
      ev.preventDefault();
      const amountPkr = subContainer.querySelector('#credit-amount').value;
      const ref = subContainer.querySelector('#credit-ref').value.trim();
      const effDate = subContainer.querySelector('#credit-date').value;
      const notes = subContainer.querySelector('#credit-notes').value.trim();
      const btn = subContainer.querySelector('#btn-save-credit');

      const amountMinor = parseCatalogPkr(amountPkr);
      if (amountMinor === null || amountMinor <= 0) {
        alert('Please enter a valid positive amount in PKR.');
        return;
      }

      btn.disabled = true;
      btn.textContent = 'Posting...';

      try {
        await postSupplierCreditNote(supplier.id, {
          amount_minor: amountMinor,
          reference: ref,
          effective_date: effDate,
          notes: notes || undefined,
        });
        subContainer.innerHTML = '';
        await loadData();
      } catch (err) {
        alert(`Failed to post credit note: ${err.message || 'Error'}`);
        btn.disabled = false;
        btn.textContent = 'Post Credit Note';
      }
    });
  }

  // Opening Balance Modal (Preview first, then apply)
  container.querySelector('#btn-open-opening-balance-modal')?.addEventListener('click', () => {
    openOpeningBalanceModal();
  });

  function openOpeningBalanceModal() {
    const subContainer = container.querySelector('#sub-modal-container');
    if (!subContainer) return;

    const todayStr = new Date().toISOString().split('T')[0];

    subContainer.innerHTML = `
      <div class="drawer-backdrop" style="position: fixed; inset: 0; background: rgba(0,0,0,0.75); z-index: 1010;"></div>
      <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 1020; background: #1B201D; border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 8px; padding: 20px; width: 480px; max-width: 90%; box-shadow: 0 20px 40px rgba(0,0,0,0.8);">
        <h4 style="margin-top: 0; font-size: 1rem; color: #FFFFFF;">⚖ Apply Opening Balance</h4>
        <p style="font-size: 0.75rem; color: rgba(255,255,255,0.7); margin-bottom: 12px;">
          Set historical pre-launch balance with full audit reference. Previews impact before committing.
        </p>
        <form id="ob-form" style="display: flex; flex-direction: column; gap: 10px;">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
            <div>
              <label style="font-size: 0.75rem; color: rgba(255,255,255,0.8); display: block; margin-bottom: 2px;">Amount PKR *</label>
              <input type="number" id="ob-amount" required min="1" step="0.01" placeholder="e.g. 50000.00" style="width: 100%; padding: 8px; background: #111413; border: 1px solid rgba(255,255,255,0.2); color: #FFF; border-radius: 4px; font-size: 0.8125rem;" />
            </div>
            <div>
              <label style="font-size: 0.75rem; color: rgba(255,255,255,0.8); display: block; margin-bottom: 2px;">Direction *</label>
              <select id="ob-direction" required style="width: 100%; padding: 8px; background: #111413; border: 1px solid rgba(255,255,255,0.2); color: #FFF; border-radius: 4px; font-size: 0.8125rem;">
                <option value="credit">Credit (AlphaZee owes vendor)</option>
                <option value="debit">Debit (Vendor owes AlphaZee / Advance)</option>
              </select>
            </div>
          </div>
          <div>
            <label style="font-size: 0.75rem; color: rgba(255,255,255,0.8); display: block; margin-bottom: 2px;">As-of Cut-off Date *</label>
            <input type="date" id="ob-date" required value="${todayStr}" style="width: 100%; padding: 8px; background: #111413; border: 1px solid rgba(255,255,255,0.2); color: #FFF; border-radius: 4px; font-size: 0.8125rem;" />
          </div>
          <div>
            <label style="font-size: 0.75rem; color: rgba(255,255,255,0.8); display: block; margin-bottom: 2px;">Source Statement Reference *</label>
            <input type="text" id="ob-ref" required placeholder="e.g. AUDIT-OCT-2026-STATEMENT" style="width: 100%; padding: 8px; background: #111413; border: 1px solid rgba(255,255,255,0.2); color: #FFF; border-radius: 4px; font-size: 0.8125rem;" />
          </div>
          <div>
            <label style="font-size: 0.75rem; color: rgba(255,255,255,0.8); display: block; margin-bottom: 2px;">Notes / Verification Details</label>
            <input type="text" id="ob-notes" placeholder="Verified against signed supplier ledger statement" style="width: 100%; padding: 8px; background: #111413; border: 1px solid rgba(255,255,255,0.2); color: #FFF; border-radius: 4px; font-size: 0.8125rem;" />
          </div>

          <!-- Preview calculation output -->
          <div id="ob-preview-box" style="display: none; background: rgba(0,0,0,0.3); border: 1px dashed rgba(255,255,255,0.2); border-radius: 6px; padding: 10px; margin-top: 4px;">
            <div style="font-size: 0.75rem; color: rgba(255,255,255,0.6);">Current Balance: <span id="prev-current" style="color: #FFF; font-weight: 600;"></span></div>
            <div style="font-size: 0.75rem; color: rgba(255,255,255,0.6); margin-top: 2px;">Proposed Change: <span id="prev-change" style="color: #34D399; font-weight: 600;"></span></div>
            <div style="font-size: 0.8125rem; color: #FFF; font-weight: 700; margin-top: 4px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 4px;">Projected Balance: <span id="prev-projected" style="color: #60A5FA;"></span></div>
          </div>

          <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 10px;">
            <button type="button" id="btn-cancel-ob" class="btn" style="background: none; border: 1px solid rgba(255,255,255,0.2); color: #FFF; font-size: 0.75rem; padding: 6px 12px; border-radius: 4px;">Cancel</button>
            <button type="button" id="btn-preview-ob" class="btn" style="background: rgba(255,255,255,0.1); color: #FFF; font-size: 0.75rem; padding: 6px 12px; border-radius: 4px;">Preview Impact</button>
            <button type="submit" id="btn-commit-ob" class="btn btn-primary" style="display: none; font-size: 0.75rem; padding: 6px 12px; border-radius: 4px;">Confirm & Apply</button>
          </div>
        </form>
      </div>
    `;

    subContainer.querySelector('#btn-cancel-ob')?.addEventListener('click', () => { subContainer.innerHTML = ''; });
    subContainer.querySelector('.drawer-backdrop')?.addEventListener('click', () => { subContainer.innerHTML = ''; });

    const btnPreview = subContainer.querySelector('#btn-preview-ob');
    const btnCommit = subContainer.querySelector('#btn-commit-ob');
    const previewBox = subContainer.querySelector('#ob-preview-box');

    btnPreview?.addEventListener('click', async () => {
      const amountPkr = subContainer.querySelector('#ob-amount').value;
      const direction = subContainer.querySelector('#ob-direction').value;
      const asOfDate = subContainer.querySelector('#ob-date').value;
      const ref = subContainer.querySelector('#ob-ref').value.trim();
      const notes = subContainer.querySelector('#ob-notes').value.trim();

      const amountMinor = parseCatalogPkr(amountPkr);
      if (amountMinor === null || amountMinor <= 0) {
        alert('Please enter a valid positive amount in PKR.');
        return;
      }
      if (!ref) {
        alert('Please enter a source statement reference.');
        return;
      }

      btnPreview.disabled = true;
      btnPreview.textContent = 'Calculating...';

      try {
        const previewRes = await previewSupplierOpeningBalance(supplier.id, {
          amount_minor: amountMinor,
          direction,
          as_of_date: asOfDate,
          reference: ref,
          notes: notes || undefined,
        });

        subContainer.querySelector('#prev-current').textContent = formatPkr(previewRes.current_outstanding_minor);
        subContainer.querySelector('#prev-change').textContent = `${direction === 'credit' ? '+' : '-'} ${formatPkr(previewRes.amount_minor)}`;
        subContainer.querySelector('#prev-projected').textContent = formatPkr(previewRes.projected_outstanding_minor);
        previewBox.style.display = 'block';
        btnCommit.style.display = 'inline-block';
      } catch (err) {
        alert(`Failed to preview opening balance: ${err.message || 'Error'}`);
      } finally {
        btnPreview.disabled = false;
        btnPreview.textContent = 'Preview Impact';
      }
    });

    subContainer.querySelector('#ob-form')?.addEventListener('submit', async (ev) => {
      ev.preventDefault();
      const amountPkr = subContainer.querySelector('#ob-amount').value;
      const direction = subContainer.querySelector('#ob-direction').value;
      const asOfDate = subContainer.querySelector('#ob-date').value;
      const ref = subContainer.querySelector('#ob-ref').value.trim();
      const notes = subContainer.querySelector('#ob-notes').value.trim();

      const amountMinor = parseCatalogPkr(amountPkr);
      if (amountMinor === null || amountMinor <= 0) {
        alert('Please enter a valid positive amount in PKR.');
        return;
      }

      btnCommit.disabled = true;
      btnCommit.textContent = 'Applying...';

      try {
        await applySupplierOpeningBalance(supplier.id, {
          amount_minor: amountMinor,
          direction,
          as_of_date: asOfDate,
          reference: ref,
          notes: notes || undefined,
        });
        subContainer.innerHTML = '';
        await loadData();
      } catch (err) {
        alert(`Failed to apply opening balance: ${err.message || 'Error'}`);
        btnCommit.disabled = false;
        btnCommit.textContent = 'Confirm & Apply';
      }
    });
  }

  // Refresh button
  container.querySelector('#btn-refresh-ledger')?.addEventListener('click', () => {
    loadData();
  });

  // Initial load
  loadData();

  return container;
}
