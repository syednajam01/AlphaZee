import { escapeHtml } from '../../utils/dom.js';
import { formatPkr, parseCatalogPkr } from '../../utils/money.js';
import {
  createBusinessExpense,
  fetchBusinessExpenses,
  fetchBusinessExpenseSummary,
} from '../../utils/api.js';

const CATEGORY_LABELS = {
  packaging: 'Packaging & Boxes',
  advertising: 'Advertising & Marketing',
  outbound_delivery: 'Outbound Courier Freight',
  rto_transport: 'RTO Return Transport (AlphaZee-Borne)',
  customer_return_transport: 'Customer Return Freight (AlphaZee-Borne)',
  platform_hosting: 'Platform & Hosting',
  office_supplies: 'Office & Equipment',
  salaries: 'Salaries & Wages',
  other_overhead: 'Other Overhead',
};

const PAYMENT_METHOD_LABELS = {
  bank_transfer: 'Bank Transfer',
  cash: 'Cash',
  credit_card: 'Credit Card',
  courier_deduction: 'Courier Deduction',
  unpaid_accrual: 'Unpaid Accrual',
};

export async function renderBusinessExpenses(container, viewGenerationRef) {
  let expenses = [];
  let summary = {
    total_incurred_minor: 0,
    total_paid_minor: 0,
    total_accrued_minor: 0,
    categories: {},
  };

  let filterCategory = '';
  let filterPaymentMethod = '';
  let filterIsPaid = '';

  async function loadData() {
    try {
      const params = {};
      if (filterCategory) params.category = filterCategory;
      if (filterPaymentMethod) params.payment_method = filterPaymentMethod;
      if (filterIsPaid === 'true') params.is_paid = true;
      if (filterIsPaid === 'false') params.is_paid = false;

      const [listRes, summaryRes] = await Promise.all([
        fetchBusinessExpenses(params),
        fetchBusinessExpenseSummary(),
      ]);

      expenses = listRes.expenses || [];
      summary = summaryRes || summary;
      render();
    } catch (err) {
      container.innerHTML = `
        <div style="padding: 16px; background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 8px; color: #F87171; font-size: 0.8125rem;">
          <strong>Failed to load business expenses:</strong> ${escapeHtml(err.message || 'Unknown error')}
        </div>
      `;
    }
  }

  function render() {
    const totalMinor = summary.total_expenses_minor ?? summary.total_incurred_minor ?? 0;
    const paidMinor = summary.paid_expenses_minor ?? summary.total_paid_minor ?? 0;
    const unpaidMinor = summary.unpaid_expenses_minor ?? summary.total_accrued_minor ?? 0;

    // Calculate freight total (RTO + Customer Return + Outbound Freight)
    const catTotals = summary.category_totals || {};
    const rtoMinor = catTotals.rto_transport || summary.categories?.rto_transport?.incurred_minor || 0;
    const returnMinor = catTotals.customer_return_transport || summary.categories?.customer_return_transport?.incurred_minor || 0;
    const outboundMinor = catTotals.outbound_delivery || summary.categories?.outbound_delivery?.incurred_minor || 0;
    const totalFreightMinor = rtoMinor + returnMinor + outboundMinor;

    // Desktop Table Rows
    const rowsHtml = expenses.map(e => {
      const isPaid = !!e.paid_date;
      const catLabel = CATEGORY_LABELS[e.category] || e.category;
      const isTransport = ['rto_transport', 'customer_return_transport'].includes(e.category);
      const isDeduction = e.payment_method === 'courier_deduction';

      return `
        <tr>
          <td style="font-family: monospace; white-space: nowrap; color: rgba(255, 255, 255, 0.75);">
            ${escapeHtml(e.incurred_date)}
          </td>
          <td>
            <span class="exp-badge-pill ${isTransport ? 'exp-badge-freight' : 'exp-badge-neutral'}">
              ${isTransport ? '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink: 0;"><rect x="1" y="3" width="15" height="13"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/></svg>' : ''}
              ${escapeHtml(catLabel)}
            </span>
          </td>
          <td>
            <div style="font-weight: 600; color: #FFFFFF;">${escapeHtml(e.payee || '—')}</div>
            ${e.reference ? `<div style="font-size: 0.6875rem; color: rgba(255, 255, 255, 0.4); font-family: monospace;">Ref: ${escapeHtml(e.reference)}</div>` : ''}
          </td>
          <td>
            <span style="color: ${isDeduction ? '#38BDF8' : 'rgba(255, 255, 255, 0.7)'};">
              ${escapeHtml(PAYMENT_METHOD_LABELS[e.payment_method] || e.payment_method)}
            </span>
          </td>
          <td>
            ${isPaid
              ? `<span class="exp-status-paid">Paid (${escapeHtml(e.paid_date)})</span>`
              : `<span class="exp-status-accrued">Accrued / Unpaid</span>`
            }
          </td>
          <td style="text-align: right; font-family: monospace; font-weight: 600; font-variant-numeric: tabular-nums; color: #FFFFFF; font-size: 0.8125rem;">
            ${escapeHtml(formatPkr(e.amount_minor))}
          </td>
          <td style="color: rgba(255, 255, 255, 0.5); max-width: 220px; font-size: 0.6875rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${escapeHtml(e.notes || '')}">
            ${escapeHtml(e.notes || '—')}
          </td>
        </tr>
      `;
    }).join('');

    // Mobile Responsive Cards (Rule 1: Zero Horizontal Scroll)
    const cardsHtml = expenses.map(e => {
      const isPaid = !!e.paid_date;
      const catLabel = CATEGORY_LABELS[e.category] || e.category;
      const isTransport = ['rto_transport', 'customer_return_transport'].includes(e.category);
      const isDeduction = e.payment_method === 'courier_deduction';

      return `
        <div class="exp-card">
          <div class="exp-card-top">
            <span style="font-family: monospace; font-size: 0.6875rem; color: rgba(255, 255, 255, 0.5);">${escapeHtml(e.incurred_date)}</span>
            <span class="exp-badge-pill ${isTransport ? 'exp-badge-freight' : 'exp-badge-neutral'}">
              ${escapeHtml(catLabel)}
            </span>
            <span class="${isPaid ? 'exp-status-paid' : 'exp-status-accrued'}" style="font-size: 0.6875rem;">
              ${isPaid ? 'PAID' : 'ACCRUED'}
            </span>
          </div>
          <div class="exp-card-mid">
            <div>
              <div style="font-weight: 600; color: #FFFFFF; font-size: 0.8125rem;">${escapeHtml(e.payee || '—')}</div>
              ${e.reference ? `<div style="font-size: 0.6875rem; color: rgba(255, 255, 255, 0.4); font-family: monospace;">Ref: ${escapeHtml(e.reference)}</div>` : ''}
            </div>
            <div style="text-align: right;">
              <div style="font-family: monospace; font-weight: 700; color: #FFFFFF; font-size: 0.9375rem;">${escapeHtml(formatPkr(e.amount_minor))}</div>
              <div style="font-size: 0.6875rem; color: ${isDeduction ? '#38BDF8' : 'rgba(255, 255, 255, 0.5)'};">${escapeHtml(PAYMENT_METHOD_LABELS[e.payment_method] || e.payment_method)}</div>
            </div>
          </div>
          ${e.notes ? `<div class="exp-card-bot"><span>Note:</span> <span style="color: rgba(255, 255, 255, 0.65);">${escapeHtml(e.notes)}</span></div>` : ''}
        </div>
      `;
    }).join('');

    container.innerHTML = `
      <div class="business-expenses-view">
        
        <!-- Header & Quick Action Toolbar -->
        <div class="exp-toolbar">
          <div class="exp-title-group">
            <div class="exp-title-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
            </div>
            <div>
              <h2 class="exp-title">Operating Costs & Freight Ledger</h2>
              <p class="exp-subtitle">Authoritative operating overhead, RTO freight absorption, & settlements.</p>
            </div>
          </div>
          <!-- Rule 2: Compact Semantic Icon Button with Micro-Tooltip -->
          <button type="button" id="btn-open-record-expense" class="exp-icon-btn exp-icon-btn-accent" data-tooltip="Record business expense or freight" aria-label="Record business expense" title="Record Business Expense">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          </button>
        </div>

        <!-- 4-Card Executive Treasury Grid -->
        <div class="exp-kpis-grid">
          <div class="exp-kpi-card">
            <div class="exp-kpi-label">Total Incurred Expenses</div>
            <div id="kpi-total-incurred" class="exp-kpi-val">${escapeHtml(formatPkr(totalMinor))}</div>
            <div class="exp-kpi-sub">Operating, freight & marketing costs</div>
          </div>

          <div class="exp-kpi-card">
            <div class="exp-kpi-label">Paid Expenses</div>
            <div id="kpi-total-paid" class="exp-kpi-val" style="color: #34D399;">${escapeHtml(formatPkr(paidMinor))}</div>
            <div class="exp-kpi-sub">Disbursed via bank, cash, or courier</div>
          </div>

          <div class="exp-kpi-card">
            <div class="exp-kpi-label">Accrued / Unpaid</div>
            <div id="kpi-total-accrued" class="exp-kpi-val" style="color: #FBBF24;">${escapeHtml(formatPkr(unpaidMinor))}</div>
            <div class="exp-kpi-sub">Incurred liabilities awaiting payment</div>
          </div>

          <div class="exp-kpi-card">
            <div class="exp-kpi-label">AlphaZee Freight & RTO</div>
            <div id="kpi-total-freight" class="exp-kpi-val" style="color: #38BDF8;">${escapeHtml(formatPkr(totalFreightMinor))}</div>
            <div class="exp-kpi-sub">100% borne RTO + return freight</div>
          </div>
        </div>

        <!-- Statutory Absorption Notice -->
        <div class="exp-policy-banner">
          <div class="exp-policy-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/></svg>
          </div>
          <div class="exp-policy-text">
            <strong>AlphaZee Transport & Expense Principle:</strong> AlphaZee strictly bears all RTO (Return to Origin) and customer-return transport expenses. Courier deductions linked to recorded expenses prevent double-counting across settlements.
          </div>
        </div>

        <!-- Filter Bar -->
        <div class="exp-filters-bar">
          <div class="exp-filters-group">
            <select id="expense-filter-category" class="exp-select" aria-label="Filter by expense category">
              <option value="">All Categories</option>
              ${Object.entries(CATEGORY_LABELS).map(([val, label]) => `<option value="${val}" ${filterCategory === val ? 'selected' : ''}>${label}</option>`).join('')}
            </select>
            <select id="expense-filter-method" class="exp-select" aria-label="Filter by payment method">
              <option value="">All Payment Methods</option>
              ${Object.entries(PAYMENT_METHOD_LABELS).map(([val, label]) => `<option value="${val}" ${filterPaymentMethod === val ? 'selected' : ''}>${label}</option>`).join('')}
            </select>
            <select id="expense-filter-paid" class="exp-select" aria-label="Filter by payment status">
              <option value="" ${filterIsPaid === '' ? 'selected' : ''}>All Statuses</option>
              <option value="true" ${filterIsPaid === 'true' ? 'selected' : ''}>Paid</option>
              <option value="false" ${filterIsPaid === 'false' ? 'selected' : ''}>Accrued / Unpaid</option>
            </select>
          </div>
          <div class="exp-count-badge">
            Showing ${expenses.length} record${expenses.length === 1 ? '' : 's'}
          </div>
        </div>

        <!-- High-Density Ledger Card -->
        <div class="exp-ledger-card">
          <!-- Desktop Table (Rule 1: Hidden on Mobile) -->
          <div class="exp-table-wrap">
            <table class="exp-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Category</th>
                  <th>Payee / Reference</th>
                  <th>Payment Method</th>
                  <th>Status</th>
                  <th style="text-align: right;">Amount (PKR)</th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody id="expense-table-body">
                ${rowsHtml.length ? rowsHtml : '<tr><td colspan="7" style="padding: 32px 12px; text-align: center; color: rgba(255,255,255,0.4);">No business expenses recorded matching the selected filters.</td></tr>'}
              </tbody>
            </table>
          </div>

          <!-- Mobile Cards List (Rule 1: Hidden on Desktop) -->
          <div class="exp-cards-list">
            ${cardsHtml.length ? cardsHtml : '<div style="padding: 24px 12px; text-align: center; color: rgba(255,255,255,0.4);">No business expenses recorded matching the selected filters.</div>'}
          </div>
        </div>

      </div>
    `;

    // Wire Filter Events
    container.querySelector('#expense-filter-category')?.addEventListener('change', e => {
      filterCategory = e.target.value;
      loadData();
    });

    container.querySelector('#expense-filter-method')?.addEventListener('change', e => {
      filterPaymentMethod = e.target.value;
      loadData();
    });

    container.querySelector('#expense-filter-paid')?.addEventListener('change', e => {
      filterIsPaid = e.target.value;
      loadData();
    });

    // Wire Modal Trigger
    container.querySelector('#btn-open-record-expense')?.addEventListener('click', () => {
      openRecordExpenseModal({
        onSuccess: () => loadData(),
      });
    });
  }

  await loadData();
}

