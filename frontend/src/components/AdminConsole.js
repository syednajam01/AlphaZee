import { createOverlay } from '../utils/overlay.js';
import { createBrandLogo } from './BrandLogo.js';
import {
  fetchAdminOverview,
  fetchAdminInventory,
  adjustAdminInventory,
  fetchAdminOrders,
  verifyOrderPayment,
  confirmSupplierAcceptance,
  reviewExpiredOrders,
  fetchPaymentInstructionsPreview,
  markPaymentInstructionsSent,
  resolvePaymentReview,
  deliverOrder,
  cancelOrder,
  initiateOrderRto,
  receiveOrderRto,
  inspectAndRestockRtoOrder,
  previewLegacyShipmentStock,
  reconcileLegacyShipmentStock,
  dispatchAdminOrder,
  updateAdminShipmentStatus,
  recordAdminCodRemittance,
  fetchAdminShipmentSettlement,
  recordAdminRefundExecution,
  fetchAdminSuppliers,
  createAdminSupplier,
  assignSupplierVariant,
  fetchAdminProfitLoss,
  fetchAdminCoupons,
  createAdminCoupon,
  deleteAdminCoupon,
  fetchAdminReturns,
  approveAdminReturn,
  dispatchAdminReplacement,
  inspectAdminShipmentRto,
  recoverAdminOrderAccess,
  revokeAdminOrderAccess,
  receiveAdminReturn,
  inspectAdminReturn,
  completeAdminReturn,
  rejectAdminReturn,
  fetchAdminMarketingAnalytics,
  ApiError,
  loginOwner,
  logoutOwner,
  fetchOwnerSession,
  onOwnerSessionExpired,
  removeLegacyAdminCredentials,
} from '../utils/api.js';
import { escapeHtml } from '../utils/dom.js';
import { formatPkr, pkrToMinor } from '../utils/money.js';

