/**
 * VendorPortal.js — Mobile-first Vendor Stock workspace (VS2-VS3).
 *
 * Dedicated stock-only portal for supplier shop staff to maintain physical stock
 * counts allocated to AlphaZee, including their agreed supply rate, without retail prices,
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
  updateVendorProfile,
  fetchVendorProfile,
} from '../utils/api.js';

import { sanitizeMediaUrl } from '../utils/dom.js';
import { VendorCountDrafts, parseVendorCount, MAX_VENDOR_COUNT } from '../utils/vendorMatrix.js';
import { createVendorStockMatrix } from './VendorStockMatrix.js';

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
  let destroyed = false;
  let refreshing = false;
  let batchGeneration = 0;
  const drafts = new VendorCountDrafts();
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
    batchGeneration++;
    saving = false;
    refreshing = false;
    drafts.clear();
    stockRequest++;
    activeModal = null;
    stockItems = [];
    searchQuery = ''; page = 1; totalItems = 0;
    notice = '';
    isLoading = false;
    render();
  });

  async function checkAuthAndLoad() {
    isLoading = true;
    errorMsg = null;
    render();
    try {
      const restored = await fetchVendorSession();
      if (destroyed) return;
      session = restored;
      if (session.onboarding_status === 'pending_profile') {
        isLoading = false;
        render();
        return;
      }
      await loadStock();
    } catch {
      session = null;
      isLoading = false;
      render();
    }
  }

  async function loadStock({ quiet = false } = {}) {
    quiet = quiet || Boolean(activeModal);
    if (!session || destroyed || saving || quiet && refreshing) return;
    refreshing = true;
    const actor = session;
    const request = ++stockRequest;
    if (!quiet) isLoading = true;
    errorMsg = null;
    if (!quiet) render();
    try {
      const res = await fetchVendorStock({ page, limit, search: searchQuery });
      if (request !== stockRequest || session !== actor || destroyed) return;
      stockItems = res.items || [];
      totalItems = res.total_items || 0;
      drafts.reconcile(stockItems);
    } catch (err) {
      if (request !== stockRequest || session !== actor || destroyed) return;
      if (quiet) notice = 'Could not refresh stock. Your pending edits are kept; use Refresh stock to retry.';
      else errorMsg = err.message || 'Failed to load stock list';
    } finally {
      if (request === stockRequest && session === actor && !destroyed) { refreshing = false; isLoading = false; if (!activeModal) render(); }
    }
  }

  function render() {
    if (destroyed) return;
    const focusedId = document.activeElement?.id;
    const selection = document.activeElement?.selectionStart;
    const selectionEnd = document.activeElement?.selectionEnd;
    root.innerHTML = '';
    const container = document.createElement('div');
    container.className = 'vendor-portal-container';

    if (!session) {
      container.classList.add('vp-login-mode');
      container.appendChild(renderLoginForm());
    } else if (session.onboarding_status === 'pending_profile') {
      container.appendChild(renderHeader());
      container.appendChild(renderOnboardingForm());
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
    } else if (focusedId === 'vp-stock-search' || focusedId?.startsWith('vp-matrix-count-')) {
      const input = document.getElementById(focusedId); input?.focus();
      if (typeof selection === 'number') { try { input?.setSelectionRange(selection, typeof selectionEnd === 'number' ? selectionEnd : selection); } catch {} }
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
        const restored = await loginVendor(uname, pwd);
        if (destroyed) return;
        session = restored;
        if (session.onboarding_status === 'pending_profile') {
          isLoading = false;
          render();
          return;
        }
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
    const isPending = session.onboarding_status === 'pending_profile';
    const header = document.createElement('header');
    header.className = 'vp-header';
    header.innerHTML = `
      <div class="vp-header-left">
        <h1 class="vp-shop-badge">${escapeHtml(session.vendor_name)}</h1>
        <div class="vp-role-pill">Stock workspace</div>
      </div>
      <div class="vp-header-right">
        ${!isPending ? `
        <button type="button" class="vp-btn vp-btn-outline vp-btn-sm" id="vp-refresh-btn" ${saving ? 'disabled' : ''}>Refresh stock</button>
        <button type="button" class="vp-btn vp-btn-outline vp-btn-sm" id="vp-history-btn" ${saving ? 'disabled' : ''}>
          Update history
        </button>` : ''}
        <button type="button" class="vp-btn vp-btn-subtle vp-btn-sm" id="vp-logout-btn" title="Sign out ${escapeHtml(session.username)}">
          Sign out (${escapeHtml(session.username)})
        </button>
      </div>
    `;

    header.querySelector('#vp-history-btn')?.addEventListener('click', openHistoryModal);
    header.querySelector('#vp-refresh-btn')?.addEventListener('click', () => { notice = ''; loadStock(); });
    header.querySelector('#vp-logout-btn').addEventListener('click', async () => {
      batchGeneration++; stockRequest++;
      drafts.clear();
      header.querySelector('#vp-logout-btn').disabled = true;
      try {
        await logoutVendor();
      } finally {
        session = null;
        saving = false;
        activeModal = null;
        stockItems = [];
        searchQuery = ''; page = 1; totalItems = 0;
        notice = '';
        render();
      }
    });

    return header;
  }

  function renderOnboardingForm() {
    const wrap = document.createElement('div');
    wrap.className = 'vp-onboard-container';
    wrap.innerHTML = `
      <div class="vp-onboard-card">
        <div class="vp-onboard-header">
          <div class="vp-onboard-badge">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
            <span>Action Required · Profile Setup</span>
          </div>
          <h2 class="vp-onboard-title">Complete Your Vendor Profile</h2>
          <p class="vp-onboard-desc">
            Welcome to AlphaZee! To unlock your stock counting workspace and activate logistics pickups, please provide your representative details, warehouse dispatch address, and settlement bank account.
          </p>
        </div>

        <div id="vp-onboard-error" class="vp-alert vp-alert-error" style="display: none; margin-bottom: 20px;" role="alert"></div>

        <form id="vp-onboard-form" class="vp-form">
          <div class="vp-onboard-section-title">1. Legal &amp; Authorized Representative</div>
          <div class="vp-onboard-grid">
            <div class="vp-form-group">
              <label for="vp-contact-person" class="vp-form-label">Contact Person Name *</label>
              <input type="text" id="vp-contact-person" class="vp-input" required placeholder="e.g. Muhammad Usman" autocomplete="name" />
            </div>
            <div class="vp-form-group">
              <label for="vp-cnic" class="vp-form-label">CNIC / National Identity *</label>
              <input type="text" id="vp-cnic" class="vp-input" required placeholder="42101-1234567-1" autocomplete="off" />
            </div>
            <div class="vp-form-group">
              <label for="vp-ntn" class="vp-form-label">NTN / Tax Number (Optional)</label>
              <input type="text" id="vp-ntn" class="vp-input" placeholder="e.g. 1234567-8" autocomplete="off" />
            </div>
            <div class="vp-form-group">
              <label for="vp-email" class="vp-form-label">Official Email (Optional)</label>
              <input type="email" id="vp-email" class="vp-input" placeholder="vendor@alphazee.pk" autocomplete="email" />
            </div>
          </div>

          <div class="vp-onboard-section-title">2. Warehouse &amp; Logistics</div>
          <div class="vp-onboard-grid">
            <div class="vp-form-group vp-col-span-2">
              <label for="vp-warehouse-address" class="vp-form-label">Warehouse / Dispatch Pickup Address *</label>
              <textarea id="vp-warehouse-address" class="vp-input" rows="2" required placeholder="Plot #, Street, Industrial Area / Market" style="resize: vertical;"></textarea>
            </div>
            <div class="vp-form-group">
              <label for="vp-city" class="vp-form-label">City *</label>
              <input type="text" id="vp-city" class="vp-input" required placeholder="e.g. Karachi" />
            </div>
            <div class="vp-form-group">
              <label for="vp-lead-time" class="vp-form-label">Dispatch Lead Time (Days) *</label>
              <input type="number" id="vp-lead-time" class="vp-input" required min="1" max="14" value="2" />
            </div>
          </div>

          <div class="vp-onboard-section-title">3. Settlement Bank Account</div>
          <div class="vp-onboard-grid">
            <div class="vp-form-group">
              <label for="vp-bank-name" class="vp-form-label">Bank Name *</label>
              <input type="text" id="vp-bank-name" class="vp-input" required placeholder="e.g. Meezan Bank / Bank Alfalah" />
            </div>
            <div class="vp-form-group">
              <label for="vp-bank-title" class="vp-form-label">Account Title *</label>
              <input type="text" id="vp-bank-title" class="vp-input" required placeholder="Account title as per cheque" />
            </div>
            <div class="vp-form-group vp-col-span-2">
              <label for="vp-bank-iban" class="vp-form-label">Bank IBAN (24 Characters) *</label>
              <input type="text" id="vp-bank-iban" class="vp-input" required placeholder="PK36MEZN0000001234567890" maxlength="34" style="font-family: monospace; letter-spacing: 0.05em;" />
            </div>
          </div>

          <div class="vp-terms-row">
            <input type="checkbox" id="vp-terms-accept" required />
            <label for="vp-terms-accept">
              I certify that all details submitted are accurate and that all merchandise supplied to AlphaZee will strictly match sample quality standards and pass the mandatory 7-day inspection window before settlement payout.
            </label>
          </div>

          <div style="margin-top: 24px;">
            <button type="submit" id="vp-btn-submit-onboard" class="vp-btn vp-btn-primary" style="width: 100%; min-height: 44px; font-weight: 600; font-size: 14px;">
              Save Profile &amp; Unlock Workspace
            </button>
          </div>
        </form>
      </div>
    `;

    const form = wrap.querySelector('#vp-onboard-form');
    const errBox = wrap.querySelector('#vp-onboard-error');
    const submitBtn = wrap.querySelector('#vp-btn-submit-onboard');

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      errBox.style.display = 'none';
      submitBtn.disabled = true;
      submitBtn.textContent = 'Saving Profile & Verifying...';

      const payload = {
        contact_person: form.querySelector('#vp-contact-person').value.trim(),
        cnic: form.querySelector('#vp-cnic').value.trim(),
        ntn: form.querySelector('#vp-ntn').value.trim() || null,
        email: form.querySelector('#vp-email').value.trim() || null,
        warehouse_address: form.querySelector('#vp-warehouse-address').value.trim(),
        city: form.querySelector('#vp-city').value.trim(),
        lead_time_days: parseInt(form.querySelector('#vp-lead-time').value, 10) || 2,
        bank_name: form.querySelector('#vp-bank-name').value.trim(),
        bank_account_title: form.querySelector('#vp-bank-title').value.trim(),
        bank_iban: form.querySelector('#vp-bank-iban').value.trim(),
      };

      try {
        await updateVendorProfile(payload);
        session.onboarding_status = 'active';
        await loadStock();
        render();
      } catch (err) {
        errBox.textContent = err.message || 'Failed to complete profile onboarding.';
        errBox.style.display = 'flex';
        submitBtn.disabled = false;
        submitBtn.textContent = 'Save Profile & Unlock Workspace';
      }
    });

    return wrap;
  }

  function renderStatsBar() {
    const totalOnHand = stockItems.reduce((acc, i) => acc + (i.allocated_on_hand || 0), 0);
    const totalHeld = stockItems.reduce((acc, i) => acc + (i.held_quantity || 0), 0);
    const totalAvail = stockItems.reduce((acc, i) => acc + (i.available_quantity || 0), 0);

    const bar = document.createElement('section');
    bar.className = 'vp-stats-bar';
    bar.innerHTML = `
      <div class="vp-stat-card">
        <div class="vp-stat-label">${searchQuery ? 'Matching items' : 'Total assigned items'}</div>
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
        <input type="search" id="vp-stock-search" class="vp-input" placeholder="Search name, SKU, size or color" value="${escapeHtml(searchQuery)}" ${saving ? 'disabled' : ''} />
        ${searchQuery ? '<button type="button" class="vp-search-clear" id="vp-clear-search" aria-label="Clear search">Clear</button>' : ''}
      </div>
    `;

    const input = bar.querySelector('#vp-stock-search');
    input.addEventListener('input', (e) => {
      searchQuery = e.target.value;
      page = 1;
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        loadStock();
      }, 300);
    });

    const clearBtn = bar.querySelector('#vp-clear-search');
    if (clearBtn) {
      clearBtn.disabled = saving;
      clearBtn.addEventListener('click', () => {
        searchQuery = '';
        page = 1;
        loadStock();
      });
    }

    return bar;
  }

  function renderMatrix(items = stockItems) {
    return createVendorStockMatrix({
      items, totalItems, limit, drafts, saving,
      onSave: prepareCounts, onCount: openCountModal, onShortage: openShortageModal,
      onDiscard: () => {
        restoreFocusId = 'vp-stock-search';
        activeModal = { type: 'matrixConfirm', title: 'Discard pending counts?',
          description: 'This removes your unsaved edits, including edits on other pages. Saved stock and reported shortages stay unchanged.',
          confirmLabel: 'Discard edits', action: () => { drafts.clear(); render(); document.getElementById('vp-stock-search')?.focus(); } };
        render();
      },
    });
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
          <h3>${totalItems > 0 ? 'This page has no items' : 'No assigned items found'}</h3>
          <p>${totalItems > 0 ? 'Inventory changed. Return to the first page to see your assigned stock.' : searchQuery ? 'No variants match your search filter.' : 'Your shop does not have active variants assigned yet.'}</p>
          ${totalItems > 0 ? '<button type="button" class="vp-btn vp-btn-outline" id="vp-first-page">Return to first page</button>' : ''}
        </div>
      `;
      if (drafts.pending().length) content.prepend(renderMatrix([]));
      content.querySelector('#vp-first-page')?.addEventListener('click', () => { page = 1; loadStock(); });
      return content;
    }

    content.appendChild(renderMatrix());
    const pages = Math.ceil(totalItems / limit);
    if (pages > 1) {
      const nav = document.createElement('nav'); nav.className = 'vp-pagination'; nav.setAttribute('aria-label', 'Stock pages');
      nav.innerHTML = `<button class="vp-btn vp-btn-outline" id="vp-prev-page" ${saving || page <= 1 ? 'disabled' : ''}>Previous</button><span>Page ${page} of ${pages}</span><button class="vp-btn vp-btn-outline" id="vp-next-page" ${saving || page >= pages ? 'disabled' : ''}>Next</button>`;
      nav.querySelector('#vp-prev-page').addEventListener('click', () => { page--; loadStock(); });
      nav.querySelector('#vp-next-page').addEventListener('click', () => { page++; loadStock(); });
      content.appendChild(nav);
    }
    return content;
  }

  function openCountModal(item) {
    restoreFocusId = `vp-count-open-${item.variant_id}`;
    activeModal = { type: 'count', item, initialCount: parseVendorCount(drafts.get(item.variant_id)?.value) ?? item.allocated_on_hand };
    render();
  }

  function prepareCounts(ids, focusId) {
    if (saving || !session) return;
    const changes = drafts.snapshot(ids);
    if (!changes.length) return;
    if (changes.some(change => change.count === null || change.needsReview)) {
      notice = 'Check invalid or conflicting counts before saving.'; render(); return;
    }
    restoreFocusId = focusId;
    const belowHolds = changes.filter(change => change.count < change.item.held_quantity);
    if (belowHolds.length) {
      activeModal = { type: 'matrixConfirm', title: 'Counts below customer holds',
        description: 'Below-hold counts create shortage reports for owner review. Recorded stock and existing reservations stay intact. Other changed sizes save separately.',
        changes: belowHolds, confirmLabel: 'Report shortages and save counts', action: () => saveCounts(changes) };
      render();
    } else saveCounts(changes);
  }

  async function saveCounts(changes) {
    if (saving || !session || destroyed) return;
    const actor = session, generation = ++batchGeneration;
    clearTimeout(debounceTimer);
    stockRequest++; refreshing = false;
    saving = true; let saved = 0, reported = 0, failed = 0;
    for (const [index, change] of changes.entries()) {
      if (session !== actor || destroyed || generation !== batchGeneration) return;
      const id = change.item.variant_id;
      drafts.saving(id);
      notice = `Saving size ${index + 1} of ${changes.length}…`;
      render();
      try {
        const result = await updateVendorStockCount(id, { counted_quantity: change.count,
          expected_version: change.baseVersion, reason: 'manual_count', request_ref: change.requestRef });
        if (session !== actor || destroyed || generation !== batchGeneration) return;
        drafts.acknowledge(id, result);
        stockItems = stockItems.map(item => item.variant_id === id ? { ...item, ...result } : item);
        result.shortage_detected ? reported++ : saved++;
      } catch (error) {
        if (session !== actor || destroyed || generation !== batchGeneration) return;
        drafts.fail(id, error); failed++;
      }
    }
    if (session !== actor || destroyed || generation !== batchGeneration) return;
    saving = false;
    notice = `${saved} saved · ${reported} shortage reports · ${failed} not saved${failed ? '. Unsaved edits are kept; review each row.' : ''}`;
    render();
    await loadStock({ quiet: true });
    if (session === actor && !destroyed) {
      const opener = document.getElementById(restoreFocusId);
      (opener && !opener.disabled ? opener : document.getElementById(`vp-matrix-count-${changes[0].item.variant_id}`) || document.getElementById('vp-stock-search'))?.focus();
    }
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

    if (activeModal.type === 'matrixConfirm') {
      const confirmation = activeModal;
      dialog.innerHTML = `<div class="vp-modal-header"><h2 id="vp-modal-title">${escapeHtml(confirmation.title)}</h2><button type="button" class="vp-modal-close" id="vp-close-modal" aria-label="Close dialog">×</button></div>
        <div class="vp-modal-body"><p class="vp-modal-desc">${escapeHtml(confirmation.description)}</p>
        ${confirmation.changes ? `<ul class="vp-confirm-counts">${confirmation.changes.map(change => `<li><strong>${escapeHtml(change.item.variant_sku)}</strong>: ${change.count} counted, ${change.item.held_quantity} held</li>`).join('')}</ul>` : ''}
        <div class="vp-modal-actions"><button type="button" class="vp-btn vp-btn-outline" id="vp-cancel-count">Cancel</button><button type="button" class="vp-btn vp-btn-primary" id="vp-confirm-matrix">${escapeHtml(confirmation.confirmLabel)}</button></div></div>`;
      dialog.querySelector('#vp-confirm-matrix').addEventListener('click', () => { activeModal = null; render(); confirmation.action(); });
    } else if (activeModal.type === 'count') {
      const item = activeModal.item;
      let currentVal = activeModal.initialCount;

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
                <input type="number" id="vp-new-count" class="vp-input vp-step-input" min="0" max="${MAX_VENDOR_COUNT}" step="1" inputmode="numeric" value="${currentVal}" required />
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
        if (parseVendorCount(input.value) === null) {
          modalError(dialog, 'Enter a whole number of units, zero or more.'); return;
        }
        saving = true;
        const submitBtn = dialog.querySelector('#vp-submit-count');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Saving…';

        const newCount = parseInt(input.value, 10);
        const reason = dialog.querySelector('#vp-reason').value;
        const note = dialog.querySelector('#vp-note').value.trim();
        const actor = session, modal = activeModal;

        try {
          const res = await updateVendorStockCount(item.variant_id, {
            counted_quantity: newCount,
            expected_version: item.version,
            reason,
            note: note || undefined,
          });
          if (destroyed || session !== actor || activeModal !== modal) return;

          // Show confirmation message
          saving = false;
          activeModal = null;
          notice = res.shortage_detected ? res.message : `Stock count saved: ${newCount} units. Customer holds are preserved.`;
          drafts.reset(item.variant_id);
          await loadStock();
          document.getElementById(restoreFocusId)?.focus();
        } catch (err) {
          if (destroyed || session !== actor || activeModal !== modal) return;
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
        if (parseVendorCount(countValue) === null) {
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
        const actor = session, modal = activeModal;

        try {
          await reportVendorShortage(item.variant_id, {
            reported_count: reportedCount,
            note,
          });
          if (destroyed || session !== actor || activeModal !== modal) return;
          saving = false;
          activeModal = null;
          notice = 'Shortage reported. AlphaZee will review it; customer holds remain protected.';
          await loadStock();
          document.getElementById(restoreFocusId)?.focus();
        } catch (err) {
          if (destroyed || session !== actor || activeModal !== modal) return;
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
  const refreshVisible = () => { if (session && !saving && !isLoading && !refreshing && !activeModal && document.visibilityState !== 'hidden') loadStock({ quiet: true }); };
  const storageRefresh = event => { if (event.key === 'alphazee_catalog_changed') refreshVisible(); };
  const poll = window.setInterval(refreshVisible, 30000);
  window.addEventListener('focus', refreshVisible);
  window.addEventListener('pageshow', refreshVisible);
  window.addEventListener('storage', storageRefresh);
  document.addEventListener('visibilitychange', refreshVisible);
  return { destroy() { destroyed = true; batchGeneration++; stockRequest++; drafts.clear(); stockItems = []; session = null; window.clearInterval(poll); clearTimeout(debounceTimer); unsubscribeSession(); document.removeEventListener('keydown', modalKeys); window.removeEventListener('focus', refreshVisible); window.removeEventListener('pageshow', refreshVisible); window.removeEventListener('storage', storageRefresh); document.removeEventListener('visibilitychange', refreshVisible); document.body.style.overflow = previousOverflow; root.textContent = ''; } };
}
