import { createOverlay } from '../utils/overlay.js';
import { createBrandLogo } from './BrandLogo.js';
import {
  fetchAdminOverview,
  fetchAdminInventory,
  adjustAdminInventory,
  fetchAdminOrders,
  verifyOrderPayment,
  confirmSupplierAcceptance,
  cancelExpiredOrders,
  deliverOrder,
  cancelOrder,
  initiateOrderRto,
  receiveOrderRto,
  inspectAndRestockRtoOrder,
  dispatchAdminOrder,
  updateAdminShipmentStatus,
  recordAdminCodRemittance,
  fetchAdminSuppliers,
  createAdminSupplier,
  assignSupplierVariant,
  fetchAdminProfitLoss,
  fetchAdminCoupons,
  createAdminCoupon,
  deleteAdminCoupon,
  fetchAdminReturns,
  approveAdminReturn,
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
          <div>
            <label style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); display: block; margin-bottom: 2px;">Remitted Amount Cleared in Bank (PKR) *</label>
            <input type="number" id="remit-amount-pkr" required min="1" step="1" style="width: 100%; padding: 8px 12px; background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 6px; font-size: 0.8125rem;" />
          </div>
          <div>
            <label style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); display: block; margin-bottom: 2px;">Courier Payout Reference / Bank Advice</label>
            <input type="text" id="remit-ref" placeholder="e.g. TRAX-WEEKLY-PAYOUT-OCT" style="width: 100%; padding: 8px 12px; background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 6px; font-size: 0.8125rem;" />
          </div>
          <div id="remit-error" style="display: none; color: #F87171; font-size: 0.75rem; font-weight: 600;"></div>
          <div style="display: flex; gap: 8px; justify-content: flex-end; margin-top: 10px;">
            <button type="button" id="btn-cancel-remit" class="btn btn-secondary" style="padding: 6px 12px; font-size: 0.8125rem;">Cancel</button>
            <button type="submit" id="btn-submit-remit" disabled class="btn btn-primary" style="padding: 6px 14px; font-size: 0.8125rem;">Remittance entry unavailable</button>
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
      const hasShipment = o.shipments && o.shipments.length > 0;
      const shipment = hasShipment ? o.shipments[0] : null;

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
          </td>
          <td style="padding: 12px 8px; text-align: right;">
            ${!isPaid && isBank && !isCancelled ? `
              <button class="btn btn-primary btn-verify-payment" data-order-id="${o.id}" style="padding: 4px 8px; font-size: 0.7rem; margin-right: 4px;">
                Verify Bank Transfer
              </button>
            ` : ''}
            ${o.order_status === 'placed' && !isCancelled ? `
              <button class="btn btn-secondary btn-confirm-supplier" data-order-id="${o.id}" style="padding: 4px 8px; font-size: 0.7rem; margin-right: 4px; border-color: rgba(74, 222, 128, 0.4); color: #4ADE80;">
                Confirm Supplier
              </button>
            ` : ''}
            ${o.order_status === 'confirmed' && !hasShipment && !isCancelled ? `
              <button class="btn btn-secondary btn-dispatch-order" data-order-id="${o.id}" style="padding: 4px 8px; font-size: 0.7rem; margin-right: 4px;">
                Dispatch Courier
              </button>
            ` : ''}
            ${o.order_status === 'dispatched' ? `
              <button class="btn btn-secondary btn-rto-order" data-order-id="${o.id}" style="padding: 4px 8px; font-size: 0.7rem; margin-right: 4px; color: #FBBF24; border-color: rgba(251, 191, 36, 0.4);">
                Initiate RTO
              </button>
            ` : ''}
            ${o.order_status === 'rto' && (!shipment || shipment.status === 'rto_initiated') ? `
              <button class="btn btn-primary btn-rto-receive" data-order-id="${o.id}" style="padding: 4px 8px; font-size: 0.7rem; margin-right: 4px; background: #E11D48; border-color: #E11D48;">
                Confirm RTO Received
              </button>
            ` : ''}
            ${o.order_status === 'rto' && shipment && shipment.status === 'rto_delivered' && !shipment.rto_restocked_at ? `
              <button class="btn btn-secondary btn-rto-inspect" data-order-id="${o.id}" style="padding: 4px 8px; font-size: 0.7rem; margin-right: 4px; color: #38BDF8; border-color: rgba(56, 189, 248, 0.4);">
                Inspect & Restock
              </button>
            ` : ''}
            ${!isCancelled && !isDelivered && o.order_status !== 'dispatched' && o.order_status !== 'rto' ? `
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
        <button id="btn-purge-expired-orders" class="btn btn-secondary" style="font-size: 0.75rem; padding: 4px 10px;">
          🧹 Cancel Expired Bank Orders (>4h)
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
    `;

    const purgeBtn = container.querySelector('#btn-purge-expired-orders');
    if (purgeBtn) {
      purgeBtn.addEventListener('click', async () => {
        purgeBtn.disabled = true;
        try {
          const res = await cancelExpiredOrders();
          alert(`Cancelled ${res.cancelled_count || 0} expired unpaid bank orders.`);
          await loadActiveTabData();
        } catch (err) {
          alert(err.message || 'Failed to cancel expired orders');
          purgeBtn.disabled = false;
        }
      });
    }

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
        if (confirm('Confirm parcel has arrived back at store?')) {
          b.disabled = true;
          try {
            await receiveOrderRto(orderId);
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
        const pass = confirm('Did the returned parcel pass physical condition inspection? Click OK if in resalable condition (restocks inventory), or Cancel if damaged/soiled.');
        const notes = prompt('Enter inspection notes (optional):', pass ? 'Physical condition verified pristine' : 'Item damaged during courier transit');
        if (notes !== null) {
          b.disabled = true;
          try {
            await inspectAndRestockRtoOrder(orderId, { condition_ok: pass, notes });
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
        <td style="padding: 12px 8px; font-weight: 600;">${r.refund_amount.formatted}</td>
        <td style="padding: 12px 8px;">
          <span class="badge ${r.status === 'completed' ? 'badge-accent' : r.status === 'approved' ? 'badge-primary' : 'badge-neutral'}" style="font-size: 0.65rem; text-transform: capitalize;">
            ${escapeHtml(r.status)}
          </span>
        </td>
        <td style="padding: 12px 8px; text-align: right;">
          ${r.status === 'requested' ? `
            <button class="btn btn-primary btn-approve-ret" data-ret-id="${r.id}" style="padding: 4px 8px; font-size: 0.7rem; margin-right: 4px;">Approve</button>
            <button class="btn btn-secondary btn-reject-ret" data-ret-id="${r.id}" style="padding: 4px 8px; font-size: 0.7rem; color: #F87171;">Reject</button>
          ` : ''}
          ${r.status === 'approved' ? `
            <button class="btn btn-primary btn-complete-ret" data-ret-id="${r.id}" style="padding: 4px 8px; font-size: 0.7rem;">Complete & Restock</button>
          ` : ''}
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
        b.disabled = true;
        await approveAdminReturn(id);
        await loadActiveTabData();
      });
    });

    container.querySelectorAll('.btn-reject-ret').forEach(b => {
      b.addEventListener('click', async () => {
        const id = b.getAttribute('data-ret-id');
        b.disabled = true;
        await rejectAdminReturn(id);
        await loadActiveTabData();
      });
    });

    container.querySelectorAll('.btn-complete-ret').forEach(b => {
      b.addEventListener('click', async () => {
        const id = b.getAttribute('data-ret-id');
        const ref = prompt('Enter Bank Refund Reference / Transaction ID (or leave blank for physical exchange):', 'MEZN-REF-');
        if (ref !== null) {
          b.disabled = true;
          await completeAdminReturn(id, { refund_reference: ref.trim(), should_restock: true });
          await loadActiveTabData();
        }
      });
    });
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
          <div style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.5); text-transform: uppercase; font-weight: 600; margin-bottom: 4px;">Realized Gross Revenue</div>
          <div style="font-size: 1.5rem; font-weight: 800; color: #4ADE80;">${escapeHtml(data.formatted_gross_revenue)}</div>
          <div style="font-size: 0.7rem; color: rgba(255, 255, 255, 0.4); margin-top: 4px;">Delivered & active verified orders</div>
        </div>

        <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 16px;">
          <div style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.5); text-transform: uppercase; font-weight: 600; margin-bottom: 4px;">Wholesale COGS</div>
          <div style="font-size: 1.5rem; font-weight: 800; color: #F59E0B;">${escapeHtml(data.formatted_cogs)}</div>
          <div style="font-size: 0.7rem; color: rgba(255, 255, 255, 0.4); margin-top: 4px;">Supplier product cost snapshot</div>
        </div>

        <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 16px;">
          <div style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.5); text-transform: uppercase; font-weight: 600; margin-bottom: 4px;">Net Commercial Margin</div>
          <div style="font-size: 1.5rem; font-weight: 800; color: #38BDF8;">${escapeHtml(data.formatted_gross_profit)}</div>
          <div style="font-size: 0.7rem; color: #38BDF8; font-weight: 700; margin-top: 4px;">${data.gross_margin_percent}% Gross Margin</div>
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

  // These forms are completed with the fulfillment/settlement repairs. Until
  // then, keep them dismissible and prevent an unhandled native form reload.
  for (const [formId, cancelId, dialogId] of [
    ['admin-dispatch-form', 'btn-cancel-dispatch', 'admin-dispatch-modal'],
    ['admin-remittance-form', 'btn-cancel-remit', 'admin-remittance-modal'],
  ]) {
    modal.querySelector(`#${formId}`).addEventListener('submit', event => event.preventDefault());
    modal.querySelector(`#${cancelId}`).addEventListener('click', () => {
      modal.querySelector(`#${dialogId}`).style.display = 'none';
    });
  }

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
