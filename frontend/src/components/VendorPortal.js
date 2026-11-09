/**
 * VendorPortal.js — Mobile-first Vendor Stock workspace (VS2-VS3).
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

import { sanitizeMediaUrl } from '../utils/dom.js';

export function initVendorPortal() {
  const root = document.getElementById('app');
  if (!root) return;

  document.title = 'AlphaZee — Vendor Stock workspace';

  let session = null;
  let stockItems = [];
  let totalItems = 0;
  let page = 1;
  const limit = 50;
  let searchQuery = '';
  let isLoading = true;
  let errorMsg = null;
  let activeModal = null; // { type: 'count' | 'shortage' | 'history', item?: ... }
  let stockRequest = 0;
  let notice = '';
  let saving = false;
  let restoreFocusId = null;
  let debounceTimer = null;
  const previousOverflow = document.body.style.overflow;

  function closeModal() {
    if (saving) return;
    activeModal = null;
    render();
    document.getElementById(restoreFocusId)?.focus();
  }
  function modalError(dialog, message) {
    let error = dialog.querySelector('.vp-form-error');
    if (!error) {
      error = document.createElement('div');
      error.className = 'vp-alert vp-alert-error vp-form-error';
      error.setAttribute('role', 'alert');
      error.setAttribute('tabindex', '-1');
      dialog.querySelector('.vp-modal-body').prepend(error);
    }
    error.textContent = message;
    error.focus();
  }
  function modalKeys(event) {
    if (!activeModal) return;
    if (event.key === 'Escape') { event.preventDefault(); closeModal(); }
    if (event.key !== 'Tab') return;
    const nodes = [...root.querySelectorAll('.vp-modal-dialog button, .vp-modal-dialog input, .vp-modal-dialog select, .vp-modal-dialog textarea')].filter(el => !el.disabled);
    if (!nodes.length) return;
    const first = nodes[0], last = nodes[nodes.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  }
  document.addEventListener('keydown', modalKeys);

  const unsubscribeSession = onVendorSessionExpired(() => {
    session = null;
    stockRequest++;
    activeModal = null;
    stockItems = [];
    notice = '';
    isLoading = false;
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
    const request = ++stockRequest;
    isLoading = true;
    errorMsg = null;
    render();
    try {
      const res = await fetchVendorStock({ page, limit, search: searchQuery });
      if (request !== stockRequest || !session) return;
      stockItems = res.items || [];
      totalItems = res.total_items || 0;
    } catch (err) {
      if (request !== stockRequest || !session) return;
      errorMsg = err.message || 'Failed to load stock list';
    } finally {
      if (request === stockRequest) { isLoading = false; render(); }
    }
  }

  function render() {
    const focusedId = document.activeElement?.id;
    const selection = document.activeElement?.selectionStart;
    root.innerHTML = '';
    const container = document.createElement('div');
    container.className = 'vendor-portal-container';

    if (!session) {
      container.classList.add('vp-login-mode');
      container.appendChild(renderLoginForm());
    } else {
      container.appendChild(renderHeader());
      if (notice) {
        const status = document.createElement('p');
        status.className = 'vp-notice'; status.setAttribute('role', 'status');
        status.textContent = notice; container.appendChild(status);
      }
      container.appendChild(renderStatsBar());
      container.appendChild(renderSearchBar());
      container.appendChild(renderStockContent());
    }

    if (activeModal) {
      container.appendChild(renderModal());
    }

    root.appendChild(container);
    document.body.style.overflow = activeModal ? 'hidden' : previousOverflow;
    if (activeModal) {
      [...container.children].forEach(child => { child.inert = !child.classList.contains('vp-modal-backdrop'); });
      const target = document.getElementById(focusedId);
      if (target && container.querySelector('.vp-modal-dialog')?.contains(target)) target.focus();
      else container.querySelector('.vp-modal-dialog input, .vp-modal-close')?.focus();
    } else if (focusedId === 'vp-stock-search') {
      const input = document.getElementById(focusedId); input?.focus();
      if (typeof selection === 'number') { try { input?.setSelectionRange(selection, selection); } catch {} }
    }
  }

  function renderLoginForm() {
    const card = document.createElement('div');
    card.className = 'vp-login-card';
    card.innerHTML = `
      <div class="vp-login-brand">
        <a class="vp-brand" href="/" aria-label="AlphaZee home"><img src="/logo/Bold%20AlphaZee%20geometric%20wordmark-2.png" alt="AlphaZee" width="160" height="48" /><span>Partner stock</span></a>
        <h1 class="vp-title">Vendor Stock workspace</h1>
        <p class="vp-subtitle">Keep your shop’s stock up to date</p>
        <div class="vp-scope-badge">
          <span class="vp-scope-dot"></span>
          Your assigned stock
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
            Username
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
          <span>Sign in</span>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>
        </button>
      </form>

      <div class="vp-login-footnote">
        <div class="vp-footnote-badge">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#52B788" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
          <strong>Your shop, your stock</strong>
        </div>
        <p>Update the units you have set aside for AlphaZee. Need access? Ask the AlphaZee team for your shop login.</p>
      </div>

      <div class="vp-login-footer">
        <a href="/" class="vp-back-store-link">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="19" y1="12" x2="5" y2="12"></line><polyline points="12 19 5 12 12 5"></polyline></svg>
          Back to the shop
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
      submitBtn.textContent = 'Signing in…';
      try {
        errorMsg = null;
        session = await loginVendor(uname, pwd);
        await loadStock();
      } catch (err) {
        errorMsg = err.message || 'Login failed';
        submitBtn.disabled = false;
        submitBtn.textContent = 'Sign in';
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
        <h1 class="vp-shop-badge">${escapeHtml(session.vendor_name)}</h1>
        <div class="vp-role-pill">Stock workspace</div>
      </div>
      <div class="vp-header-right">
        <button type="button" class="vp-btn vp-btn-outline vp-btn-sm" id="vp-refresh-btn">Refresh stock</button>
        <button type="button" class="vp-btn vp-btn-outline vp-btn-sm" id="vp-history-btn">
          Update history
        </button>
        <button type="button" class="vp-btn vp-btn-subtle vp-btn-sm" id="vp-logout-btn" title="Sign out ${escapeHtml(session.username)}">
          Sign out (${escapeHtml(session.username)})
        </button>
      </div>
    `;

    header.querySelector('#vp-history-btn').addEventListener('click', openHistoryModal);
    header.querySelector('#vp-refresh-btn').addEventListener('click', () => { notice = ''; loadStock(); });
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
        <div class="vp-stat-label">Matching variants</div>
        <div class="vp-stat-val">${totalItems}</div>
      </div>
      <div class="vp-stat-card">
        <div class="vp-stat-label">Your stock · this page</div>
        <div class="vp-stat-val vp-stat-highlight">${totalOnHand}</div>
      </div>
      <div class="vp-stat-card">
        <div class="vp-stat-label">Customer holds · this page</div>
        <div class="vp-stat-val vp-stat-warn">${totalHeld}</div>
      </div>
      <div class="vp-stat-card">
        <div class="vp-stat-label">Available online · this page</div>
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
        <label for="vp-stock-search" class="vp-search-label">Find a variant</label>
        <input type="search" id="vp-stock-search" class="vp-input" placeholder="Search name, SKU, size or color" value="${escapeHtml(searchQuery)}" />
        ${searchQuery ? '<button type="button" class="vp-search-clear" id="vp-clear-search" aria-label="Clear search">Clear</button>' : ''}
      </div>
    `;

    const input = bar.querySelector('#vp-stock-search');
    input.addEventListener('input', (e) => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        searchQuery = e.target.value;
        page = 1;
        loadStock();
      }, 300);
    });

    const clearBtn = bar.querySelector('#vp-clear-search');
    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        searchQuery = '';
        page = 1;
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
      content.innerHTML = `<div class="vp-alert vp-alert-error" role="alert">${escapeHtml(errorMsg)}</div><button type="button" class="vp-btn vp-btn-outline" id="vp-retry">Try again</button>`;
      content.querySelector('#vp-retry').addEventListener('click', loadStock);
      return content;
    }

    if (stockItems.length === 0) {
      content.innerHTML = `
        <div class="vp-empty-state">
          <div class="vp-empty-icon" aria-hidden="true">—</div>
          <h3>No assigned items found</h3>
          <p>${searchQuery ? 'No variants match your search filter.' : 'Your shop does not have active variants assigned yet.'}</p>
        </div>
      `;
      return content;
    }

    const groups = new Map();
    stockItems.forEach(item => {
      const key = `${item.product_title}|||${item.color || 'Standard'}`;
      if (!groups.has(key)) {
        groups.set(key, {
          title: item.product_title,
          color: item.color || 'Standard',
          thumb: sanitizeMediaUrl(item.thumbnail_url, '/images/storefront-empty.svg'),
          items: []
        });
      }
      groups.get(key).items.push(item);
    });

    groups.forEach(group => {
      const groupSection = document.createElement('section');
      groupSection.className = 'vp-stock-group';
      groupSection.style.cssText = 'margin-bottom: 24px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px;';
      
      const groupHeader = document.createElement('div');
      groupHeader.style.cssText = 'display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #f1f5f9; padding-bottom: 10px; margin-bottom: 14px;';
      groupHeader.innerHTML = `
        <div style="display: flex; align-items: center; gap: 12px;">
          <img src="${escapeHtml(group.thumb)}" width="40" height="50" style="border-radius: 4px; object-fit: cover;" alt="">
          <div>
            <h3 style="margin: 0; font-size: 1rem; color: #0f172a; font-weight: 600;">${escapeHtml(group.title)}</h3>
            <span style="font-size: 0.8125rem; color: #64748b;">Color: <strong style="color: #0f172a;">${escapeHtml(group.color)}</strong> · ${group.items.length} size${group.items.length === 1 ? '' : 's'}</span>
          </div>
        </div>
      `;
      groupSection.appendChild(groupHeader);

      const grid = document.createElement('div');
      grid.className = 'vp-stock-grid';
      group.items.forEach(item => {
        grid.appendChild(renderStockCard(item));
      });
      groupSection.appendChild(grid);
      content.appendChild(groupSection);
    });
    const pages = Math.ceil(totalItems / limit);
    if (pages > 1) {
      const nav = document.createElement('nav'); nav.className = 'vp-pagination'; nav.setAttribute('aria-label', 'Stock pages');
      nav.innerHTML = `<button class="vp-btn vp-btn-outline" id="vp-prev-page" ${page <= 1 ? 'disabled' : ''}>Previous</button><span>Page ${page} of ${pages}</span><button class="vp-btn vp-btn-outline" id="vp-next-page" ${page >= pages ? 'disabled' : ''}>Next</button>`;
      nav.querySelector('#vp-prev-page').addEventListener('click', () => { page--; loadStock(); });
      nav.querySelector('#vp-next-page').addEventListener('click', () => { page++; loadStock(); });
      content.appendChild(nav);
    }
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
        <img class="vp-item-photo" src="${escapeHtml(sanitizeMediaUrl(item.thumbnail_url, '/images/storefront-empty.svg'))}" alt="" width="64" height="80" loading="lazy" />
        <div class="vp-card-info">
          <h3 class="vp-item-title">${escapeHtml(item.product_title)}</h3>
          <div class="vp-item-tags">
            <span class="vp-badge vp-badge-sku">${escapeHtml(item.variant_sku)}</span>
            ${item.size ? `<span class="vp-badge vp-badge-opt">Size: ${escapeHtml(item.size)}</span>` : ''}
            ${item.color ? `<span class="vp-badge vp-badge-opt">Color: ${escapeHtml(item.color)}</span>` : ''}
          </div>
        </div>
        ${hasShortageRisk ? '<span class="vp-tag vp-tag-danger">Count needs review</span>' : isOutOfStock ? '<span class="vp-tag vp-tag-muted">Unavailable online</span>' : '<span class="vp-tag vp-tag-active">Available</span>'}
      </div>

      <div class="vp-card-counters">
        <div class="vp-counter-box">
          <div class="vp-counter-label">Your stock</div>
          <div class="vp-counter-num ${item.allocated_on_hand === 0 ? 'is-zero' : ''}">${item.allocated_on_hand}</div>
        </div>
        <div class="vp-counter-box">
          <div class="vp-counter-label">Customer holds</div>
          <div class="vp-counter-num is-held">${item.held_quantity}</div>
        </div>
        <div class="vp-counter-box">
          <div class="vp-counter-label">Available online</div>
          <div class="vp-counter-num is-avail">${item.available_quantity}</div>
        </div>
      </div>

      <p class="vp-updated">${item.last_updated_at ? `Last updated ${formatDate(item.last_updated_at)}` : 'Not counted yet'}</p>
      <div class="vp-card-actions">
        <button type="button" class="vp-btn vp-btn-primary vp-btn-sm vp-update-btn" data-variant-id="${item.variant_id}">
          Update count
        </button>
        <button type="button" class="vp-btn vp-btn-outline vp-btn-sm vp-shortage-btn" data-variant-id="${item.variant_id}">
          Report a shortage
        </button>
      </div>
    `;

    card.querySelector('.vp-update-btn').addEventListener('click', () => {
      openCountModal(item);
    });
    card.querySelector('.vp-update-btn').id = `vp-count-open-${item.variant_id}`;
    card.querySelector('.vp-shortage-btn').id = `vp-shortage-open-${item.variant_id}`;

    card.querySelector('.vp-shortage-btn').addEventListener('click', () => {
      openShortageModal(item);
    });

    return card;
  }

  function openCountModal(item) {
    restoreFocusId = `vp-count-open-${item.variant_id}`;
    activeModal = { type: 'count', item };
    render();
  }

  function openShortageModal(item) {
    restoreFocusId = `vp-shortage-open-${item.variant_id}`;
    activeModal = { type: 'shortage', item };
    render();
  }

  async function openHistoryModal() {
    restoreFocusId = 'vp-history-btn';
    activeModal = { type: 'history', loading: true, events: [] };
    const modal = activeModal;
    render();
    try {
      const res = await fetchVendorStockHistory(30);
      if (activeModal !== modal || !session) return;
      activeModal.events = res.history || [];
      activeModal.loading = false;
      render();
    } catch (err) {
      if (activeModal !== modal || !session) return;
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
    dialog.setAttribute('aria-modal', 'true');
    dialog.setAttribute('aria-labelledby', 'vp-modal-title');

    if (activeModal.type === 'count') {
      const item = activeModal.item;
      let currentVal = item.allocated_on_hand;

      dialog.innerHTML = `
        <div class="vp-modal-header">
          <h2 id="vp-modal-title">Update stock count</h2>
          <button type="button" class="vp-modal-close" id="vp-close-modal" aria-label="Close dialog">×</button>
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
              Your stock: <strong>${item.allocated_on_hand}</strong> | Customer holds: <strong class="vp-warn-text">${item.held_quantity}</strong>
            </div>
          </div>

          <form id="vp-count-form" class="vp-form">
            <div class="vp-form-group">
              <label for="vp-new-count">Units you have for AlphaZee</label>
              <div class="vp-stepper">
                <button type="button" class="vp-step-btn" id="vp-step-minus" aria-label="Decrease count">−</button>
                <input type="number" id="vp-new-count" class="vp-input vp-step-input" min="0" max="9999" step="1" inputmode="numeric" value="${currentVal}" required />
                <button type="button" class="vp-step-btn" id="vp-step-plus" aria-label="Increase count">+</button>
              </div>
            </div>

            <p class="vp-field-help">Enter the new total, not the amount sold. If you had 3 and sold 1, enter 2. Include units already held for customers.</p>
            <div id="vp-shortage-warning" class="vp-alert vp-alert-warning" style="${currentVal < item.held_quantity ? 'display:block;' : 'display:none;'}">
              <strong>Count below holds:</strong> Entered count (${currentVal}) is below customer holds (${item.held_quantity}). Submitting will record a shortage alert for owner review. Existing customer reservations are safely preserved.
            </div>

            <div class="vp-form-group">
              <label for="vp-reason">Reason for update</label>
              <select id="vp-reason" class="vp-select">
                <option value="shop_sale">Sold in your shop</option>
                <option value="restock">Restocked</option>
                <option value="inventory_count_correction">Count correction</option>
                <option value="other">Damaged or other</option>
              </select>
            </div>

            <div class="vp-form-group">
              <label for="vp-note">Note (optional)</label>
              <input type="text" id="vp-note" class="vp-input" placeholder="e.g. 1 unit sold to walk-in customer" maxlength="200" />
            </div>

            <div class="vp-modal-actions">
              <button type="button" class="vp-btn vp-btn-outline" id="vp-cancel-count">Cancel</button>
              <button type="submit" class="vp-btn vp-btn-primary" id="vp-submit-count">Save count</button>
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
          warning.innerHTML = `<strong>Count below holds:</strong> Entered count (${val}) is below customer holds (${item.held_quantity}). Submitting will record a shortage alert for owner review. Existing customer reservations are safely preserved.`;
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
        if (saving) return;
        if (!Number.isInteger(Number(input.value)) || Number(input.value) < 0 || input.value === '') {
          modalError(dialog, 'Enter a whole number of units, zero or more.'); return;
        }
        saving = true;
        const submitBtn = dialog.querySelector('#vp-submit-count');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Saving…';

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
          saving = false;
          activeModal = null;
          notice = res.shortage_detected ? res.message : `Stock count saved: ${newCount} units. Customer holds are preserved.`;
          await loadStock();
          document.getElementById(restoreFocusId)?.focus();
        } catch (err) {
          saving = false;
          if (!activeModal || !session) return;
          modalError(dialog, err.status === 409 ? 'This count changed. Close this dialog and refresh stock before trying again.' : `Could not save: ${err.message}`);
          submitBtn.disabled = err.status === 409;
          submitBtn.textContent = 'Save count';
        }
      });
    } else if (activeModal.type === 'shortage') {
      const item = activeModal.item;
      dialog.innerHTML = `
        <div class="vp-modal-header">
          <h2 id="vp-modal-title">Report a shortage</h2>
          <button type="button" class="vp-modal-close" id="vp-close-modal" aria-label="Close dialog">×</button>
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
              <label for="vp-shortage-count">Units you have for AlphaZee</label>
              <input type="number" id="vp-shortage-count" class="vp-input" min="0" step="1" inputmode="numeric" value="0" required />
            </div>

            <div class="vp-form-group">
              <label for="vp-shortage-note">What happened?</label>
              <textarea id="vp-shortage-note" class="vp-textarea" rows="3" maxlength="500" placeholder="For example, one unit was damaged" required></textarea>
            </div>

            <div class="vp-modal-actions">
              <button type="button" class="vp-btn vp-btn-outline" id="vp-cancel-count">Cancel</button>
              <button type="submit" class="vp-btn vp-btn-danger" id="vp-submit-shortage">Send shortage report</button>
            </div>
          </form>
        </div>
      `;

      const form = dialog.querySelector('#vp-shortage-form');
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (saving) return;
        const countValue = dialog.querySelector('#vp-shortage-count').value;
        if (countValue === '' || !Number.isInteger(Number(countValue)) || Number(countValue) < 0) {
          modalError(dialog, 'Enter a whole number of units, zero or more.'); return;
        }
        if (!dialog.querySelector('#vp-shortage-note').value.trim()) {
          modalError(dialog, 'Describe what happened before sending the report.'); return;
        }
        saving = true;
        const submitBtn = dialog.querySelector('#vp-submit-shortage');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Sending…';

        const reportedCount = parseInt(dialog.querySelector('#vp-shortage-count').value, 10);
        const note = dialog.querySelector('#vp-shortage-note').value.trim();

        try {
          await reportVendorShortage(item.variant_id, {
            reported_count: reportedCount,
            note,
          });
          saving = false;
          activeModal = null;
          notice = 'Shortage reported. AlphaZee will review it; customer holds remain protected.';
          await loadStock();
          document.getElementById(restoreFocusId)?.focus();
        } catch (err) {
          saving = false;
          if (!activeModal || !session) return;
          modalError(dialog, `Could not send report: ${err.message}`);
          submitBtn.disabled = false;
          submitBtn.textContent = 'Send shortage report';
        }
      });
    } else if (activeModal.type === 'history') {
      dialog.className += ' vp-modal-wide';
      dialog.innerHTML = `
        <div class="vp-modal-header">
          <h2 id="vp-modal-title">Stock update history</h2>
          <button type="button" class="vp-modal-close" id="vp-close-modal" aria-label="Close dialog">×</button>
        </div>
        <div class="vp-modal-body">
          ${activeModal.loading ? '<div class="vp-loading"><div class="vp-spinner"></div><p>Loading updates…</p></div>' : ''}
          ${activeModal.error ? `<div class="vp-alert vp-alert-error">${escapeHtml(activeModal.error)}</div>` : ''}
          ${!activeModal.loading && !activeModal.error && activeModal.events.length === 0 ? '<p class="vp-empty-hint">No updates yet</p>' : ''}
          ${!activeModal.loading && activeModal.events.length > 0 ? `
            <div class="vp-history-table-wrap">
              <table class="vp-history-table">
                <thead>
                  <tr>
                    <th>Date and time</th>
                    <th>Product and SKU</th>
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
      closeModal();
    });

    dialog.querySelector('#vp-cancel-count')?.addEventListener('click', () => {
      closeModal();
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
  return { destroy() { stockRequest++; clearTimeout(debounceTimer); unsubscribeSession(); document.removeEventListener('keydown', modalKeys); document.body.style.overflow = previousOverflow; } };
}
