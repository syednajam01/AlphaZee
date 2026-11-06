/**
 * VendorPortal.js — Mobile-first Vendor Stock Portal (VS2-VS3).
 *
 * Dedicated stock-only portal for supplier shop staff to maintain physical stock
 * counts allocated to AlphaZee with zero leakage of prices, wholesale costs,
 * customer data, or other vendors' products.
 */

import {
  fetchVendorSession,
  loginVendor,
  logoutVendor,
  fetchVendorStock,
  updateVendorStockCount,
  reportVendorShortage,
  fetchVendorStockHistory,
  onVendorSessionExpired,
} from '../utils/api.js';

export function initVendorPortal() {
  const root = document.getElementById('app');
  if (!root) return;

  document.title = 'AlphaZee — Vendor Stock Portal';

  let session = null;
  let stockItems = [];
  let totalItems = 0;
  let page = 1;
  const limit = 50;
  let searchQuery = '';
  let isLoading = true;
  let errorMsg = null;
  let activeModal = null; // { type: 'count' | 'shortage' | 'history', item?: ... }

  onVendorSessionExpired(() => {
    session = null;
    render();
  });

  async function checkAuthAndLoad() {
    isLoading = true;
    errorMsg = null;
    render();
    try {
      session = await fetchVendorSession();
      await loadStock();
    } catch {
      session = null;
      isLoading = false;
      render();
    }
  }

  async function loadStock() {
    isLoading = true;
    errorMsg = null;
    render();
    try {
      const res = await fetchVendorStock({ page, limit, search: searchQuery });
      stockItems = res.items || [];
      totalItems = res.total_items || 0;
    } catch (err) {
      errorMsg = err.message || 'Failed to load stock list';
    } finally {
      isLoading = false;
      render();
    }
  }

  function render() {
    root.innerHTML = '';
    const container = document.createElement('div');
    container.className = 'vendor-portal-container';

    if (!session) {
      container.classList.add('vp-login-mode');
      container.appendChild(renderLoginForm());
    } else {
      container.appendChild(renderHeader());
      container.appendChild(renderStatsBar());
      container.appendChild(renderSearchBar());
      container.appendChild(renderStockContent());
    }

    if (activeModal) {
      container.appendChild(renderModal());
    }

    root.appendChild(container);
  }

  function renderLoginForm() {
    const card = document.createElement('div');
    card.className = 'vp-login-card';
    card.innerHTML = `
      <div class="vp-login-brand">
        <div class="vp-logo-badge">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#52B788" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
            <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
            <line x1="12" y1="22.08" x2="12" y2="12"></line>
          </svg>
        </div>
        <h1 class="vp-title">Vendor Stock Portal</h1>
        <p class="vp-subtitle">Physical Inventory Allocation & Synchronization</p>
        <div class="vp-scope-badge">
          <span class="vp-scope-dot"></span>
          Isolated Stock-Only Scope
        </div>
      </div>

      ${errorMsg ? `<div class="vp-alert vp-alert-error" role="alert">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
        <span>${escapeHtml(errorMsg)}</span>
      </div>` : ''}

      <form id="vp-login-form" class="vp-form">
        <div class="vp-form-group">
          <label for="vp-username" class="vp-form-label">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
            Stock Username
          </label>
          <input type="text" id="vp-username" name="username" class="vp-input" placeholder="e.g. karachi_stock_1" required autocomplete="username" />
        </div>
        <div class="vp-form-group">
          <label for="vp-password" class="vp-form-label">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
            Password
          </label>
          <div class="vp-password-wrapper">
            <input type="password" id="vp-password" name="password" class="vp-input" placeholder="••••••••••••" required autocomplete="current-password" />
            <button type="button" id="btn-toggle-vp-pw" class="vp-pw-toggle" aria-label="Toggle password visibility">
              <svg class="eye-open" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
              <svg class="eye-closed" style="display:none;" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>
            </button>
          </div>
        </div>
        <button type="submit" class="vp-btn vp-btn-primary vp-btn-block" id="vp-login-btn">
          <span>Sign In to Shop Stock</span>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>
        </button>
      </form>

      <div class="vp-login-footnote">
        <div class="vp-footnote-badge">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#52B788" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
          <strong>Zero Cross-Shop Leakage:</strong>
        </div>
        <p>Pricing, wholesale costs, customer identities, and other suppliers' records remain strictly isolated from this portal.</p>
      </div>

      <div class="vp-login-footer">
        <a href="/" class="vp-back-store-link">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>
          Return to Storefront
        </a>
      </div>
    `;

    const togglePwBtn = card.querySelector('#btn-toggle-vp-pw');
    togglePwBtn?.addEventListener('click', () => {
      const pwInput = card.querySelector('#vp-password');
      const eyeOpen = togglePwBtn.querySelector('.eye-open');
      const eyeClosed = togglePwBtn.querySelector('.eye-closed');
      if (pwInput.type === 'password') {
        pwInput.type = 'text';
        eyeOpen.style.display = 'none';
        eyeClosed.style.display = 'block';
      } else {
        pwInput.type = 'password';
        eyeOpen.style.display = 'block';
        eyeClosed.style.display = 'none';
      }
    });

    const form = card.querySelector('#vp-login-form');
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const uname = form.username.value.trim();
      const pwd = form.password.value;
      const submitBtn = card.querySelector('#vp-login-btn');
      submitBtn.disabled = true;
      submitBtn.textContent = 'Signing in...';
      try {
        errorMsg = null;
        session = await loginVendor(uname, pwd);
        await loadStock();
      } catch (err) {
        errorMsg = err.message || 'Login failed';
        submitBtn.disabled = false;
        submitBtn.textContent = 'Sign In to Shop Stock';
        render();
      }
    });

    return card;
  }

  function renderHeader() {
    const header = document.createElement('header');
    header.className = 'vp-header';
    header.innerHTML = `
      <div class="vp-header-left">
        <div class="vp-shop-badge">🏪 ${escapeHtml(session.vendor_name)}</div>
        <div class="vp-role-pill">Stock Portal</div>
      </div>
      <div class="vp-header-right">
        <button type="button" class="vp-btn vp-btn-outline vp-btn-sm" id="vp-history-btn">
          📜 History
        </button>
        <button type="button" class="vp-btn vp-btn-subtle vp-btn-sm" id="vp-logout-btn" title="Sign out ${escapeHtml(session.username)}">
          Sign Out (${escapeHtml(session.username)})
        </button>
      </div>
    `;

    header.querySelector('#vp-history-btn').addEventListener('click', openHistoryModal);
    header.querySelector('#vp-logout-btn').addEventListener('click', async () => {
      try {
        await logoutVendor();
      } finally {
        session = null;
        render();
      }
    });

    return header;
  }

  function renderStatsBar() {
    const totalOnHand = stockItems.reduce((acc, i) => acc + (i.allocated_on_hand || 0), 0);
    const totalHeld = stockItems.reduce((acc, i) => acc + (i.held_quantity || 0), 0);
    const totalAvail = stockItems.reduce((acc, i) => acc + (i.available_quantity || 0), 0);

    const bar = document.createElement('section');
    bar.className = 'vp-stats-bar';
    bar.innerHTML = `
      <div class="vp-stat-card">
        <div class="vp-stat-label">Assigned SKUs</div>
        <div class="vp-stat-val">${totalItems}</div>
      </div>
      <div class="vp-stat-card">
        <div class="vp-stat-label">Allocated On-Hand</div>
        <div class="vp-stat-val vp-stat-highlight">${totalOnHand}</div>
      </div>
      <div class="vp-stat-card">
        <div class="vp-stat-label">Held Online</div>
        <div class="vp-stat-val vp-stat-warn">${totalHeld}</div>
      </div>
      <div class="vp-stat-card">
        <div class="vp-stat-label">Live Available</div>
        <div class="vp-stat-val vp-stat-success">${totalAvail}</div>
      </div>
    `;
    return bar;
  }

  function renderSearchBar() {
    const bar = document.createElement('div');
    bar.className = 'vp-search-bar';
    bar.innerHTML = `
      <div class="vp-search-input-wrap">
        <span class="vp-search-icon">🔍</span>
        <input type="search" id="vp-stock-search" class="vp-input" placeholder="Search by title, SKU, size, or color..." value="${escapeHtml(searchQuery)}" />
        ${searchQuery ? '<button type="button" class="vp-search-clear" id="vp-clear-search">✕</button>' : ''}
      </div>
    `;

    const input = bar.querySelector('#vp-stock-search');
    let debounceTimer = null;
    input.addEventListener('input', (e) => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        searchQuery = e.target.value;
        loadStock();
      }, 300);
    });

    const clearBtn = bar.querySelector('#vp-clear-search');
    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        searchQuery = '';
        loadStock();
      });
    }

    return bar;
  }

  function renderStockContent() {
    const content = document.createElement('main');
    content.className = 'vp-stock-main';

    if (isLoading) {
      content.innerHTML = '<div class="vp-loading"><div class="vp-spinner"></div><p>Refreshing inventory counts...</p></div>';
      return content;
    }

    if (errorMsg) {
      content.innerHTML = `<div class="vp-alert vp-alert-error" role="alert">${escapeHtml(errorMsg)}</div>`;
      return content;
    }

    if (stockItems.length === 0) {
      content.innerHTML = `
        <div class="vp-empty-state">
          <div class="vp-empty-icon">📦</div>
          <h3>No assigned items found</h3>
          <p>${searchQuery ? 'No variants match your search filter.' : 'Your shop does not have active variants assigned yet.'}</p>
        </div>
      `;
      return content;
    }

    const grid = document.createElement('div');
    grid.className = 'vp-stock-grid';

    stockItems.forEach(item => {
      grid.appendChild(renderStockCard(item));
    });

    content.appendChild(grid);
    return content;
  }

  function renderStockCard(item) {
    const card = document.createElement('article');
    card.className = 'vp-stock-card';
    card.id = `vp-card-${item.variant_id}`;

    const hasShortageRisk = item.held_quantity > item.allocated_on_hand;
    const isOutOfStock = item.available_quantity === 0;

    card.innerHTML = `
      <div class="vp-card-top">
        <div class="vp-card-info">
          <h3 class="vp-item-title">${escapeHtml(item.product_title)}</h3>
          <div class="vp-item-tags">
            <span class="vp-badge vp-badge-sku">${escapeHtml(item.variant_sku)}</span>
            ${item.size ? `<span class="vp-badge vp-badge-opt">Size: ${escapeHtml(item.size)}</span>` : ''}
            ${item.color ? `<span class="vp-badge vp-badge-opt">Color: ${escapeHtml(item.color)}</span>` : ''}
          </div>
        </div>
        ${hasShortageRisk ? '<span class="vp-tag vp-tag-danger">⚠️ SHORTAGE</span>' : isOutOfStock ? '<span class="vp-tag vp-tag-muted">Out of Stock</span>' : '<span class="vp-tag vp-tag-active">Live</span>'}
      </div>

      <div class="vp-card-counters">
        <div class="vp-counter-box">
          <div class="vp-counter-label">Allocated Count</div>
          <div class="vp-counter-num ${item.allocated_on_hand === 0 ? 'is-zero' : ''}">${item.allocated_on_hand}</div>
        </div>
        <div class="vp-counter-box">
          <div class="vp-counter-label">Committed Holds</div>
          <div class="vp-counter-num is-held">${item.held_quantity}</div>
        </div>
        <div class="vp-counter-box">
          <div class="vp-counter-label">Available Online</div>
          <div class="vp-counter-num is-avail">${item.available_quantity}</div>
        </div>
      </div>

      <div class="vp-card-actions">
        <button type="button" class="vp-btn vp-btn-primary vp-btn-sm vp-update-btn" data-variant-id="${item.variant_id}">
          ✏️ Update Count
        </button>
        <button type="button" class="vp-btn vp-btn-outline vp-btn-sm vp-shortage-btn" data-variant-id="${item.variant_id}">
          ⚠️ Report Shortage
        </button>
      </div>
    `;

    card.querySelector('.vp-update-btn').addEventListener('click', () => {
      openCountModal(item);
    });

    card.querySelector('.vp-shortage-btn').addEventListener('click', () => {
      openShortageModal(item);
    });

    return card;
  }

  function openCountModal(item) {
    activeModal = { type: 'count', item };
    render();
  }

  function openShortageModal(item) {
    activeModal = { type: 'shortage', item };
    render();
  }

  async function openHistoryModal() {
    activeModal = { type: 'history', loading: true, events: [] };
    render();
    try {
      const res = await fetchVendorStockHistory(30);
      activeModal.events = res.history || [];
      activeModal.loading = false;
      render();
    } catch (err) {
      activeModal.error = err.message || 'Failed to fetch history';
      activeModal.loading = false;
      render();
    }
  }

  function renderModal() {
    const backdrop = document.createElement('div');
    backdrop.className = 'vp-modal-backdrop';

    const dialog = document.createElement('div');
    dialog.className = 'vp-modal-dialog';
    dialog.setAttribute('role', 'dialog');

    if (activeModal.type === 'count') {
      const item = activeModal.item;
      let currentVal = item.allocated_on_hand;

      dialog.innerHTML = `
        <div class="vp-modal-header">
          <h2>Update Stock Count</h2>
          <button type="button" class="vp-modal-close" id="vp-close-modal">✕</button>
        </div>
        <div class="vp-modal-body">
          <div class="vp-modal-summary">
            <strong>${escapeHtml(item.product_title)}</strong>
            <div class="vp-item-tags" style="margin-top: 4px;">
              <span class="vp-badge vp-badge-sku">${escapeHtml(item.variant_sku)}</span>
              ${item.size ? `<span class="vp-badge vp-badge-opt">${escapeHtml(item.size)}</span>` : ''}
              ${item.color ? `<span class="vp-badge vp-badge-opt">${escapeHtml(item.color)}</span>` : ''}
            </div>
            <div class="vp-modal-hold-info">
              Current Allocated: <strong>${item.allocated_on_hand}</strong> | Committed Holds: <strong class="vp-warn-text">${item.held_quantity}</strong>
            </div>
          </div>

          <form id="vp-count-form" class="vp-form">
            <div class="vp-form-group">
              <label for="vp-new-count">New Physical Count Allocated to AlphaZee</label>
              <div class="vp-stepper">
                <button type="button" class="vp-step-btn" id="vp-step-minus">−</button>
                <input type="number" id="vp-new-count" class="vp-input vp-step-input" min="0" max="9999" value="${currentVal}" required />
                <button type="button" class="vp-step-btn" id="vp-step-plus">+</button>
              </div>
            </div>

            <div id="vp-shortage-warning" class="vp-alert vp-alert-warning" style="${currentVal < item.held_quantity ? 'display:block;' : 'display:none;'}">
              ⚠️ <strong>Warning:</strong> Entered count (${currentVal}) is below customer holds (${item.held_quantity}). Submitting will record a shortage alert for owner review. Existing customer reservations are safely preserved.
            </div>

            <div class="vp-form-group">
              <label for="vp-reason">Update Reason</label>
              <select id="vp-reason" class="vp-select">
                <option value="shop_sale">Physical Shop Sale (Sold in store)</option>
                <option value="restock">Restock Received (Fresh inventory)</option>
                <option value="inventory_count_correction">Count Correction (Stock audit)</option>
                <option value="other">Damaged / Discarded / Other</option>
              </select>
            </div>

            <div class="vp-form-group">
              <label for="vp-note">Operational Note (Optional)</label>
              <input type="text" id="vp-note" class="vp-input" placeholder="e.g. 1 unit sold to walk-in customer" maxlength="200" />
            </div>

            <div class="vp-modal-actions">
              <button type="button" class="vp-btn vp-btn-outline" id="vp-cancel-count">Cancel</button>
              <button type="submit" class="vp-btn vp-btn-primary" id="vp-submit-count">Confirm & Save Count</button>
            </div>
          </form>
        </div>
      `;

      const input = dialog.querySelector('#vp-new-count');
      const warning = dialog.querySelector('#vp-shortage-warning');
      const minusBtn = dialog.querySelector('#vp-step-minus');
      const plusBtn = dialog.querySelector('#vp-step-plus');

      const updateWarning = () => {
        const val = parseInt(input.value, 10) || 0;
        if (val < item.held_quantity) {
          warning.innerHTML = `⚠️ <strong>Warning:</strong> Entered count (${val}) is below customer holds (${item.held_quantity}). Submitting will record a shortage alert for owner review. Existing customer reservations are safely preserved.`;
          warning.style.display = 'block';
        } else {
          warning.style.display = 'none';
        }
      };

      minusBtn.addEventListener('click', () => {
        let val = parseInt(input.value, 10) || 0;
        if (val > 0) input.value = val - 1;
        updateWarning();
      });

      plusBtn.addEventListener('click', () => {
        let val = parseInt(input.value, 10) || 0;
        input.value = val + 1;
        updateWarning();
      });

      input.addEventListener('input', updateWarning);

      const form = dialog.querySelector('#vp-count-form');
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const submitBtn = dialog.querySelector('#vp-submit-count');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Saving...';

        const newCount = parseInt(input.value, 10);
        const reason = dialog.querySelector('#vp-reason').value;
        const note = dialog.querySelector('#vp-note').value.trim();

        try {
          const res = await updateVendorStockCount(item.variant_id, {
            counted_quantity: newCount,
            expected_version: item.version,
            reason,
            note: note || undefined,
          });

          // Show confirmation message
          activeModal = null;
          await loadStock();
          if (res.shortage_detected) {
            alert(`Shortage alert submitted to AlphaZee: ${res.message}`);
          }
        } catch (err) {
          alert(`Error updating count: ${err.message}`);
          submitBtn.disabled = false;
          submitBtn.textContent = 'Confirm & Save Count';
        }
      });
    } else if (activeModal.type === 'shortage') {
      const item = activeModal.item;
      dialog.innerHTML = `
        <div class="vp-modal-header">
          <h2>Report Stock Shortage</h2>
          <button type="button" class="vp-modal-close" id="vp-close-modal">✕</button>
        </div>
        <div class="vp-modal-body">
          <p class="vp-modal-desc">
            Use this to immediately alert the AlphaZee team if physical stock is damaged, missing, or unavailable to fulfill held reservations.
          </p>
          <div class="vp-modal-summary">
            <strong>${escapeHtml(item.product_title)}</strong>
            <div class="vp-item-tags" style="margin-top: 4px;">
              <span class="vp-badge vp-badge-sku">${escapeHtml(item.variant_sku)}</span>
            </div>
            <div class="vp-modal-hold-info">
              Held for Customers: <strong class="vp-warn-text">${item.held_quantity}</strong>
            </div>
          </div>

          <form id="vp-shortage-form" class="vp-form">
            <div class="vp-form-group">
              <label for="vp-shortage-count">Actual Units Remaining in Shop</label>
              <input type="number" id="vp-shortage-count" class="vp-input" min="0" value="0" required />
            </div>

            <div class="vp-form-group">
              <label for="vp-shortage-note">Reason / Explanation for AlphaZee</label>
              <textarea id="vp-shortage-note" class="vp-textarea" rows="3" placeholder="Explain the shortage (e.g. flood damage, misplaced by staff, defective batch)..." required></textarea>
            </div>

            <div class="vp-modal-actions">
              <button type="button" class="vp-btn vp-btn-outline" id="vp-cancel-count">Cancel</button>
              <button type="submit" class="vp-btn vp-btn-danger" id="vp-submit-shortage">Submit Shortage Alert</button>
            </div>
          </form>
        </div>
      `;

      const form = dialog.querySelector('#vp-shortage-form');
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const submitBtn = dialog.querySelector('#vp-submit-shortage');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Reporting...';

        const reportedCount = parseInt(dialog.querySelector('#vp-shortage-count').value, 10);
        const note = dialog.querySelector('#vp-shortage-note').value.trim();

        try {
          await reportVendorShortage(item.variant_id, {
            reported_count: reportedCount,
            note,
          });
          activeModal = null;
          await loadStock();
          alert('Stock shortage alert successfully submitted for owner resolution.');
        } catch (err) {
          alert(`Error reporting shortage: ${err.message}`);
          submitBtn.disabled = false;
          submitBtn.textContent = 'Submit Shortage Alert';
        }
      });
    } else if (activeModal.type === 'history') {
      dialog.className += ' vp-modal-wide';
      dialog.innerHTML = `
        <div class="vp-modal-header">
          <h2>Stock Update Audit History</h2>
          <button type="button" class="vp-modal-close" id="vp-close-modal">✕</button>
        </div>
        <div class="vp-modal-body">
          ${activeModal.loading ? '<div class="vp-loading"><div class="vp-spinner"></div><p>Loading audit log...</p></div>' : ''}
          ${activeModal.error ? `<div class="vp-alert vp-alert-error">${escapeHtml(activeModal.error)}</div>` : ''}
          ${!activeModal.loading && !activeModal.error && activeModal.events.length === 0 ? '<p class="vp-empty-hint">No audit events recorded yet.</p>' : ''}
          ${!activeModal.loading && activeModal.events.length > 0 ? `
            <div class="vp-history-table-wrap">
              <table class="vp-history-table">
                <thead>
                  <tr>
                    <th>Date / Time</th>
                    <th>Product & SKU</th>
                    <th>Change</th>
                    <th>Count</th>
                    <th>Reason</th>
                    <th>User</th>
                  </tr>
                </thead>
                <tbody>
                  ${activeModal.events.map(ev => `
                    <tr>
                      <td class="vp-td-date">${formatDate(ev.occurred_at)}</td>
                      <td>
                        <div class="vp-td-prod">${escapeHtml(ev.product_title)}</div>
                        <div class="vp-td-sku">${escapeHtml(ev.variant_sku)}</div>
                      </td>
                      <td class="vp-td-delta ${ev.delta > 0 ? 'is-pos' : ev.delta < 0 ? 'is-neg' : 'is-zero'}">
                        ${ev.delta > 0 ? `+${ev.delta}` : ev.delta}
                      </td>
                      <td>${ev.previous_on_hand} → <strong>${ev.new_on_hand}</strong></td>
                      <td>
                        <span class="vp-reason-chip">${escapeHtml(ev.reason)}</span>
                        ${ev.notes ? `<div class="vp-td-note">${escapeHtml(ev.notes)}</div>` : ''}
                      </td>
                      <td><span class="vp-actor-chip">${escapeHtml(ev.actor_username)}</span></td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          ` : ''}
        </div>
      `;
    }

    dialog.querySelector('#vp-close-modal')?.addEventListener('click', () => {
      activeModal = null;
      render();
    });

    dialog.querySelector('#vp-cancel-count')?.addEventListener('click', () => {
      activeModal = null;
      render();
    });

    backdrop.appendChild(dialog);
    return backdrop;
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function formatDate(isoStr) {
    if (!isoStr) return '';
    try {
      const d = new Date(isoStr);
      return d.toLocaleString('en-PK', {
        timeZone: 'Asia/Karachi',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoStr;
    }
  }

  checkAuthAndLoad();
}