export function createAdminConsoleModal() {
  const modal = document.createElement('div');
  modal.className = 'modal-container';
  modal.id = 'admin-modal';
  modal.setAttribute('role', 'dialog');
  modal.setAttribute('aria-label', 'AlphaZee Store Management Console');

  let activeTab = 'overview';
  let authenticated = false;
  let currentRemitOutstandingMinor = 0;
  let authGeneration = 0;
  removeLegacyAdminCredentials();
  let isCollapsed = false;

  modal.innerHTML = `
    <div class="drawer-backdrop" style="z-index: 1;"></div>
    <div class="modal-content" style="z-index: 2; max-width: 1100px; height: 720px; padding: 0; display: flex; overflow: hidden; background: #141715; color: #FFFFFF; border-radius: var(--radius-card); border: 1px solid rgba(255, 255, 255, 0.12); box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);">
      
      <!-- Admin Sidebar -->
      <aside id="admin-sidebar" style="width: 220px; background: #0E100F; border-right: 1px solid rgba(255, 255, 255, 0.08); display: flex; flex-direction: column; transition: width 200ms ease; flex-shrink: 0;">
        <!-- Sidebar Brand Header -->
        <div style="height: 60px; display: flex; align-items: center; justify-content: space-between; padding: 0 16px; border-bottom: 1px solid rgba(255, 255, 255, 0.08);">
          <div id="admin-expanded-logo-slot"></div>
          <div id="admin-collapsed-logo-slot" style="display: none;"></div>
          
          <button id="btn-toggle-admin-sidebar" class="btn-icon" style="color: rgba(255, 255, 255, 0.7); padding: 4px;" aria-label="Toggle sidebar collapse">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
              <line x1="9" y1="3" x2="9" y2="21"></line>
            </svg>
          </button>
        </div>

        <!-- Sidebar Navigation -->
        <nav style="flex: 1; padding: 12px 8px; display: flex; flex-direction: column; gap: 4px;">
          <button type="button" class="admin-tab-btn" data-tab="overview" style="display: flex; align-items: center; gap: 10px; width: 100%; padding: 10px 12px; border-radius: 6px; background: rgba(20, 92, 68, 0.4); color: #FFFFFF; border: none; font-size: 0.8125rem; font-weight: 600; cursor: pointer; text-align: left;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
            </svg>
            <span class="admin-nav-label">Overview</span>
          </button>

          <button type="button" class="admin-tab-btn" data-tab="orders" style="display: flex; align-items: center; gap: 10px; width: 100%; padding: 10px 12px; border-radius: 6px; background: transparent; color: rgba(255, 255, 255, 0.7); border: none; font-size: 0.8125rem; font-weight: 600; cursor: pointer; text-align: left;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="9" cy="21" r="1"></circle>
              <circle cx="20" cy="21" r="1"></circle>
              <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>
            </svg>
            <span class="admin-nav-label">Orders & Logistics</span>
          </button>

          <button type="button" class="admin-tab-btn" data-tab="inventory" style="display: flex; align-items: center; gap: 10px; width: 100%; padding: 10px 12px; border-radius: 6px; background: transparent; color: rgba(255, 255, 255, 0.7); border: none; font-size: 0.8125rem; font-weight: 600; cursor: pointer; text-align: left;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
              <polyline points="2 17 12 22 22 17"></polyline>
              <polyline points="2 12 12 17 22 12"></polyline>
            </svg>
            <span class="admin-nav-label">Inventory & Stock</span>
          </button>

          <button type="button" class="admin-tab-btn" data-tab="coupons" style="display: flex; align-items: center; gap: 10px; width: 100%; padding: 10px 12px; border-radius: 6px; background: transparent; color: rgba(255, 255, 255, 0.7); border: none; font-size: 0.8125rem; font-weight: 600; cursor: pointer; text-align: left;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"></path>
              <line x1="7" y1="7" x2="7.01" y2="7"></line>
            </svg>
            <span class="admin-nav-label">Coupons & Promos</span>
          </button>

          <button type="button" class="admin-tab-btn" data-tab="returns" style="display: flex; align-items: center; gap: 10px; width: 100%; padding: 10px 12px; border-radius: 6px; background: transparent; color: rgba(255, 255, 255, 0.7); border: none; font-size: 0.8125rem; font-weight: 600; cursor: pointer; text-align: left;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="1 4 1 10 7 10"></polyline>
              <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path>
            </svg>
            <span class="admin-nav-label">Returns & Refunds</span>
          </button>

          <button type="button" class="admin-tab-btn" data-tab="suppliers" style="display: flex; align-items: center; gap: 10px; width: 100%; padding: 10px 12px; border-radius: 6px; background: transparent; color: rgba(255, 255, 255, 0.7); border: none; font-size: 0.8125rem; font-weight: 600; cursor: pointer; text-align: left;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
              <circle cx="9" cy="7" r="4"></circle>
              <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
              <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
            </svg>
            <span class="admin-nav-label">Suppliers</span>
          </button>

          <button type="button" class="admin-tab-btn" data-tab="analytics" style="display: flex; align-items: center; gap: 10px; width: 100%; padding: 10px 12px; border-radius: 6px; background: transparent; color: rgba(255, 255, 255, 0.7); border: none; font-size: 0.8125rem; font-weight: 600; cursor: pointer; text-align: left;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="20" x2="18" y2="10"></line>
              <line x1="12" y1="20" x2="12" y2="4"></line>
              <line x1="6" y1="20" x2="6" y2="14"></line>
            </svg>
            <span class="admin-nav-label">P&L & Analytics</span>
          </button>
        </nav>

        <div style="padding: 12px 16px; border-top: 1px solid rgba(255, 255, 255, 0.08); display: flex; align-items: center; justify-content: space-between; font-size: 0.75rem; color: rgba(255, 255, 255, 0.4);">
          <span class="admin-nav-label">Owner Ops v1.2</span>
          <button id="btn-admin-logout" title="Sign out" style="background: none; border: none; color: rgba(255, 255, 255, 0.5); cursor: pointer; padding: 2px 4px; font-size: 0.75rem;">Sign out</button>
        </div>
      </aside>

      <!-- Main Admin Content Area -->
      <main style="flex: 1; display: flex; flex-direction: column; overflow: hidden; background: #141715;">
        <!-- Top Bar -->
        <header style="height: 60px; display: flex; align-items: center; justify-content: space-between; padding: 0 24px; border-bottom: 1px solid rgba(255, 255, 255, 0.08); background: #181C1A;">
          <div>
            <h2 id="admin-view-title" style="font-size: 1rem; font-weight: 700; margin: 0; color: #FFFFFF;">Store Overview & Metrics</h2>
          </div>
          <div style="display: flex; align-items: center; gap: 12px;">
            <button id="btn-refresh-admin-tab" class="btn btn-secondary" style="padding: 6px 12px; font-size: 0.75rem; color: #FFFFFF; border-color: rgba(255, 255, 255, 0.2);">
              ↻ Refresh
            </button>
            <button class="btn-icon" id="admin-close-btn" style="color: rgba(255, 255, 255, 0.7);" aria-label="Close admin console">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>
        </header>

        <!-- Body View Container -->
        <p id="admin-session-message" role="status" style="color:#FCA5A5;"></p>
          <div id="admin-tab-content" style="flex: 1; padding: 24px; overflow-y: auto;">
          <div style="text-align: center; color: rgba(255, 255, 255, 0.5); padding: 40px 0;">Loading administrative metrics...</div>
        </div>
      </main>
    </div>

    <!-- Dispatch Courier Dialog Modal -->
    <div id="admin-dispatch-modal" style="display: none; position: fixed; inset: 0; z-index: 100; align-items: center; justify-content: center; background: rgba(0, 0, 0, 0.7);">
      <div style="background: #1A1D1C; border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 8px; width: 440px; padding: 20px; color: #FFF; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);">
        <h3 style="font-size: 1rem; font-weight: 700; margin: 0 0 12px 0;">Dispatch Order via Courier</h3>
        <form id="admin-dispatch-form" style="display: flex; flex-direction: column; gap: 10px;">
          <input type="hidden" id="dispatch-order-id" />
          <div>
            <label style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); display: block; margin-bottom: 2px;">Select Courier *</label>
            <select id="dispatch-courier-code" style="width: 100%; padding: 8px 12px; background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 6px; font-size: 0.8125rem;">
              <option value="trax">Trax Logistics</option>
              <option value="leopards">Leopards Courier</option>
              <option value="call_courier">Call Courier</option>
              <option value="postex">PostEx</option>
              <option value="tcs">TCS Express</option>
              <option value="mnp">M&P Express</option>
              <option value="manual">AlphaZee Direct Dispatch</option>
            </select>
          </div>
          <div>
            <label style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); display: block; margin-bottom: 2px;">Tracking Number / Waybill ID *</label>
            <input type="text" id="dispatch-tracking-number" required placeholder="e.g. TRX-12345678" style="width: 100%; padding: 8px 12px; background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 6px; font-size: 0.8125rem;" />
          </div>
          <div>
            <label style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); display: block; margin-bottom: 2px;">Courier Fee Charged to AlphaZee (PKR)</label>
            <input type="number" id="dispatch-shipping-cost" value="250" min="0" step="10" style="width: 100%; padding: 8px 12px; background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 6px; font-size: 0.8125rem;" />
          </div>
          <div>
            <label style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); display: block; margin-bottom: 2px;">Tracking Web URL (Optional)</label>
            <input type="url" id="dispatch-tracking-url" placeholder="https://trax.pk/tracking?num=..." style="width: 100%; padding: 8px 12px; background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 6px; font-size: 0.8125rem;" />
          </div>
          <div id="dispatch-error" style="display: none; color: #F87171; font-size: 0.75rem; font-weight: 600;"></div>
          <div style="display: flex; gap: 8px; justify-content: flex-end; margin-top: 10px;">
            <button type="button" id="btn-cancel-dispatch" class="btn btn-secondary" style="padding: 6px 12px; font-size: 0.8125rem;">Cancel</button>
            <button type="submit" id="btn-submit-dispatch" disabled class="btn btn-primary" style="padding: 6px 14px; font-size: 0.8125rem;">Dispatch unavailable</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Record Remittance Dialog Modal -->
    <div id="admin-remittance-modal" style="display: none; position: fixed; inset: 0; z-index: 100; align-items: center; justify-content: center; background: rgba(0, 0, 0, 0.7);">
      <div style="background: #1A1D1C; border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 8px; width: 420px; padding: 20px; color: #FFF; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);">
        <h3 style="font-size: 1rem; font-weight: 700; margin: 0 0 12px 0;">Record COD Bank Remittance</h3>
        <form id="admin-remittance-form" style="display: flex; flex-direction: column; gap: 10px;">
          <input type="hidden" id="remit-shipment-id" />
          <div id="remit-summary" style="font-size: .8rem; color: #FBBF24;"></div>
          <div id="remit-history" style="font-size: .72rem; max-height: 90px; overflow: auto;"></div>
          <div>
            <label style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); display: block; margin-bottom: 2px;">New cash received in bank (PKR; 0 for deduction only)</label>
            <input type="number" id="remit-amount-pkr" required min="0" step="0.01" value="0" style="width: 100%; padding: 8px 12px; background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 6px; font-size: 0.8125rem;" />
          </div>
          <div>
            <label style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); display: block; margin-bottom: 2px;">Bank payout reference (required for cash)</label>
            <input type="text" id="remit-ref" placeholder="e.g. TRAX-WEEKLY-PAYOUT-OCT" style="width: 100%; padding: 8px 12px; background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 6px; font-size: 0.8125rem;" />
          </div>
          <label style="font-size: .75rem;">Documented deduction (optional)
            <select id="remit-deduction-type"><option value="">None</option><option value="outbound_shipping">Outbound courier fee</option><option value="rto_shipping">RTO courier fee</option><option value="other_deduction">Other documented deduction</option></select>
          </label>
          <input type="number" id="remit-deduction-pkr" min="0" step="0.01" placeholder="Deduction amount PKR" />
          <input type="text" id="remit-deduction-ref" maxlength="120" placeholder="Deduction invoice/reference" />
          <input type="text" id="remit-deduction-note" maxlength="500" placeholder="Evidence note (at least 5 characters)" />
          <label style="font-size: .75rem;"><input type="checkbox" id="remit-final-statement" /> Courier marked this as the final payout</label>
          <div id="remit-error" style="display: none; color: #F87171; font-size: 0.75rem; font-weight: 600;"></div>
          <div style="display: flex; gap: 8px; justify-content: flex-end; margin-top: 10px;">
            <button type="button" id="btn-cancel-remit" class="btn btn-secondary" style="padding: 6px 12px; font-size: 0.8125rem;">Cancel</button>
            <button type="submit" id="btn-submit-remit" class="btn btn-primary" style="padding: 6px 14px; font-size: 0.8125rem;">Record settlement</button>
          </div>
        </form>
      </div>
    </div>
  `;

  // Mount Logos in Sidebar
  const expandedLogoSlot = modal.querySelector('#admin-expanded-logo-slot');
  const collapsedLogoSlot = modal.querySelector('#admin-collapsed-logo-slot');
  if (expandedLogoSlot) {
    const fullLogo = createBrandLogo({ variant: 'combined', height: '24px' });
    fullLogo.style.filter = 'brightness(0) invert(1)';
    expandedLogoSlot.appendChild(fullLogo);
  }
  if (collapsedLogoSlot) {
    const markLogo = createBrandLogo({ variant: 'mark', height: '24px' });
    markLogo.style.filter = 'brightness(0) invert(1)';
    collapsedLogoSlot.appendChild(markLogo);
  }

  // Sidebar Collapse Toggle
  const sidebar = modal.querySelector('#admin-sidebar');
  const toggleBtn = modal.querySelector('#btn-toggle-admin-sidebar');
  toggleBtn?.addEventListener('click', () => {
    isCollapsed = !isCollapsed;
    sidebar.style.width = isCollapsed ? '64px' : '220px';
    modal.querySelectorAll('.admin-nav-label').forEach(el => {
      el.style.display = isCollapsed ? 'none' : 'inline';
    });
    if (expandedLogoSlot) expandedLogoSlot.style.display = isCollapsed ? 'none' : 'block';
    if (collapsedLogoSlot) collapsedLogoSlot.style.display = isCollapsed ? 'block' : 'none';
  });

  // Tab Navigation Handling
  const tabBtns = modal.querySelectorAll('.admin-tab-btn');
  const contentArea = modal.querySelector('#admin-tab-content');
  const viewTitle = modal.querySelector('#admin-view-title');

  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const tab = btn.getAttribute('data-tab');
      if (tab === activeTab) return;
      activeTab = tab;

      tabBtns.forEach(b => {
        b.style.background = 'transparent';
        b.style.color = 'rgba(255, 255, 255, 0.7)';
      });
      btn.style.background = 'rgba(20, 92, 68, 0.4)';
      btn.style.color = '#FFFFFF';

      const titles = {
        overview: 'Store Overview & Metrics',
        orders: 'Orders & Logistics Management',
        inventory: 'Real-Time Inventory & Stock Balance',
        coupons: 'Promotional Coupons & Voucher Codes',
        returns: 'Customer Returns & Size Exchanges',
        suppliers: 'Approved Suppliers & Cost Mapping',
        analytics: 'Gross Profit, COGS & Attribution',
      };
      if (viewTitle) viewTitle.textContent = titles[tab] || 'Store Management';

      loadActiveTabData();
    });
  });

  modal.querySelector('#btn-refresh-admin-tab')?.addEventListener('click', () => {
    loadActiveTabData();
  });

  modal.querySelector('#btn-admin-logout')?.addEventListener('click', async () => {
    const button = modal.querySelector('#btn-admin-logout');
    button.disabled = true;
    try {
      await logoutOwner();
      authenticated = false;
      renderLogin('You have signed out.');
    } catch (error) {
      if (error.status !== 401) {
        // Keep the session visible if the server could not confirm revocation.
        showSessionMessage('Could not sign out. Please try again.');
      }
    } finally { button.disabled = false; }
  });

  function showSessionMessage(message) {
    const status = modal.querySelector('#admin-session-message');
    status.textContent = message;
  }

  function renderLogin(message = '') {
    authGeneration++;
    showSessionMessage(message);
    modal.querySelector('#btn-admin-logout').hidden = true;
    contentArea.innerHTML = `
      <div style="max-width: 440px; margin: 40px auto; padding: 24px;">
        <h3>Owner sign in</h3>
        <p>Sign in to manage your store.</p>
        <form id="admin-auth-form" style="display:flex; flex-direction:column; gap:12px;">
          <label for="admin-username">Username</label>
          <input id="admin-username" name="username" autocomplete="username" required maxlength="100" />
          <label for="admin-password">Password</label>
          <input id="admin-password" name="password" type="password" autocomplete="current-password" required maxlength="128" />
          <p id="admin-login-error" role="alert"></p>
          <button type="submit" class="btn btn-primary" id="admin-login-submit">Sign in</button>
        </form>
      </div>`;
    const form = contentArea.querySelector('#admin-auth-form');
    form.addEventListener('submit', async event => {
      event.preventDefault();
      const button = form.querySelector('#admin-login-submit');
      if (button.disabled) return;
      const passwordInput = form.querySelector('#admin-password');
      const generation = authGeneration;
      button.disabled = true;
      form.querySelector('#admin-login-error').textContent = '';
      try {
        await loginOwner(form.querySelector('#admin-username').value.trim(), passwordInput.value);
        passwordInput.value = '';
        if (generation !== authGeneration) return;
        authenticated = true;
        showSessionMessage('');
        modal.querySelector('#btn-admin-logout').hidden = false;
        await loadActiveTabData();
      } catch (error) {
        passwordInput.value = '';
        if (generation === authGeneration) form.querySelector('#admin-login-error').textContent = error.message || 'Unable to sign in.';
      } finally { button.disabled = false; }
    });
  }

  onOwnerSessionExpired(() => {
    authenticated = false;
    renderLogin('Your session has ended. Sign in again to continue.');
  });

  async function loadActiveTabData() {
    if (!contentArea) return;
    if (!authenticated) { renderLogin(); return; }
    const generation = authGeneration;
    contentArea.innerHTML = '<div style="text-align: center; color: rgba(255, 255, 255, 0.5); padding: 40px 0;">Loading data...</div>';

    try {
      if (activeTab === 'overview') {
        await renderOverviewTab(contentArea);
      } else if (activeTab === 'orders') {
        await renderOrdersTab(contentArea);
      } else if (activeTab === 'inventory') {
        await renderInventoryTab(contentArea);
      } else if (activeTab === 'coupons') {
        await renderCouponsTab(contentArea);
      } else if (activeTab === 'returns') {
        await renderReturnsTab(contentArea);
      } else if (activeTab === 'suppliers') {
        await renderSuppliersTab(contentArea);
      } else if (activeTab === 'analytics') {
        await renderAnalyticsTab(contentArea);
      }
      if (generation !== authGeneration && !authenticated) renderLogin('Sign in again to continue.');
    } catch (err) {
      if (err.status === 401) {
        authenticated = false;
        renderLogin('Your session has ended. Sign in again to continue.');
        return;
      }
      if (generation !== authGeneration) return;

      contentArea.innerHTML = `
        <div style="padding: 16px; background: rgba(220, 38, 38, 0.15); border: 1px solid rgba(220, 38, 38, 0.3); border-radius: 6px; color: #FCA5A5; font-size: 0.875rem;">
          Failed to load administrative data: ${escapeHtml(err.message)}
        </div>
      `;
    }
  }

  // 1. Overview Tab
  async function renderOverviewTab(container) {
    const data = await fetchAdminOverview();
    container.innerHTML = `
      <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px;">
        <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 16px;">
          <div style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.5); text-transform: uppercase; font-weight: 600; margin-bottom: 4px;">Verified Gross Revenue</div>
          <div style="font-size: 1.5rem; font-weight: 800; color: #4ADE80;">${escapeHtml(data.formatted_gross_revenue)}</div>
          <div style="font-size: 0.7rem; color: rgba(255, 255, 255, 0.4); margin-top: 4px;">Bank & confirmed COD revenue</div>
        </div>
        <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 16px;">
          <div style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.5); text-transform: uppercase; font-weight: 600; margin-bottom: 4px;">Total Orders</div>
          <div style="font-size: 1.5rem; font-weight: 800; color: #FFFFFF;">${data.total_orders}</div>
          <div style="font-size: 0.7rem; color: rgba(255, 255, 255, 0.4); margin-top: 4px;">${data.pending_orders} pending action</div>
        </div>
        <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 16px;">
          <div style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.5); text-transform: uppercase; font-weight: 600; margin-bottom: 4px;">Active Catalog SKUs</div>
          <div style="font-size: 1.5rem; font-weight: 800; color: #38BDF8;">${data.total_skus}</div>
          <div style="font-size: 0.7rem; color: rgba(255, 255, 255, 0.4); margin-top: 4px;">Linked to suppliers</div>
        </div>
        <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 16px;">
          <div style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.5); text-transform: uppercase; font-weight: 600; margin-bottom: 4px;">Low Stock Alerts</div>
          <div style="font-size: 1.5rem; font-weight: 800; color: ${data.low_stock_skus > 0 ? '#F87171' : '#4ADE80'};">${data.low_stock_skus}</div>
          <div style="font-size: 0.7rem; color: rgba(255, 255, 255, 0.4); margin-top: 4px;">≤ 2 available to sell</div>
        </div>
      </div>
    `;
  }

  // 2. Orders Tab
  async function renderOrdersTab(container) {
    await reviewExpiredOrders();
    const res = await fetchAdminOrders();
    const orders = res.orders || [];

    if (orders.length === 0) {
      container.innerHTML = '<div style="text-align: center; color: rgba(255, 255, 255, 0.5); padding: 40px 0;">No customer orders placed yet.</div>';
      return;
    }

    const rowsHtml = orders.map(o => {
      const isBank = o.payment_method === 'bank_transfer';
      const isPaid = o.payment_status === 'verified';
      const isDelivered = o.order_status === 'delivered';
      const isCancelled = o.order_status === 'cancelled';
      const shipment = o.shipments?.find(s => !s.replacement_return_id) || null;
      const hasShipment = Boolean(shipment);

      return `
        <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.06); font-size: 0.8125rem;">
          <td style="padding: 12px 8px; font-weight: 700; color: #4ADE80;">${escapeHtml(o.order_number)}</td>
          <td style="padding: 12px 8px;">
            <div>${escapeHtml(o.customer_name)}</div>
            <div style="font-size: 0.7rem; color: rgba(255, 255, 255, 0.5);">${escapeHtml(o.customer_phone)} • ${escapeHtml(o.shipping_city)}</div>
          </td>
          <td style="padding: 12px 8px; font-weight: 600;">
            ${o.total.formatted}
            ${o.discount_amount && o.discount_amount.minor > 0 ? `<div style="font-size: 0.7rem; color: #4ADE80;">-${o.discount_amount.formatted} (${escapeHtml(o.coupon_code || 'Promo')})</div>` : ''}
          </td>
          <td style="padding: 12px 8px;">
            <span style="font-size: 0.7rem; text-transform: uppercase; padding: 2px 6px; border-radius: 4px; background: ${o.order_status === 'delivered' ? 'rgba(74, 222, 128, 0.2)' : 'rgba(255, 255, 255, 0.1)'}; color: ${o.order_status === 'delivered' ? '#4ADE80' : '#FFF'};">
              ${escapeHtml(o.order_status)}
            </span>
          </td>
          <td style="padding: 12px 8px;">
            <span style="font-size: 0.7rem; text-transform: uppercase; padding: 2px 6px; border-radius: 4px; background: ${isPaid ? 'rgba(74, 222, 128, 0.2)' : 'rgba(251, 191, 36, 0.2)'}; color: ${isPaid ? '#4ADE80' : '#FBBF24'};">
              ${escapeHtml(o.payment_method)} (${escapeHtml(o.payment_status)})
            </span>
            ${isBank && o.payment_review_status === 'required' ? '<div style="color: #FBBF24; font-size: 0.7rem;">Payment review required; stock reserved</div>' : ''}
            ${isBank && o.payment_instructions_sent_at ? `<div style="font-size: 0.7rem;">Instructions sent ${escapeHtml(new Date(o.payment_instructions_sent_at).toLocaleString())}${o.payment_instructions_channel ? ` via ${escapeHtml(o.payment_instructions_channel)}` : ''}</div>` : ''}
            ${isBank && o.payment_deadline_at ? `<div style="font-size: 0.7rem;">Deadline ${escapeHtml(new Date(o.payment_deadline_at).toLocaleString())}</div>` : ''}
          </td>
          <td style="padding: 12px 8px; text-align: right;">
            <button class="btn btn-secondary btn-recover-order-access" data-order-id="${o.id}" style="padding: 4px 8px; font-size: .7rem;">Recover Access</button>
            <button class="btn btn-secondary btn-revoke-order-access" data-order-id="${o.id}" style="padding: 4px 8px; font-size: .7rem;">Revoke Access</button>
            ${!isPaid && isBank && !isCancelled && o.payment_review_status !== 'required' ? `
              <button class="btn btn-primary btn-verify-payment" data-order-id="${o.id}" style="padding: 4px 8px; font-size: 0.7rem; margin-right: 4px;">
                Verify Bank Transfer
              </button>
            ` : ''}
            ${o.order_status === 'placed' && !isCancelled ? `
              <button class="btn btn-secondary btn-confirm-supplier" data-order-id="${o.id}" style="padding: 4px 8px; font-size: 0.7rem; margin-right: 4px; border-color: rgba(74, 222, 128, 0.4); color: #4ADE80;">
                Confirm Supplier
              </button>
            ` : ''}
            ${isBank && o.order_status === 'confirmed' && !isPaid && !o.payment_instructions_sent_at && o.payment_review_status !== 'required' ? `
              <button class="btn btn-secondary btn-prepare-instructions" data-order-id="${o.id}">Prepare Instructions</button>
            ` : ''}
            ${isBank && o.payment_review_status === 'required' ? `
              <button class="btn btn-secondary btn-resolve-payment" data-order-id="${o.id}">Resolve Payment Review</button>
            ` : ''}
            ${shipment?.stock_reconciliation_status === 'legacy_review' ? `<button class="btn btn-secondary btn-reconcile-stock" data-shipment-id="${shipment.id}" style="padding: 4px 8px; font-size: .7rem; color: #FBBF24;">Review Legacy Stock</button>` : ''}
            ${o.order_status === 'confirmed' && !hasShipment && !isCancelled && (!isBank || isPaid) ? `
              <button class="btn btn-secondary btn-dispatch-order" data-order-id="${o.id}" style="padding: 4px 8px; font-size: 0.7rem; margin-right: 4px;">
                Dispatch Courier
              </button>
            ` : ''}
            ${o.order_status === 'dispatched' ? `
              <button class="btn btn-secondary btn-rto-order" data-order-id="${o.id}" style="padding: 4px 8px; font-size: 0.7rem; margin-right: 4px; color: #FBBF24; border-color: rgba(251, 191, 36, 0.4);">
                Initiate RTO
              </button>
            ` : ''}
            ${shipment?.cod_amount_minor > 0 && (shipment.status === 'delivered' || shipment.delivered_at) ? `
              <button class="btn btn-secondary btn-remit-order" data-shipment-id="${shipment.id}" style="padding: 4px 8px; font-size: .7rem;">COD Settlement (${formatPkr(shipment.settlement_outstanding_minor)})</button>
            ` : ''}
            ${o.order_status === 'rto' && shipment?.status === 'rto_initiated' && shipment.stock_reconciliation_status !== 'legacy_review' ? `
              <button class="btn btn-primary btn-rto-receive" data-order-id="${o.id}" style="padding: 4px 8px; font-size: 0.7rem; margin-right: 4px; background: #E11D48; border-color: #E11D48;">
                Confirm RTO Received
              </button>
            ` : ''}
            ${o.order_status === 'rto' && shipment && shipment.status === 'rto_delivered' && shipment.stock_reconciliation_status !== 'legacy_review' && !shipment.rto_restocked_at ? `
              <button class="btn btn-secondary btn-rto-inspect" data-order-id="${o.id}" style="padding: 4px 8px; font-size: 0.7rem; margin-right: 4px; color: #38BDF8; border-color: rgba(56, 189, 248, 0.4);">
                Inspect & Restock
              </button>
            ` : ''}
            ${!isCancelled && !isDelivered && o.order_status !== 'dispatched' && o.order_status !== 'rto' && !(isBank && (isPaid || o.payment_review_status === 'required' || (o.payment_deadline_at && new Date(o.payment_deadline_at) <= new Date()))) ? `
              <button class="btn btn-secondary btn-cancel-order" data-order-id="${o.id}" style="padding: 4px 8px; font-size: 0.7rem; color: #F87171; border-color: rgba(248, 113, 113, 0.3);">
                Cancel
              </button>
            ` : ''}
          </td>
        </tr>
      `;
    }).join('');

    container.innerHTML = `
      <div style="display: flex; justify-content: flex-end; margin-bottom: 12px;">
        <button id="btn-review-expired-orders" class="btn btn-secondary" style="font-size: 0.75rem; padding: 4px 10px;">
          Check Expired Bank Transfers
        </button>
      </div>
      <div style="overflow-x: auto;">
        <table style="width: 100%; border-collapse: collapse; text-align: left;">
          <thead>
            <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.12); font-size: 0.75rem; color: rgba(255, 255, 255, 0.5); text-transform: uppercase;">
              <th style="padding: 8px;">Order #</th>
              <th style="padding: 8px;">Customer</th>
              <th style="padding: 8px;">Total</th>
              <th style="padding: 8px;">Status</th>
              <th style="padding: 8px;">Payment</th>
              <th style="padding: 8px; text-align: right;">Actions</th>
            </tr>
          </thead>
          <tbody>${rowsHtml}</tbody>
        </table>
      </div>
      <div id="payment-workflow-panel" role="region" aria-live="polite"></div>
    `;

    container.querySelectorAll('.btn-recover-order-access').forEach(b => b.addEventListener('click', async () => {
      const note = prompt('Describe how you independently verified this customer before issuing a new code:');
      if (note === null) return;
      if (note.trim().length < 10) { alert('Enter a verification note of at least 10 characters.'); return; }
      b.disabled = true;
      try {
        const result = await recoverAdminOrderAccess(b.getAttribute('data-order-id'), note.trim());
        prompt(`Private code for ${result.order_number}. Copy it now and convey it through the verified channel; it will not be shown again.`, result.access_code);
      } catch (error) { alert(error.message || 'Access recovery failed'); }
      finally { b.disabled = false; }
    }));
    container.querySelectorAll('.btn-revoke-order-access').forEach(b => b.addEventListener('click', async () => {
      if (!confirm('Revoke all customer codes and sessions for this order?')) return;
      b.disabled = true;
      try { await revokeAdminOrderAccess(b.getAttribute('data-order-id')); alert('Order access revoked. Issue a new code after verifying the customer.'); }
      catch (error) { alert(error.message || 'Access revocation failed'); }
      finally { b.disabled = false; }
    }));
    container.querySelectorAll('.btn-remit-order').forEach(b => b.addEventListener('click', async () => {
      const shipmentId = b.getAttribute('data-shipment-id');
      b.disabled = true;
      try {
        const shipment = await fetchAdminShipmentSettlement(shipmentId);
        currentRemitOutstandingMinor = shipment.settlement_outstanding_minor;
        modal.querySelector('#remit-shipment-id').value = shipmentId;
        modal.querySelector('#remit-summary').textContent = `Gross COD ${formatPkr(shipment.cod_amount_minor)} · Bank receipts ${formatPkr(shipment.cod_remitted_amount_minor)} · Deductions ${formatPkr(shipment.settlement_deductions_minor)} · Outstanding ${formatPkr(shipment.settlement_outstanding_minor)}`;
        modal.querySelector('#remit-history').textContent = shipment.settlement_entries.map(entry => `${entry.entry_type}: ${formatPkr(entry.amount_minor)} (${entry.reference})`).join(' | ') || 'No settlement entries yet.';
        modal.querySelector('#remit-error').style.display = 'none';
        modal.querySelector('#admin-remittance-modal').style.display = 'flex';
      } catch (error) { alert(error.message || 'Unable to load settlement'); }
      finally { b.disabled = false; }
    }));

    const purgeBtn = container.querySelector('#btn-review-expired-orders');
    if (purgeBtn) {
      purgeBtn.addEventListener('click', async () => {
        purgeBtn.disabled = true;
        try {
          await reviewExpiredOrders();
          await loadActiveTabData();
        } catch (err) {
          container.querySelector('#payment-workflow-panel').textContent = err.message || 'Failed to check expired transfers';
          purgeBtn.disabled = false;
        }
      });
    }

    const workflowPanel = container.querySelector('#payment-workflow-panel');
    container.querySelectorAll('.btn-prepare-instructions').forEach(button => {
      button.addEventListener('click', async () => {
        const orderId = button.getAttribute('data-order-id');
        button.disabled = true;
        workflowPanel.textContent = 'Loading payment instructions...';
        try {
          const preview = await fetchPaymentInstructionsPreview(orderId);
          workflowPanel.innerHTML = `
            <form id="instructions-sent-form" style="margin-top: 16px; padding: 16px; border: 1px solid rgba(255,255,255,.2);">
              <h3>Bank instructions for ${escapeHtml(preview.order_number)}</h3>
              <p>Amount: ${escapeHtml(formatPkr(preview.total_minor))}</p>
              <p>Bank: ${escapeHtml(preview.bank_name)}<br>Account title: ${escapeHtml(preview.account_title)}<br>Account number: ${escapeHtml(preview.account_number)}<br>IBAN: ${escapeHtml(preview.iban)}</p>
              <p>Send these details through your normal customer channel. Record the handoff only after it succeeds.</p>
              <label>Channel <select name="channel" required><option value="whatsapp">WhatsApp</option><option value="sms">SMS</option><option value="email">Email</option><option value="phone">Phone</option><option value="other">Other</option></select></label>
              <label>Delivery reference <input name="reference" required minlength="3" maxlength="200" placeholder="Message ID or call reference"></label>
              <label><input type="checkbox" name="confirmed_sent" required> I have sent these instructions successfully</label>
              <button type="submit" class="btn btn-primary">Record successful handoff</button>
              <p class="payment-workflow-feedback" role="status"></p>
            </form>`;
          workflowPanel.querySelector('form').addEventListener('submit', async event => {
            event.preventDefault();
            const form = event.currentTarget;
            const submit = form.querySelector('button[type="submit"]');
            submit.disabled = true;
            try {
              await markPaymentInstructionsSent(orderId, {
                channel: form.elements.channel.value,
                reference: form.elements.reference.value.trim(),
              });
              await loadActiveTabData();
            } catch (error) {
              form.querySelector('.payment-workflow-feedback').textContent = error.message || 'Unable to record handoff';
              submit.disabled = false;
            }
          });
        } catch (error) {
          workflowPanel.textContent = error.message || 'Unable to load payment instructions';
          button.disabled = false;
        }
      });
    });

    container.querySelectorAll('.btn-resolve-payment').forEach(button => {
      button.addEventListener('click', () => {
        const orderId = button.getAttribute('data-order-id');
        workflowPanel.innerHTML = `
          <form id="payment-review-form" style="margin-top: 16px; padding: 16px; border: 1px solid rgba(255,255,255,.2);">
            <h3>Review expired bank transfer</h3>
            <p>Check the bank account for received or pending funds before choosing a resolution. Stock stays reserved until this review is complete.</p>
            <label><input type="checkbox" name="funds_checked" required> I checked received and pending funds</label>
            <label>Resolution <select name="resolution" required><option value="payment_received">Payment received — verify and retain order</option><option value="release_unpaid">No payment — cancel and release stock</option></select></label>
            <label>Review note <textarea name="note" required minlength="5" maxlength="500"></textarea></label>
            <button type="submit" class="btn btn-primary">Save review decision</button>
            <p class="payment-workflow-feedback" role="status"></p>
          </form>`;
        workflowPanel.querySelector('form').addEventListener('submit', async event => {
          event.preventDefault();
          const form = event.currentTarget;
          const submit = form.querySelector('button[type="submit"]');
          submit.disabled = true;
          try {
            await resolvePaymentReview(orderId, {
              resolution: form.elements.resolution.value,
              note: form.elements.note.value.trim(),
            });
            await loadActiveTabData();
          } catch (error) {
            form.querySelector('.payment-workflow-feedback').textContent = error.message || 'Unable to resolve payment review';
            submit.disabled = false;
          }
        });
      });
    });

    container.querySelectorAll('.btn-verify-payment').forEach(b => {
      b.addEventListener('click', async () => {
        const orderId = b.getAttribute('data-order-id');
        b.disabled = true;
        try {
          await verifyOrderPayment(orderId);
          await loadActiveTabData();
        } catch (error) {
          if (error.status !== 401) showSessionMessage(error.message || 'Payment verification failed.');
          b.disabled = false;
        }
      });
    });

    container.querySelectorAll('.btn-confirm-supplier').forEach(b => {
      b.addEventListener('click', async () => {
        const orderId = b.getAttribute('data-order-id');
        const notes = prompt('Enter supplier / warehouse fulfillment notes (optional):');
        if (notes !== null) {
          b.disabled = true;
          try {
            await confirmSupplierAcceptance(orderId, notes);
            await loadActiveTabData();
          } catch (err) {
            alert(err.message || 'Failed to confirm supplier acceptance');
            b.disabled = false;
          }
        }
      });
    });

    container.querySelectorAll('.btn-reconcile-stock').forEach(b => b.addEventListener('click', async () => {
      b.disabled = true;
      try {
        const shipmentId = b.getAttribute('data-shipment-id');
        const preview = await previewLegacyShipmentStock(shipmentId);
        if (preview.shipment_count !== 1 || !preview.lines?.length) {
          throw new Error('Historical allocations are ambiguous. Review the data before reconciliation.');
        }
        const lines = [];
        for (const line of preview.lines) {
          const answer = prompt(`Reservation ${line.reservation_id}: ${line.quantity} units at supplier variant ${line.supplier_variant_id}. Was physical stock already deducted? Enter YES or NO:`, '');
          if (answer === null) return;
          const decision = answer.trim().toUpperCase();
          if (!['YES', 'NO'].includes(decision)) throw new Error('Enter YES or NO for each historical reservation.');
          const received = preview.status === 'rto_delivered'
            ? prompt(`Actual RTO units received for this reservation (0-${line.quantity}):`, '0') : null;
          if (preview.status === 'rto_delivered' && received === null) return;
          const receivedQuantity = received === null ? undefined : Number(received);
          if (received !== null && (!Number.isInteger(receivedQuantity) || receivedQuantity < 0 || receivedQuantity > line.quantity)) {
            throw new Error('Received quantity must be a whole number within the dispatched quantity.');
          }
          lines.push({ reservation_id: line.reservation_id, physical_deducted: decision === 'YES',
            ...(receivedQuantity === undefined ? {} : { received_quantity: receivedQuantity }) });
        }
        const note = prompt('Record how you verified these historical physical stock decisions (at least 5 characters):', '');
        if (note === null) return;
        if (note.trim().length < 5) throw new Error('A verification note of at least 5 characters is required.');
        await reconcileLegacyShipmentStock(shipmentId, { lines, note: note.trim() });
        await loadActiveTabData();
      } catch (error) { alert(error.message || 'Stock reconciliation failed'); }
      finally { b.disabled = false; }
    }));

    container.querySelectorAll('.btn-rto-order').forEach(b => {
      b.addEventListener('click', async () => {
        const orderId = b.getAttribute('data-order-id');
        const reason = prompt('Enter RTO reason (e.g. customer refused, unreachable, bad address):');
        if (reason !== null) {
          const costInput = prompt('Enter courier return shipping cost in PKR (optional, default 0):', '0');
          const costMinor = costInput ? pkrToMinor(parseFloat(costInput) || 0) : 0;
          b.disabled = true;
          try {
            await initiateOrderRto(orderId, { reason, rto_courier_cost_minor: costMinor });
            await loadActiveTabData();
          } catch (err) {
            alert(err.message || 'Failed to initiate RTO');
            b.disabled = false;
          }
        }
      });
    });

    container.querySelectorAll('.btn-rto-receive').forEach(b => {
      b.addEventListener('click', async () => {
        const orderId = b.getAttribute('data-order-id');
        const order = orders.find(item => item.id === orderId);
        const lines = [];
        for (const allocation of order.shipments?.[0]?.allocations || []) {
          const line = order.lines.find(item => item.id === allocation.order_line_id);
          const value = prompt(`Received quantity for ${line?.product_title || 'item'} (dispatched ${allocation.quantity}; 0 if missing):`, String(allocation.quantity));
          if (value === null) return;
          const quantity = Number(value);
          if (!Number.isInteger(quantity) || quantity < 0 || quantity > allocation.quantity) {
            alert('Enter a whole number within the dispatched quantity.');
            return;
          }
          lines.push({ order_line_id: allocation.order_line_id, received_quantity: quantity });
        }
        if (lines.length && confirm('Record these received units in quarantine for inspection?')) {
          b.disabled = true;
          try {
            await receiveOrderRto(orderId, lines);
            await loadActiveTabData();
          } catch (err) {
            alert(err.message || 'Failed to confirm RTO receipt');
            b.disabled = false;
          }
        }
      });
    });

    container.querySelectorAll('.btn-rto-inspect').forEach(b => {
      b.addEventListener('click', async () => {
        const orderId = b.getAttribute('data-order-id');
        const order = orders.find(item => item.id === orderId);
        const lines = [];
        for (const allocation of order.shipments?.[0]?.allocations || []) {
          const line = order.lines.find(item => item.id === allocation.order_line_id);
          const sellableInput = prompt(`Cumulative sellable quantity for ${line?.product_title || 'item'} (received ${allocation.received_quantity}):`, String(allocation.sellable_quantity));
          if (sellableInput === null) return;
          const damagedInput = prompt(`Cumulative damaged quantity for ${line?.product_title || 'item'}:`, String(allocation.damaged_quantity));
          if (damagedInput === null) return;
          const sellable = Number(sellableInput);
          const damaged = Number(damagedInput);
          if (![sellable, damaged].every(Number.isInteger) || sellable < allocation.sellable_quantity || damaged < allocation.damaged_quantity || sellable + damaged > allocation.received_quantity) {
            alert('Enter nondecreasing whole quantities within the received quantity.');
            return;
          }
          lines.push({ order_line_id: allocation.order_line_id, sellable_quantity: sellable, damaged_quantity: damaged });
        }
        const notes = prompt('Inspection notes (required for damaged units):', '');
        if (notes !== null) {
          b.disabled = true;
          try {
            await inspectAndRestockRtoOrder(orderId, { lines, notes });
            await loadActiveTabData();
          } catch (err) {
            alert(err.message || 'Failed to complete RTO inspection');
            b.disabled = false;
          }
        }
      });
    });

    container.querySelectorAll('.btn-cancel-order').forEach(b => {
      b.addEventListener('click', async () => {
        const orderId = b.getAttribute('data-order-id');
        if (confirm('Are you sure you want to cancel this order and release held stock?')) {
          b.disabled = true;
          try {
            await cancelOrder(orderId);
            await loadActiveTabData();
          } catch (err) {
            alert(err.message || 'Failed to cancel order');
            b.disabled = false;
          }
        }
      });
    });

    container.querySelectorAll('.btn-dispatch-order').forEach(b => {
      b.addEventListener('click', () => {
        const orderId = b.getAttribute('data-order-id');
        const modalEl = modal.querySelector('#admin-dispatch-modal');
        const idInput = modal.querySelector('#dispatch-order-id');
        if (modalEl && idInput) {
          idInput.value = orderId;
          modalEl.style.display = 'flex';
        }
      });
    });
  }

  // 3. Inventory Tab
  async function renderInventoryTab(container) {
    const res = await fetchAdminInventory();
    const items = res.items || [];

    const rowsHtml = items.map(it => `
      <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.06); font-size: 0.8125rem;">
        <td style="padding: 12px 8px; font-weight: 600;">${escapeHtml(it.product_title)}</td>
        <td style="padding: 12px 8px; font-family: monospace; color: rgba(255, 255, 255, 0.7);">${escapeHtml(it.sku)}</td>
        <td style="padding: 12px 8px;">${it.physical_on_hand}</td>
        <td style="padding: 12px 8px; color: #FBBF24;">${it.held_reservations}</td>
        <td style="padding: 12px 8px; font-weight: 700; color: ${it.available_to_sell <= 2 ? '#F87171' : '#4ADE80'};">${it.available_to_sell}</td>
      </tr>
    `).join('');

    container.innerHTML = `
      <div style="overflow-x: auto;">
        <table style="width: 100%; border-collapse: collapse; text-align: left;">
          <thead>
            <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.12); font-size: 0.75rem; color: rgba(255, 255, 255, 0.5); text-transform: uppercase;">
              <th style="padding: 8px;">Product</th>
              <th style="padding: 8px;">SKU</th>
              <th style="padding: 8px;">Physical Stock</th>
              <th style="padding: 8px;">Held Stock</th>
              <th style="padding: 8px;">Available</th>
            </tr>
          </thead>
          <tbody>${rowsHtml}</tbody>
        </table>
      </div>
    `;
  }

  // 4. Coupons Tab
  async function renderCouponsTab(container) {
    const coupons = await fetchAdminCoupons();

    const rowsHtml = coupons.map(c => `
      <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.06); font-size: 0.8125rem;">
        <td style="padding: 12px 8px; font-family: monospace; font-weight: 700; color: #4ADE80;">${escapeHtml(c.code)}</td>
        <td style="padding: 12px 8px; text-transform: capitalize;">${escapeHtml(c.discount_type)}</td>
        <td style="padding: 12px 8px;">
          ${c.discount_type === 'percentage' ? `${c.discount_value}%` : c.discount_type === 'fixed_amount' ? formatPkr(c.discount_value) : '100% Shipping'}
        </td>
        <td style="padding: 12px 8px;">${c.min_subtotal.formatted}</td>
        <td style="padding: 12px 8px;">${c.times_used} ${c.usage_limit ? `/ ${c.usage_limit}` : 'uses'}</td>
        <td style="padding: 12px 8px;">
          <span class="badge ${c.is_active ? 'badge-accent' : 'badge-neutral'}" style="font-size: 0.65rem;">
            ${c.is_active ? 'Active' : 'Inactive'}
          </span>
        </td>
        <td style="padding: 12px 8px; text-align: right;">
          <button class="btn btn-secondary btn-del-coupon" data-coupon-id="${c.id}" style="padding: 4px 8px; font-size: 0.7rem; color: #F87171; border-color: rgba(248, 113, 113, 0.3);">
            Delete
          </button>
        </td>
      </tr>
    `).join('');

    container.innerHTML = `
      <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 20px;">
        <div>
          <h3 style="font-size: 0.9375rem; font-weight: 700; margin-bottom: 12px;">Active Discount Vouchers</h3>
          <div style="overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse; text-align: left;">
              <thead>
                <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.12); font-size: 0.75rem; color: rgba(255, 255, 255, 0.5); text-transform: uppercase;">
                  <th style="padding: 8px;">Code</th>
                  <th style="padding: 8px;">Type</th>
                  <th style="padding: 8px;">Value</th>
                  <th style="padding: 8px;">Min Subtotal</th>
                  <th style="padding: 8px;">Usage</th>
                  <th style="padding: 8px;">Status</th>
                  <th style="padding: 8px; text-align: right;">Action</th>
                </tr>
              </thead>
              <tbody>${rowsHtml.length ? rowsHtml : '<tr><td colspan="7" style="padding: 20px 8px; text-align: center; color: rgba(255,255,255,0.4);">No coupons created yet.</td></tr>'}</tbody>
            </table>
          </div>
        </div>

        <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 16px;">
          <h3 style="font-size: 0.9375rem; font-weight: 700; margin-bottom: 12px;">+ Create New Coupon</h3>
          <form id="new-coupon-form" style="display: flex; flex-direction: column; gap: 10px;">
            <div>
              <label style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); display: block; margin-bottom: 2px;">Coupon Code *</label>
              <input type="text" id="cpn-code" required placeholder="e.g. FLASH20" style="width: 100%; padding: 8px 12px; background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 6px; font-size: 0.8125rem; text-transform: uppercase;" />
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
              <div>
                <label style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); display: block; margin-bottom: 2px;">Type *</label>
                <select id="cpn-type" style="width: 100%; padding: 8px 12px; background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 6px; font-size: 0.8125rem;">
                  <option value="percentage">Percentage (%)</option>
                  <option value="fixed_amount">Fixed Amount (PKR)</option>
                  <option value="free_shipping">Free Shipping</option>
                </select>
              </div>
              <div>
                <label style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); display: block; margin-bottom: 2px;">Value *</label>
                <input type="number" id="cpn-val" required min="0" value="10" style="width: 100%; padding: 8px 12px; background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 6px; font-size: 0.8125rem;" />
              </div>
            </div>
            <div>
              <label style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); display: block; margin-bottom: 2px;">Min Subtotal (PKR)</label>
              <input type="number" id="cpn-min-pkr" value="0" min="0" step="100" style="width: 100%; padding: 8px 12px; background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 6px; font-size: 0.8125rem;" />
            </div>
            <div>
              <label style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); display: block; margin-bottom: 2px;">Usage Limit (Optional)</label>
              <input type="number" id="cpn-limit" placeholder="Unlimited" min="1" style="width: 100%; padding: 8px 12px; background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 6px; font-size: 0.8125rem;" />
            </div>
            <div id="cpn-error" style="display: none; color: #F87171; font-size: 0.75rem; font-weight: 600;"></div>
            <button type="submit" id="btn-save-coupon" class="btn btn-primary" style="align-self: flex-start; padding: 6px 14px; font-size: 0.8125rem;">
              Create Coupon
            </button>
          </form>
        </div>
      </div>
    `;

    container.querySelectorAll('.btn-del-coupon').forEach(b => {
      b.addEventListener('click', async () => {
        const id = b.getAttribute('data-coupon-id');
        if (confirm('Delete this coupon code?')) {
          b.disabled = true;
          await deleteAdminCoupon(id);
          await loadActiveTabData();
        }
      });
    });

    const form = container.querySelector('#new-coupon-form');
    const cpnError = container.querySelector('#cpn-error');
    const saveBtn = container.querySelector('#btn-save-coupon');

    form?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const code = container.querySelector('#cpn-code').value.trim();
      const discountType = container.querySelector('#cpn-type').value;
      let val = parseInt(container.querySelector('#cpn-val').value, 10) || 0;
      if (discountType === 'fixed_amount') {
        val = pkrToMinor(val);
      }
      const minPkr = parseInt(container.querySelector('#cpn-min-pkr').value, 10) || 0;
      const limitRaw = container.querySelector('#cpn-limit').value.trim();
      const usageLimit = limitRaw ? parseInt(limitRaw, 10) : null;

      saveBtn.disabled = true;
      saveBtn.textContent = 'Creating...';
      cpnError.style.display = 'none';

      try {
        await createAdminCoupon({
          code,
          discount_type: discountType,
          discount_value: val,
          min_subtotal_minor: pkrToMinor(minPkr),
          usage_limit: usageLimit,
        });
        await loadActiveTabData();
      } catch (err) {
        saveBtn.disabled = false;
        saveBtn.textContent = 'Create Coupon';
        cpnError.textContent = err.message || 'Failed to create coupon.';
        cpnError.style.display = 'block';
      }
    });
  }

  // 5. Returns Tab
  async function renderReturnsTab(container) {
    const returns = await fetchAdminReturns();

    const rowsHtml = returns.map(r => `
      <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.06); font-size: 0.8125rem;">
        <td style="padding: 12px 8px; font-family: monospace; color: rgba(255, 255, 255, 0.7);">${escapeHtml(String(r.id).slice(0, 8))}</td>
        <td style="padding: 12px 8px; text-transform: capitalize;">${escapeHtml(r.return_type)}</td>
        <td style="padding: 12px 8px;">${escapeHtml(r.reason)}</td>
        <td style="padding: 12px 8px; color: rgba(255, 255, 255, 0.6);">${escapeHtml(r.customer_notes || '—')}</td>
        <td style="padding: 12px 8px; font-weight: 600;">${r.refund_amount.formatted}<div style="font-size: .7rem;">Paid: ${r.refund_paid.formatted} · Due: ${r.refund_outstanding.formatted}</div></td>
        <td style="padding: 12px 8px;">
          <span class="badge ${r.status === 'completed' ? 'badge-accent' : r.status === 'approved' ? 'badge-primary' : 'badge-neutral'}" style="font-size: 0.65rem; text-transform: capitalize;">
            ${escapeHtml(r.status)}
          </span>
          <div style="font-size: 0.7rem; color: rgba(255,255,255,.65);">Requested ${r.quantity ?? '?'} · received ${r.received_quantity} · sellable ${r.sellable_quantity} · damaged ${r.damaged_quantity}</div>
          ${r.inspection_state === 'legacy_review' ? '<div style="color: #FBBF24; font-size: .7rem;">Historical return needs reconciliation</div>' : ''}
        </td>
        <td style="padding: 12px 8px; text-align: right;">
          ${r.status === 'requested' ? `
            <button class="btn btn-primary btn-approve-ret" data-ret-id="${r.id}" style="padding: 4px 8px; font-size: 0.7rem; margin-right: 4px;">Approve</button>
            <button class="btn btn-secondary btn-reject-ret" data-ret-id="${r.id}" style="padding: 4px 8px; font-size: 0.7rem; color: #F87171;">Reject</button>
          ` : ''}
          ${['approved', 'item_received', 'inspected_passed'].includes(r.status) ? `
            ${r.status === 'approved' && r.inspection_state !== 'legacy_review' && r.received_quantity === 0 ? `<button class="btn btn-secondary btn-receive-ret" data-ret-id="${r.id}" style="padding: 4px 8px; font-size: .7rem;">Record Receipt</button>` : ''}
            ${r.inspection_state !== 'legacy_review' && r.received_quantity > r.sellable_quantity + r.damaged_quantity ? `<button class="btn btn-secondary btn-inspect-ret" data-ret-id="${r.id}" style="padding: 4px 8px; font-size: .7rem;">Inspect Units</button>` : ''}
            ${r.received_quantity > 0 && r.sellable_quantity + r.damaged_quantity === r.received_quantity ? `<button class="btn btn-primary btn-complete-ret" data-ret-id="${r.id}" style="padding: 4px 8px; font-size: 0.7rem;">Complete Return</button>` : ''}
          ` : ''}
          ${r.return_type === 'size_exchange' && ['inspected_passed', 'completed'].includes(r.status) && r.received_quantity === r.quantity && !r.replacement_shipment_id ? `<button class="btn btn-primary btn-dispatch-replacement" data-ret-id="${r.id}" style="padding: 4px 8px; font-size: .7rem;">Dispatch Replacement</button>` : ''}
          ${r.return_type === 'refund_bank_transfer' && r.status === 'completed' && r.refund_outstanding.minor > 0 ? `<button class="btn btn-primary btn-record-refund" data-ret-id="${r.id}" style="padding: 4px 8px; font-size: .7rem;">Record Paid Refund</button>` : ''}
          ${r.replacement_shipment_id ? `<div style="font-size: .7rem;">Replacement: ${escapeHtml(r.replacement_shipment_status)}</div>
            ${['dispatched', 'in_transit', 'out_for_delivery'].includes(r.replacement_shipment_status) ? `<button class="btn btn-secondary btn-replacement-status" data-ret-id="${r.id}" data-next="delivered">Mark Delivered</button><button class="btn btn-secondary btn-replacement-status" data-ret-id="${r.id}" data-next="rto_initiated">Start RTO</button>` : ''}
            ${r.replacement_shipment_status === 'rto_initiated' ? `<button class="btn btn-secondary btn-replacement-status" data-ret-id="${r.id}" data-next="rto_delivered">Receive RTO</button>` : ''}
            ${r.replacement_shipment_status === 'rto_delivered' ? `<button class="btn btn-secondary btn-inspect-replacement-rto" data-ret-id="${r.id}">Inspect RTO</button>` : ''}` : ''}
        </td>
      </tr>
    `).join('');

    container.innerHTML = `
      <div>
        <h3 style="font-size: 0.9375rem; font-weight: 700; margin-bottom: 12px;">Customer Return & Size Exchange Inquiries</h3>
        <div style="overflow-x: auto;">
          <table style="width: 100%; border-collapse: collapse; text-align: left;">
            <thead>
              <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.12); font-size: 0.75rem; color: rgba(255, 255, 255, 0.5); text-transform: uppercase;">
                <th style="padding: 8px;">Return ID</th>
                <th style="padding: 8px;">Type</th>
                <th style="padding: 8px;">Reason</th>
                <th style="padding: 8px;">Customer Explanation</th>
                <th style="padding: 8px;">Refund Eligible</th>
                <th style="padding: 8px;">Status</th>
                <th style="padding: 8px; text-align: right;">Actions</th>
              </tr>
            </thead>
            <tbody>${rowsHtml.length ? rowsHtml : '<tr><td colspan="7" style="padding: 20px 8px; text-align: center; color: rgba(255,255,255,0.4);">No return requests filed.</td></tr>'}</tbody>
          </table>
        </div>
      </div>
    `;

    container.querySelectorAll('.btn-approve-ret').forEach(b => {
      b.addEventListener('click', async () => {
        const id = b.getAttribute('data-ret-id');
        const ret = returns.find(item => item.id === id);
        const payload = {};
        if (ret?.return_type === 'size_exchange') {
          const charge = prompt('Additional replacement charge in PKR (default 0; original COD is never charged again):', '0');
          if (charge === null) return;
          const amount = Number(charge);
          if (!Number.isFinite(amount) || amount < 0 || !Number.isSafeInteger(Math.round(amount * 100))
              || Math.round(amount * 100) > 2147483647) {
            alert('Enter a non-negative amount in PKR.');
            return;
          }
          payload.replacement_charge_minor = Math.round(amount * 100);
        }
        b.disabled = true;
        try { await approveAdminReturn(id, payload); await loadActiveTabData(); }
        catch (error) { alert(error.message || 'Failed to approve return'); b.disabled = false; }
      });
    });

    container.querySelectorAll('.btn-reject-ret').forEach(b => {
      b.addEventListener('click', async () => {
        const id = b.getAttribute('data-ret-id');
        b.disabled = true;
        try { await rejectAdminReturn(id); await loadActiveTabData(); }
        catch (error) { alert(error.message || 'Failed to reject return'); b.disabled = false; }
      });
    });

    container.querySelectorAll('.btn-dispatch-replacement').forEach(b => b.addEventListener('click', async () => {
      const courier = prompt('Courier code (manual, trax, leopards, tcs, mnp, postex, call_courier):', 'manual');
      if (courier === null) return;
      const tracking = prompt('Replacement tracking number:');
      if (!tracking) return;
      b.disabled = true;
      try {
        await dispatchAdminReplacement(b.getAttribute('data-ret-id'), { courier_code: courier, tracking_number: tracking });
        await loadActiveTabData();
      } catch (error) { alert(error.message || 'Replacement dispatch failed'); b.disabled = false; }
    }));
    container.querySelectorAll('.btn-replacement-status').forEach(b => b.addEventListener('click', async () => {
      const ret = returns.find(item => item.id === b.getAttribute('data-ret-id'));
      const next = b.getAttribute('data-next');
      const payload = { status: next };
      if (next === 'rto_delivered') {
        const value = prompt(`Received replacement units (0-${ret.quantity}):`, String(ret.quantity));
        if (value === null) return;
        const quantity = Number(value);
        if (!Number.isInteger(quantity) || quantity < 0 || quantity > ret.quantity) return;
        payload.received_lines = [{ order_line_id: ret.replacement_line_id, received_quantity: quantity }];
      }
      b.disabled = true;
      try { await updateAdminShipmentStatus(ret.replacement_shipment_id, payload); await loadActiveTabData(); }
      catch (error) { alert(error.message || 'Replacement status update failed'); b.disabled = false; }
    }));
    container.querySelectorAll('.btn-inspect-replacement-rto').forEach(b => b.addEventListener('click', async () => {
      const ret = returns.find(item => item.id === b.getAttribute('data-ret-id'));
      const value = prompt('Sellable replacement units received:', '0');
      if (value === null) return;
      const sellable = Number(value);
      const damagedValue = prompt('Damaged replacement units:', '0');
      if (damagedValue === null) return;
      const damaged = Number(damagedValue);
      if (![sellable, damaged].every(Number.isInteger) || sellable < 0 || damaged < 0) return;
      const notes = prompt('Inspection findings (required if damaged):', '');
      if (notes === null) return;
      b.disabled = true;
      try {
        await inspectAdminShipmentRto(ret.replacement_shipment_id, {
          lines: [{ order_line_id: ret.replacement_line_id, sellable_quantity: sellable, damaged_quantity: damaged }], notes,
        });
        await loadActiveTabData();
      } catch (error) { alert(error.message || 'Replacement inspection failed'); b.disabled = false; }
    }));

    container.querySelectorAll('.btn-complete-ret').forEach(b => {
      b.addEventListener('click', async () => {
        const id = b.getAttribute('data-ret-id');
        if (confirm('Complete the inspected return? A refund is recorded separately only after money has actually been sent.')) {
          b.disabled = true;
          try {
            await completeAdminReturn(id, { should_restock: true });
            await loadActiveTabData();
          } catch (error) { alert(error.message || 'Failed to complete return'); b.disabled = false; }
        }
      });
    });
    container.querySelectorAll('.btn-record-refund').forEach(b => b.addEventListener('click', async () => {
      const ret = returns.find(item => item.id === b.getAttribute('data-ret-id'));
      const amountValue = prompt(`Actual refund sent (PKR; remaining ${formatPkr(ret.refund_outstanding.minor)}):`,
        String(ret.refund_outstanding.minor / 100));
      if (amountValue === null) return;
      const amount = Number(amountValue);
      const amountMinor = pkrToMinor(amount);
      if (!Number.isFinite(amount) || amountMinor <= 0 || amountMinor > ret.refund_outstanding.minor) {
        alert('Enter a positive refund within the remaining approved amount.'); return;
      }
      const reference = prompt('Bank transfer or cash payment reference:');
      if (reference === null) return;
      if (reference.trim().length < 3) { alert('Enter a payment reference.'); return; }
      b.disabled = true;
      try {
        await recordAdminRefundExecution(ret.id, { amount_minor: amountMinor,
          reference: reference.trim(), channel: 'bank_transfer' });
        await loadActiveTabData();
      } catch (error) { alert(error.message || 'Unable to record paid refund'); b.disabled = false; }
    }));

    container.querySelectorAll('.btn-receive-ret').forEach(b => b.addEventListener('click', async () => {
      const ret = returns.find(item => item.id === b.getAttribute('data-ret-id'));
      const value = prompt(`Cumulative received quantity (requested ${ret.quantity}):`, String(ret.quantity));
      if (value === null) return;
      const quantity = Number(value);
      if (!Number.isInteger(quantity) || quantity < ret.received_quantity || quantity > ret.quantity) {
        alert('Enter a whole quantity between the previous receipt and requested quantity.');
        return;
      }
      b.disabled = true;
      try { await receiveAdminReturn(ret.id, quantity); await loadActiveTabData(); }
      catch (error) { alert(error.message || 'Failed to record receipt'); b.disabled = false; }
    }));

    container.querySelectorAll('.btn-inspect-ret').forEach(b => b.addEventListener('click', async () => {
      const ret = returns.find(item => item.id === b.getAttribute('data-ret-id'));
      const sellableInput = prompt(`Cumulative sellable quantity (received ${ret.received_quantity}):`, String(ret.sellable_quantity));
      if (sellableInput === null) return;
      const damagedInput = prompt('Cumulative damaged quantity:', String(ret.damaged_quantity));
      if (damagedInput === null) return;
      const sellable = Number(sellableInput);
      const damaged = Number(damagedInput);
      if (![sellable, damaged].every(Number.isInteger) || sellable < ret.sellable_quantity || damaged < ret.damaged_quantity || sellable + damaged > ret.received_quantity) {
        alert('Enter nondecreasing whole quantities within the received quantity.');
        return;
      }
      const notes = prompt('Inspection findings:', '');
      if (notes === null) return;
      b.disabled = true;
      try {
        await inspectAdminReturn(ret.id, { sellable_quantity: sellable, damaged_quantity: damaged, notes });
        await loadActiveTabData();
      } catch (error) { alert(error.message || 'Failed to record inspection'); b.disabled = false; }
    }));
  }

  // 6. Suppliers Tab
  async function renderSuppliersTab(container) {
    const res = await fetchAdminSuppliers();
    const suppliers = res.suppliers || [];

    const rowsHtml = suppliers.map(s => `
      <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.06); font-size: 0.8125rem;">
        <td style="padding: 12px 8px; font-weight: 700; color: #FFFFFF;">${escapeHtml(s.name)}</td>
        <td style="padding: 12px 8px; font-family: monospace; color: rgba(255, 255, 255, 0.7);">${escapeHtml(s.slug)}</td>
        <td style="padding: 12px 8px;">
          <span class="badge ${s.status === 'active' ? 'badge-accent' : 'badge-neutral'}" style="font-size: 0.65rem;">
            ${escapeHtml(s.status)}
          </span>
        </td>
        <td style="padding: 12px 8px; color: rgba(255, 255, 255, 0.6);">${escapeHtml(s.notes || '—')}</td>
      </tr>
    `).join('');

    container.innerHTML = `
      <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 20px;">
        <div>
          <h3 style="font-size: 0.9375rem; font-weight: 700; margin-bottom: 12px;">Active Local Suppliers</h3>
          <div style="overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse; text-align: left;">
              <thead>
                <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.12); font-size: 0.75rem; color: rgba(255, 255, 255, 0.5); text-transform: uppercase;">
                  <th style="padding: 8px;">Supplier Name</th>
                  <th style="padding: 8px;">Identifier Slug</th>
                  <th style="padding: 8px;">Status</th>
                  <th style="padding: 8px;">Terms / Notes</th>
                </tr>
              </thead>
              <tbody>${rowsHtml.length ? rowsHtml : '<tr><td colspan="4" style="padding: 20px 8px; text-align: center; color: rgba(255,255,255,0.4);">No suppliers registered yet.</td></tr>'}</tbody>
            </table>
          </div>
        </div>

        <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 16px;">
          <h3 style="font-size: 0.9375rem; font-weight: 700; margin-bottom: 12px;">+ Register Supplier</h3>
          <form id="new-supplier-form" style="display: flex; flex-direction: column; gap: 10px;">
            <div>
              <label style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); display: block; margin-bottom: 2px;">Supplier Name *</label>
              <input type="text" id="sup-name" required placeholder="Karachi Apparel Works" style="width: 100%; padding: 8px 12px; background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 6px; font-size: 0.8125rem;" />
            </div>
            <div>
              <label style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); display: block; margin-bottom: 2px;">Slug *</label>
              <input type="text" id="sup-slug" required placeholder="karachi-apparel" style="width: 100%; padding: 8px 12px; background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 6px; font-size: 0.8125rem;" />
            </div>
            <div>
              <label style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); display: block; margin-bottom: 2px;">Notes / Settlement Terms</label>
              <textarea id="sup-notes" rows="2" placeholder="e.g. Prepay per order; WhatsApp 0300-1111111" style="width: 100%; padding: 8px 12px; background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 6px; font-size: 0.8125rem; resize: vertical;"></textarea>
            </div>
            <div id="sup-error" style="display: none; color: #F87171; font-size: 0.75rem; font-weight: 600;"></div>
            <button type="submit" id="btn-save-supplier" class="btn btn-primary" style="align-self: flex-start; padding: 6px 14px; font-size: 0.8125rem;">
              Register Supplier
            </button>
          </form>
        </div>
      </div>
    `;

    const form = container.querySelector('#new-supplier-form');
    const supError = container.querySelector('#sup-error');
    const saveBtn = container.querySelector('#btn-save-supplier');

    form?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const name = container.querySelector('#sup-name').value.trim();
      const slug = container.querySelector('#sup-slug').value.trim();
      const notes = container.querySelector('#sup-notes').value.trim() || null;

      saveBtn.disabled = true;
      saveBtn.textContent = 'Registering...';
      supError.style.display = 'none';

      try {
        await createAdminSupplier({ name, slug, status: 'active', notes });
        await loadActiveTabData();
      } catch (err) {
        saveBtn.disabled = false;
        saveBtn.textContent = 'Register Supplier';
        supError.textContent = err.message || 'Failed to create supplier.';
        supError.style.display = 'block';
      }
    });
  }

  // 7. Analytics & Marketing Tab
  async function renderAnalyticsTab(container) {
    const [data, marketing] = await Promise.all([
      fetchAdminProfitLoss(),
      fetchAdminMarketingAnalytics(),
    ]);

    const mktRows = (marketing.channels || []).map(c => `
      <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.06); font-size: 0.8125rem;">
        <td style="padding: 10px 8px; font-weight: 700; color: #38BDF8;">${escapeHtml(c.utm_source)}</td>
        <td style="padding: 10px 8px;">${escapeHtml(c.utm_medium)}</td>
        <td style="padding: 10px 8px;">${escapeHtml(c.utm_campaign)}</td>
        <td style="padding: 10px 8px; font-weight: 600;">${c.orders_count}</td>
        <td style="padding: 10px 8px; font-weight: 700; color: #4ADE80;">${c.formatted_revenue}</td>
        <td style="padding: 10px 8px; color: #F59E0B;">${c.formatted_discount}</td>
      </tr>
    `).join('');

    container.innerHTML = `
      <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 20px;">
        
        <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 16px;">
          <div style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.5); text-transform: uppercase; font-weight: 600; margin-bottom: 4px;">Delivered Sales</div>
          <div style="font-size: 1.5rem; font-weight: 800; color: #4ADE80;">${escapeHtml(data.formatted_gross_revenue)}</div>
          <div style="font-size: 0.7rem; color: rgba(255, 255, 255, 0.4); margin-top: 4px;">Undelivered and unpaid orders excluded</div>
        </div>

        <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 16px;">
          <div style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.5); text-transform: uppercase; font-weight: 600; margin-bottom: 4px;">Wholesale COGS</div>
          <div style="font-size: 1.5rem; font-weight: 800; color: #F59E0B;">${escapeHtml(data.formatted_cogs)}</div>
          <div style="font-size: 0.7rem; color: rgba(255, 255, 255, 0.4); margin-top: 4px;">Supplier product cost snapshot</div>
        </div>

        <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 16px;">
          <div style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.5); text-transform: uppercase; font-weight: 600; margin-bottom: 4px;">Estimated Contribution</div>
          <div style="font-size: 1.5rem; font-weight: 800; color: #38BDF8;">${escapeHtml(data.formatted_gross_profit)}</div>
          <div style="font-size: 0.7rem; color: #38BDF8; font-weight: 700; margin-top: 4px;">${data.gross_margin_percent}% after recorded product/courier costs; excludes other overhead</div>
        </div>

      </div>

      <div style="background: rgba(255,255,255,.03); border: 1px solid rgba(255,255,255,.08); padding: 16px; margin-bottom: 20px;">
        <h4 style="font-size: .8125rem; margin: 0 0 10px;">Sales and cash reconciliation · all-time PKR</h4>
        <div style="display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 7px; font-size: .8rem;">
          <div>Order value: ${formatPkr(data.order_value_minor)}</div>
          <div>Delivered sales: ${formatPkr(data.delivered_sales_minor)}</div>
          <div>Bank payments verified: ${formatPkr(data.bank_customer_payments_minor)}</div>
          <div>COD collected by couriers: ${formatPkr(data.cod_collected_minor)}</div>
          <div>COD receipts cleared in bank: ${formatPkr(data.cod_remitted_minor)}</div>
          <div>Documented courier deductions: ${formatPkr(data.courier_deductions_minor)}</div>
          <div>COD outstanding with couriers: ${formatPkr(data.courier_held_cod_minor)}</div>
          <div>Refunds approved/completed: ${formatPkr(data.sales_reversals_minor)}</div>
          <div>Refunds actually paid: ${formatPkr(data.refund_paid_minor)}</div>
          <div>Refunds still payable: ${formatPkr(data.refund_outstanding_minor)}</div>
          <div>Business cash after refunds: ${formatPkr(data.business_cash_received_minor)}</div>
          <div>Sellable return COGS reversal: ${formatPkr(data.cogs_reversals_minor)}</div>
          <div>Other evidenced deductions: ${formatPkr(data.other_deductions_minor)}</div>
        </div>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px;">
        
        <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 16px;">
          <h4 style="font-size: 0.8125rem; font-weight: 700; color: #FFFFFF; margin: 0 0 10px 0;">Courier Costs & RTO Analytics</h4>
          <div style="display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.06); font-size: 0.8125rem;">
            <span style="color: rgba(255, 255, 255, 0.7);">Total Courier Expenses:</span>
            <strong style="color: #F87171;">${escapeHtml(data.formatted_courier_expenses)}</strong>
          </div>
          <div style="display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.06); font-size: 0.8125rem;">
            <span style="color: rgba(255, 255, 255, 0.7);">Outbound Delivery Fees:</span>
            <span>${formatPkr(data.outbound_courier_cost_minor)}</span>
          </div>
          <div style="display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.06); font-size: 0.8125rem;">
            <span style="color: rgba(255, 255, 255, 0.7);">RTO Return Penalties:</span>
            <span style="color: #F87171;">${formatPkr(data.rto_courier_cost_minor)}</span>
          </div>
          <div style="display: flex; justify-content: space-between; padding: 6px 0; font-size: 0.8125rem;">
            <span style="color: rgba(255, 255, 255, 0.7);">Return-to-Origin (RTO) Rate:</span>
            <strong style="color: ${data.rto_rate_percent > 20 ? '#F87171' : '#4ADE80'};">${data.rto_rate_percent}% (${data.rto_shipments_count} / ${data.total_shipments_count} parcels)</strong>
          </div>
        </div>

        <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 16px;">
          <h4 style="font-size: 0.8125rem; font-weight: 700; color: #FFFFFF; margin: 0 0 10px 0;">COD Cash Remittance Tracking</h4>
          <div style="display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.06); font-size: 0.8125rem;">
            <span style="color: rgba(255, 255, 255, 0.7);">Pending Courier Remittance:</span>
            <strong style="color: #F59E0B;">${formatPkr(data.cod_pending_remittance_minor)}</strong>
          </div>
          <div style="display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.06); font-size: 0.8125rem;">
            <span style="color: rgba(255, 255, 255, 0.7);">Cleared in Bank Account:</span>
            <strong style="color: #4ADE80;">${formatPkr(data.cod_remitted_minor)}</strong>
          </div>
          <p style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.5); margin: 12px 0 0 0;">
            COD cash collected by couriers is remitted on weekly payout cycles. Track clearing references on each order.
          </p>
        </div>

      </div>

      <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 16px;">
        <h4 style="font-size: 0.8125rem; font-weight: 700; color: #FFFFFF; margin: 0 0 10px 0;">Marketing Attribution & Campaign Conversion (UTM)</h4>
        <div style="overflow-x: auto;">
          <table style="width: 100%; border-collapse: collapse; text-align: left;">
            <thead>
              <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.12); font-size: 0.75rem; color: rgba(255, 255, 255, 0.5); text-transform: uppercase;">
                <th style="padding: 8px;">Source</th>
                <th style="padding: 8px;">Medium</th>
                <th style="padding: 8px;">Campaign</th>
                <th style="padding: 8px;">Orders</th>
                <th style="padding: 8px;">Revenue</th>
                <th style="padding: 8px;">Discounts Given</th>
              </tr>
            </thead>
            <tbody>${mktRows.length ? mktRows : '<tr><td colspan="6" style="padding: 20px 8px; text-align: center; color: rgba(255,255,255,0.4);">No attribution data recorded yet.</td></tr>'}</tbody>
          </table>
        </div>
      </div>
    `;
  }

  async function open() {
    overlay.open();
    const generation = ++authGeneration;
    contentArea.innerHTML = '<p role="status">Checking owner session...</p>';
    try {
      await fetchOwnerSession();
      if (generation !== authGeneration) return;
      authenticated = true;
      modal.querySelector('#btn-admin-logout').hidden = false;
      showSessionMessage('');
      await loadActiveTabData();
    } catch (error) {
      authenticated = false;
      renderLogin(error.status === 401 ? '' : 'Unable to reach the store. You can try signing in again.');
    }
  }

  function close() {
    overlay.close();
  }

  // Dispatch remains in Phase L2; settlement is handled below.
  for (const [formId, cancelId, dialogId] of [
    ['admin-dispatch-form', 'btn-cancel-dispatch', 'admin-dispatch-modal'],
  ]) {
    modal.querySelector(`#${formId}`).addEventListener('submit', event => event.preventDefault());
    modal.querySelector(`#${cancelId}`).addEventListener('click', () => {
      modal.querySelector(`#${dialogId}`).style.display = 'none';
    });
  }
  modal.querySelector('#btn-cancel-remit').addEventListener('click', () => {
    modal.querySelector('#admin-remittance-modal').style.display = 'none';
  });
  modal.querySelector('#admin-remittance-form').addEventListener('submit', async event => {
    event.preventDefault();
    const form = event.currentTarget;
    const submit = form.querySelector('#btn-submit-remit');
    const error = form.querySelector('#remit-error');
    const amount = Number(form.querySelector('#remit-amount-pkr').value);
    const deductionType = form.querySelector('#remit-deduction-type').value;
    const deductionAmount = Number(form.querySelector('#remit-deduction-pkr').value || 0);
    const cashMinor = pkrToMinor(amount);
    const deductionMinor = pkrToMinor(deductionAmount);
    const cashRef = form.querySelector('#remit-ref').value.trim();
    const deductionRef = form.querySelector('#remit-deduction-ref').value.trim();
    const deductionNote = form.querySelector('#remit-deduction-note').value.trim();
    const invalid = ![amount, deductionAmount].every(Number.isFinite) || amount < 0 || deductionAmount < 0
      || !Number.isSafeInteger(cashMinor) || !Number.isSafeInteger(deductionMinor)
      || cashMinor + deductionMinor <= 0 || cashMinor + deductionMinor > currentRemitOutstandingMinor
      || (cashMinor > 0 && cashRef.length < 3)
      || (deductionType ? deductionMinor <= 0 || deductionRef.length < 3 || deductionNote.length < 5 : deductionMinor > 0);
    if (invalid) {
      error.textContent = 'Enter a valid cash receipt and/or evidenced deduction within the outstanding COD amount.';
      error.style.display = 'block';
      return;
    }
    const deductions = deductionType ? [{ entry_type: deductionType,
      amount_minor: deductionMinor, reference: deductionRef, note: deductionNote }] : [];
    error.style.display = 'none';
    submit.disabled = true;
    submit.textContent = 'Recording...';
    try {
      await recordAdminCodRemittance(form.querySelector('#remit-shipment-id').value, {
        remitted_amount_minor: cashMinor, reference: cashMinor ? cashRef : null,
        deductions, final_statement: form.querySelector('#remit-final-statement').checked,
      });
      form.reset();
      modal.querySelector('#admin-remittance-modal').style.display = 'none';
      await loadActiveTabData();
    } catch (requestError) {
      error.textContent = requestError.message || 'Unable to record settlement.';
      error.style.display = 'block';
    } finally {
      submit.disabled = false;
      submit.textContent = 'Record settlement';
    }
  });

  const overlay = createOverlay({ element: modal, onClose: () => {
    modal.querySelector('#admin-dispatch-modal').style.display = 'none';
    modal.querySelector('#admin-remittance-modal').style.display = 'none';
  } });

  modal.querySelector('.drawer-backdrop').addEventListener('click', close);
  modal.querySelector('#admin-close-btn').addEventListener('click', close);

  return {
    element: modal,
    open,
    close,
  };
}