export function openRecordExpenseModal({ onSuccess = () => {} } = {}) {
  const modal = document.createElement('div');
  modal.className = 'expense-modal modal-container is-open';
  modal.id = 'record-expense-modal';
  modal.setAttribute('role', 'dialog');
  modal.setAttribute('aria-modal', 'true');
  modal.setAttribute('aria-label', 'Record Business Expense');
  modal.style.cssText = 'position: fixed; inset: 0; z-index: 1050; display: flex; align-items: center; justify-content: center;';

  const todayStr = new Date().toISOString().split('T')[0];

  modal.innerHTML = `
    <div class="drawer-backdrop" style="position: fixed; inset: 0; background: rgba(0,0,0,0.75); backdrop-filter: blur(4px); z-index: 1051;"></div>
    <div class="record-expense-modal-box" style="z-index: 1052;">
      
      <!-- Header -->
      <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding-bottom: 12px; margin-bottom: 16px;">
        <div style="display: flex; align-items: center; gap: 8px;">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
          <h3 style="font-size: 1rem; font-weight: 700; margin: 0; color: #FFFFFF;">
            Record Business Expense
          </h3>
        </div>
        <!-- Rule 2: Compact Semantic Close Button -->
        <button id="btn-close-expense-modal" class="exp-icon-btn" data-tooltip="Close dialog" aria-label="Close dialog" title="Close dialog">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>

      <!-- Expense Form -->
      <form id="record-expense-form" style="display: flex; flex-direction: column; gap: 12px;">
        <div class="exp-form-group">
          <label class="exp-form-label">Expense Category *</label>
          <select id="exp-category" class="exp-input" required>
            ${Object.entries(CATEGORY_LABELS).map(([val, label]) => `<option value="${val}">${label}</option>`).join('')}
          </select>
        </div>

        <div class="exp-form-grid">
          <div class="exp-form-group">
            <label class="exp-form-label">Amount (PKR) *</label>
            <input type="number" id="exp-amount" class="exp-input" min="0.01" step="0.01" required placeholder="1500.00" />
          </div>
          <div class="exp-form-group">
            <label class="exp-form-label">Incurred Date *</label>
            <input type="date" id="exp-incurred-date" class="exp-input" value="${todayStr}" required />
          </div>
        </div>

        <div class="exp-form-grid">
          <div class="exp-form-group">
            <label class="exp-form-label">Payment Method *</label>
            <select id="exp-payment-method" class="exp-input" required>
              ${Object.entries(PAYMENT_METHOD_LABELS).map(([val, label]) => `<option value="${val}">${label}</option>`).join('')}
            </select>
          </div>
          <div class="exp-form-group">
            <label class="exp-form-label">Paid Date (Leave empty if unpaid)</label>
            <input type="date" id="exp-paid-date" class="exp-input" value="${todayStr}" />
          </div>
        </div>

        <div class="exp-form-grid">
          <div class="exp-form-group">
            <label class="exp-form-label">Payee / Vendor Name</label>
            <input type="text" id="exp-payee" class="exp-input" placeholder="e.g. Trax Logistics, Packaging Depot" maxlength="200" />
          </div>
          <div class="exp-form-group">
            <label class="exp-form-label">Invoice / Reference #</label>
            <input type="text" id="exp-reference" class="exp-input" placeholder="e.g. INV-2026-004, TRX-9923" maxlength="100" />
          </div>
        </div>

        <div class="exp-form-group">
          <label class="exp-form-label">Description / Notes</label>
          <textarea id="exp-notes" class="exp-input" rows="2" placeholder="Details about this expense, batch size, or tracking link..." style="resize: vertical;"></textarea>
        </div>

        <div id="exp-error" style="display: none; color: #F87171; font-size: 0.75rem; font-weight: 600;"></div>

        <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 6px;">
          <button type="button" id="btn-cancel-expense" class="btn btn-secondary" style="padding: 6px 14px; font-size: 0.75rem;">
            Cancel
          </button>
          <button type="submit" id="btn-submit-expense" class="btn btn-primary" style="padding: 6px 18px; font-size: 0.75rem;">
            Save Expense
          </button>
        </div>
      </form>
    </div>
  `;

  document.body.appendChild(modal);

  const close = () => {
    modal.remove();
  };

  modal.querySelector('#btn-close-expense-modal')?.addEventListener('click', close);
  modal.querySelector('#btn-cancel-expense')?.addEventListener('click', close);
  modal.querySelector('.drawer-backdrop')?.addEventListener('click', close);

  // Method change toggles paid date automatically
  const methodSelect = modal.querySelector('#exp-payment-method');
  const paidDateInput = modal.querySelector('#exp-paid-date');
  methodSelect?.addEventListener('change', () => {
    if (methodSelect.value === 'unpaid_accrual') {
      paidDateInput.value = '';
    } else if (!paidDateInput.value) {
      paidDateInput.value = todayStr;
    }
  });

  const form = modal.querySelector('#record-expense-form');
  const errorDiv = modal.querySelector('#exp-error');
  const submitBtn = modal.querySelector('#btn-submit-expense');

  form?.addEventListener('submit', async e => {
    e.preventDefault();
    errorDiv.style.display = 'none';

    const category = modal.querySelector('#exp-category').value;
    const amountVal = modal.querySelector('#exp-amount').value;
    const amountMinor = parseCatalogPkr(amountVal);

    if (amountMinor === null || amountMinor <= 0) {
      errorDiv.textContent = 'Enter a valid positive PKR amount.';
      errorDiv.style.display = 'block';
      return;
    }

    const incurredDate = modal.querySelector('#exp-incurred-date').value;
    const paymentMethod = modal.querySelector('#exp-payment-method').value;
    const paidDate = modal.querySelector('#exp-paid-date').value || null;
    const payee = modal.querySelector('#exp-payee').value.trim() || null;
    const reference = modal.querySelector('#exp-reference').value.trim() || null;
    const notes = modal.querySelector('#exp-notes').value.trim() || null;

    submitBtn.disabled = true;
    submitBtn.textContent = 'Saving...';

    try {
      await createBusinessExpense({
        category,
        amount_minor: amountMinor,
        incurred_date: incurredDate,
        payment_method: paymentMethod,
        paid_date: paidDate,
        payee,
        reference,
        notes,
      });

      close();
      onSuccess();
    } catch (err) {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Save Expense';
      errorDiv.textContent = err.message || 'Failed to save expense.';
      errorDiv.style.display = 'block';
    }
  });
}
