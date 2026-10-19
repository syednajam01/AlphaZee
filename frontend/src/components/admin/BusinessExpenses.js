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
        <div style="padding: 16px; background: rgba(220, 38, 38, 0.15); border: 1px solid rgba(220, 38, 38, 0.3); border-radius: 6px; color: #FCA5A5; font-size: 0.875rem;">
          Failed to load business expenses: ${escapeHtml(err.message || 'Unknown error')}
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

    const rowsHtml = expenses.map(e => {
      const isPaid = !!e.paid_date;
      const catLabel = CATEGORY_LABELS[e.category] || e.category;
      const isTransport = ['rto_transport', 'customer_return_transport'].includes(e.category);
      const isDeduction = e.payment_method === 'courier_deduction';

      return `
        <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.06); font-size: 0.8125rem;">
          <td style="padding: 12px 8px; font-family: monospace; color: rgba(255, 255, 255, 0.85); white-space: nowrap;">
            ${escapeHtml(e.incurred_date)}
          </td>
          <td style="padding: 12px 8px;">
            <span class="badge ${isTransport ? 'badge-accent' : 'badge-neutral'}" style="font-size: 0.7rem; font-weight: 600;">
              ${escapeHtml(catLabel)}
            </span>
          </td>
          <td style="padding: 12px 8px; color: #FFFFFF;">
            <strong>${escapeHtml(e.payee || '—')}</strong>
            ${e.reference ? `<div style="font-size: 0.72rem; color: rgba(255, 255, 255, 0.5); font-family: monospace;">Ref: ${escapeHtml(e.reference)}</div>` : ''}
          </td>
          <td style="padding: 12px 8px;">
            <span style="font-size: 0.75rem; color: ${isDeduction ? '#60A5FA' : 'rgba(255, 255, 255, 0.7)'};">
              ${escapeHtml(PAYMENT_METHOD_LABELS[e.payment_method] || e.payment_method)}
            </span>
          </td>
          <td style="padding: 12px 8px;">
            ${isPaid
              ? `<span style="display: inline-flex; align-items: center; gap: 4px; color: #34D399; font-size: 0.75rem; font-weight: 600;">
                  ✓ Paid (${escapeHtml(e.paid_date)})
                 </span>`
              : `<span style="display: inline-flex; align-items: center; gap: 4px; color: #FBBF24; font-size: 0.75rem; font-weight: 600;">
                  ⏳ Accrued / Unpaid
                 </span>`
            }
          </td>
          <td style="padding: 12px 8px; text-align: right; font-weight: 700; color: #FFFFFF; font-size: 0.875rem;">
            ${escapeHtml(formatPkr(e.amount_minor))}
          </td>
          <td style="padding: 12px 8px; color: rgba(255, 255, 255, 0.6); max-width: 220px; font-size: 0.75rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${escapeHtml(e.notes || '')}">
            ${escapeHtml(e.notes || '—')}
          </td>
        </tr>
      `;
    }).join('');

    container.innerHTML = `
      <div style="display: flex; flex-direction: column; gap: 20px;">
        <!-- Policy Banner -->
        <div style="background: rgba(20, 92, 68, 0.25); border: 1px solid #145C44; border-radius: 8px; padding: 14px 18px; display: flex; align-items: center; gap: 14px;">
          <div style="font-size: 1.5rem; flex-shrink: 0;">🛡️</div>
          <div>
            <div style="font-size: 0.875rem; font-weight: 700; color: #34D399; margin-bottom: 2px;">
              AlphaZee Transport & Expense Principle
            </div>
            <div style="font-size: 0.8125rem; color: rgba(255, 255, 255, 0.85); line-height: 1.4;">
              AlphaZee strictly bears all RTO (Return to Origin) and customer-return transport expenses. Courier deductions linked to recorded expenses prevent double-counting across settlements.
            </div>
          </div>
        </div>

        <!-- KPI Summary Cards -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px;">
          <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 16px;">
            <div style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.6); text-transform: uppercase; font-weight: 600;">Total Incurred Expenses</div>
            <div id="kpi-total-incurred" style="font-size: 1.5rem; font-weight: 800; color: #FFFFFF; margin-top: 6px;">
              ${escapeHtml(formatPkr(totalMinor))}
            </div>
            <div style="font-size: 0.7rem; color: rgba(255, 255, 255, 0.4); margin-top: 4px;">Operating, freight & marketing costs</div>
          </div>

          <div style="background: rgba(20, 92, 68, 0.15); border: 1px solid rgba(20, 92, 68, 0.3); border-radius: 8px; padding: 16px;">
            <div style="font-size: 0.75rem; color: #34D399; text-transform: uppercase; font-weight: 600;">Paid Expenses</div>
            <div id="kpi-total-paid" style="font-size: 1.5rem; font-weight: 800; color: #34D399; margin-top: 6px;">
              ${escapeHtml(formatPkr(paidMinor))}
            </div>
            <div style="font-size: 0.7rem; color: rgba(255, 255, 255, 0.4); margin-top: 4px;">Disbursed via bank, cash, or courier</div>
          </div>

          <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 16px;">
            <div style="font-size: 0.75rem; color: #FBBF24; text-transform: uppercase; font-weight: 600;">Accrued / Unpaid</div>
            <div id="kpi-total-accrued" style="font-size: 1.5rem; font-weight: 800; color: #FBBF24; margin-top: 6px;">
              ${escapeHtml(formatPkr(unpaidMinor))}
            </div>
            <div style="font-size: 0.7rem; color: rgba(255, 255, 255, 0.4); margin-top: 4px;">Incurred liabilities awaiting payment</div>
          </div>

          <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 16px;">
            <div style="font-size: 0.75rem; color: #60A5FA; text-transform: uppercase; font-weight: 600;">AlphaZee Freight & RTO</div>
            <div id="kpi-total-freight" style="font-size: 1.5rem; font-weight: 800; color: #60A5FA; margin-top: 6px;">
              ${escapeHtml(formatPkr(totalFreightMinor))}
            </div>
            <div style="font-size: 0.7rem; color: rgba(255, 255, 255, 0.4); margin-top: 4px;">RTO + Return freight + Outbound</div>
          </div>
        </div>

        <!-- Filter & Action Toolbar -->
        <div style="display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap;">
          <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
            <div>
              <select id="expense-filter-category" style="padding: 6px 10px; background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 6px; font-size: 0.8125rem;">
                <option value="">All Categories</option>
                ${Object.entries(CATEGORY_LABELS).map(([val, label]) => `<option value="${val}" ${filterCategory === val ? 'selected' : ''}>${label}</option>`).join('')}
              </select>
            </div>
            <div>
              <select id="expense-filter-method" style="padding: 6px 10px; background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 6px; font-size: 0.8125rem;">
                <option value="">All Payment Methods</option>
                ${Object.entries(PAYMENT_METHOD_LABELS).map(([val, label]) => `<option value="${val}" ${filterPaymentMethod === val ? 'selected' : ''}>${label}</option>`).join('')}
              </select>
            </div>
            <div>
              <select id="expense-filter-paid" style="padding: 6px 10px; background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 6px; font-size: 0.8125rem;">
                <option value="" ${filterIsPaid === '' ? 'selected' : ''}>All Statuses</option>
                <option value="true" ${filterIsPaid === 'true' ? 'selected' : ''}>Paid</option>
                <option value="false" ${filterIsPaid === 'false' ? 'selected' : ''}>Accrued / Unpaid</option>
              </select>
            </div>
          </div>

          <button type="button" id="btn-open-record-expense" class="btn btn-primary" style="padding: 7px 16px; font-size: 0.8125rem; font-weight: 600; display: inline-flex; align-items: center; gap: 6px;">
            <span>+</span> Record Business Expense
          </button>
        </div>

        <!-- Expenses Table -->
        <div style="background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; overflow: hidden;">
          <div style="overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse; text-align: left;">
              <thead>
                <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.12); font-size: 0.75rem; color: rgba(255, 255, 255, 0.5); text-transform: uppercase; background: rgba(0, 0, 0, 0.2);">
                  <th style="padding: 10px 8px;">Date</th>
                  <th style="padding: 10px 8px;">Category</th>
                  <th style="padding: 10px 8px;">Payee / Reference</th>
                  <th style="padding: 10px 8px;">Payment Method</th>
                  <th style="padding: 10px 8px;">Status</th>
                  <th style="padding: 10px 8px; text-align: right;">Amount (PKR)</th>
                  <th style="padding: 10px 8px;">Notes</th>
                </tr>
              </thead>
              <tbody id="expense-table-body">
                ${rowsHtml.length ? rowsHtml : '<tr><td colspan="7" style="padding: 32px 8px; text-align: center; color: rgba(255,255,255,0.4);">No business expenses recorded matching the selected filters.</td></tr>'}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    `;

    // Wire filter events
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

    // Wire Modal Open
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
    <div class="drawer-backdrop" style="position: fixed; inset: 0; background: rgba(0,0,0,0.75); z-index: 1051;"></div>
    <div class="modal-content" style="z-index: 1052; max-width: 580px; width: 94%; max-height: 90vh; overflow-y: auto; background: #141715; color: #FFFFFF; border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.15); padding: 24px; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.8); position: relative;">
      
      <!-- Header -->
      <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255, 255, 255, 0.1); padding-bottom: 12px; margin-bottom: 18px;">
        <h3 style="font-size: 1.125rem; font-weight: 700; margin: 0; color: #FFFFFF;">
          Record Business Expense
        </h3>
        <button id="btn-close-expense-modal" class="btn-icon" style="background: none; border: none; color: rgba(255, 255, 255, 0.7); font-size: 1.5rem; cursor: pointer; padding: 2px 6px;" aria-label="Close dialog">&times;</button>
      </div>

      <!-- Expense Form -->
      <form id="record-expense-form" style="display: flex; flex-direction: column; gap: 14px;">
        <div>
          <label style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); display: block; margin-bottom: 4px;">Expense Category *</label>
          <select id="exp-category" required style="width: 100%; padding: 8px 10px; background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 6px; font-size: 0.8125rem;">
            ${Object.entries(CATEGORY_LABELS).map(([val, label]) => `<option value="${val}">${label}</option>`).join('')}
          </select>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
          <div>
            <label style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); display: block; margin-bottom: 4px;">Amount (PKR) *</label>
            <input type="number" id="exp-amount" min="0.01" step="0.01" required placeholder="1500.00" style="width: 100%; padding: 8px 10px; background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 6px; font-size: 0.8125rem;" />
          </div>
          <div>
            <label style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); display: block; margin-bottom: 4px;">Incurred Date *</label>
            <input type="date" id="exp-incurred-date" value="${todayStr}" required style="width: 100%; padding: 8px 10px; background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 6px; font-size: 0.8125rem;" />
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
          <div>
            <label style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); display: block; margin-bottom: 4px;">Payment Method *</label>
            <select id="exp-payment-method" required style="width: 100%; padding: 8px 10px; background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 6px; font-size: 0.8125rem;">
              ${Object.entries(PAYMENT_METHOD_LABELS).map(([val, label]) => `<option value="${val}">${label}</option>`).join('')}
            </select>
          </div>
          <div>
            <label style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); display: block; margin-bottom: 4px;">Paid Date (Leave empty if unpaid)</label>
            <input type="date" id="exp-paid-date" value="${todayStr}" style="width: 100%; padding: 8px 10px; background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 6px; font-size: 0.8125rem;" />
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
          <div>
            <label style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); display: block; margin-bottom: 4px;">Payee / Vendor Name</label>
            <input type="text" id="exp-payee" placeholder="e.g. Trax Logistics, Packaging Depot" maxlength="200" style="width: 100%; padding: 8px 10px; background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 6px; font-size: 0.8125rem;" />
          </div>
          <div>
            <label style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); display: block; margin-bottom: 4px;">Invoice / Reference #</label>
            <input type="text" id="exp-reference" placeholder="e.g. INV-2026-004, TRX-9923" maxlength="100" style="width: 100%; padding: 8px 10px; background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 6px; font-size: 0.8125rem;" />
          </div>
        </div>

        <div>
          <label style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); display: block; margin-bottom: 4px;">Description / Notes</label>
          <textarea id="exp-notes" rows="2" placeholder="Details about this expense, batch size, or tracking link..." style="width: 100%; padding: 8px 10px; background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 6px; font-size: 0.8125rem; resize: vertical;"></textarea>
        </div>

        <div id="exp-error" style="display: none; color: #F87171; font-size: 0.75rem; font-weight: 600;"></div>

        <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 8px;">
          <button type="button" id="btn-cancel-expense" class="btn btn-secondary" style="padding: 7px 14px; font-size: 0.8125rem;">
            Cancel
          </button>
          <button type="submit" id="btn-submit-expense" class="btn btn-primary" style="padding: 7px 18px; font-size: 0.8125rem;">
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
