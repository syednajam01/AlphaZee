import { createOverlay } from '../utils/overlay.js';
import { createBrandLogo } from './BrandLogo.js';
import {
  fetchAdminOverview,
  fetchAdminInventory,
  adjustAdminInventory,
  fetchAdminOrders,
  confirmSupplierAcceptance,
  confirmSupplierPickup,
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
  fetchAdminCatalogVariants,
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
  fetchAdminPreferences,
  onOwnerSessionExpired,
  removeLegacyAdminCredentials,
} from '../utils/api.js';
import { escapeHtml } from '../utils/dom.js';
import { formatPkr, parseCatalogPkr } from '../utils/money.js';
import { mountCatalogSection } from './admin/CatalogWorkspace.js';
import { mountStockHolds } from './admin/StockHolds.js';
import {orderEvidence, returnEvidence, mountFundsReview, mountAccessRecovery} from './admin/OrderEvidence.js';
import { createSupplierFinanceView } from './admin/SupplierFinance.js';
import { createVendorUsersModal } from './admin/VendorUsersModal.js';
import { renderBusinessExpenses } from './admin/BusinessExpenses.js';
import { renderFinancialReports } from './admin/FinancialReports.js';
import { createStoreSettingsComponent } from './admin/StoreSettings.js';

export function createAdminConsoleModal({ page = false, initialTab = 'overview', onNavigate = () => {} } = {}) {
  const modal = document.createElement('div');
  modal.className = page ? 'admin-page' : 'modal-container';
  modal.id = 'admin-modal';
  modal.setAttribute('role', page ? 'region' : 'dialog');
  modal.setAttribute('aria-label', 'AlphaZee Store Management Console');

  let activeTab = initialTab;
  let dirty = false;
  let authenticated = false;
  let currentRemitOutstandingMinor = 0;
  let authGeneration = 0;
  let viewGeneration = 0;
  let catalogView = null;
  let stockHoldViews = [];
  let dispatchOpener = null;
  let remitOpener = null;
  let ordersPage = 1, ordersStatus = '', ordersSearch = '', returnsStatus = '';
  let settlementGeneration = 0;
  removeLegacyAdminCredentials();
  let isCollapsed = false;
  let ownerPreferences = null;
  modal.addEventListener('owner-preferences-changed', () => { applyOwnerPreferences().catch(error => showSessionMessage(error.message)); });
  async function applyOwnerPreferences() {
    const prefs = await fetchAdminPreferences();
    if (!authenticated) return;
    ownerPreferences = prefs;
    modal.dataset.ownerTheme = prefs.theme === 'system' ? (window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark') : prefs.theme;
    modal.dataset.tableDensity = prefs.table_density;
    const nav = modal.querySelector('.admin-tab-btn')?.parentElement;
    if (nav) for (const id of prefs.nav_order || []) {
      const button = Array.from(nav.querySelectorAll('.admin-tab-btn')).find(node => node.dataset.tab === id);
      if (button) nav.append(button);
    }
  }


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
        <nav aria-label="Owner sections" style="flex: 1; padding: 12px 8px; display: flex; flex-direction: column; gap: 4px; overflow-y: auto;">
          <button type="button" class="admin-tab-btn" data-tab="overview" style="display: flex; align-items: center; gap: 10px; width: 100%; padding: 10px 12px; border-radius: 6px; background: rgba(20, 92, 68, 0.4); color: #FFFFFF; border: none; font-size: 0.8125rem; font-weight: 600; cursor: pointer; text-align: left;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
            </svg>
            <span class="admin-nav-label">Overview</span>
          </button>

          <button type="button" class="admin-tab-btn" data-tab="products" style="display: flex; align-items: center; gap: 10px; width: 100%; padding: 10px 12px; border-radius: 6px; background: transparent; color: rgba(255, 255, 255, 0.7); border: none; font-size: 0.8125rem; font-weight: 600; cursor: pointer; text-align: left;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"></path>
              <line x1="7" y1="7" x2="7.01" y2="7"></line>
            </svg>
            <span class="admin-nav-label">Products & Catalog</span>
          </button>

          <button type="button" class="admin-tab-btn" data-tab="collections" style="display: flex; align-items: center; gap: 10px; width: 100%; padding: 10px 12px; border-radius: 6px; background: transparent; color: rgba(255, 255, 255, 0.7); border: none; font-size: 0.8125rem; font-weight: 600; cursor: pointer; text-align: left;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
            </svg>
            <span class="admin-nav-label">Collections</span>
          </button>

          <button type="button" class="admin-tab-btn" data-tab="hero" style="display: flex; align-items: center; gap: 10px; width: 100%; padding: 10px 12px; border-radius: 6px; background: transparent; color: rgba(255, 255, 255, 0.7); border: none; font-size: 0.8125rem; font-weight: 600; cursor: pointer; text-align: left;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"></rect>
              <line x1="7" y1="2" x2="7" y2="22"></line>
              <line x1="17" y1="2" x2="17" y2="22"></line>
              <line x1="2" y1="12" x2="22" y2="12"></line>
              <line x1="2" y1="7" x2="7" y2="7"></line>
              <line x1="2" y1="17" x2="7" y2="17"></line>
              <line x1="17" y1="17" x2="22" y2="17"></line>
              <line x1="17" y1="7" x2="22" y2="7"></line>
            </svg>
            <span class="admin-nav-label">Homepage Hero</span>
          </button>

          <button type="button" class="admin-tab-btn" data-tab="media" style="display: flex; align-items: center; gap: 10px; width: 100%; padding: 10px 12px; border-radius: 6px; background: transparent; color: rgba(255, 255, 255, 0.7); border: none; font-size: 0.8125rem; font-weight: 600; cursor: pointer; text-align: left;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
              <circle cx="8.5" cy="8.5" r="1.5"></circle>
              <polyline points="21 15 16 10 5 21"></polyline>
            </svg>
            <span class="admin-nav-label">Media Library</span>
          </button>

          <button type="button" class="admin-tab-btn" data-tab="inventory" style="display: flex; align-items: center; gap: 10px; width: 100%; padding: 10px 12px; border-radius: 6px; background: transparent; color: rgba(255, 255, 255, 0.7); border: none; font-size: 0.8125rem; font-weight: 600; cursor: pointer; text-align: left;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
              <polyline points="2 17 12 22 22 17"></polyline>
              <polyline points="2 12 12 17 22 12"></polyline>
            </svg>
            <span class="admin-nav-label">Inventory & Stock</span>
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

          <button type="button" class="admin-tab-btn" data-tab="orders" style="display: flex; align-items: center; gap: 10px; width: 100%; padding: 10px 12px; border-radius: 6px; background: transparent; color: rgba(255, 255, 255, 0.7); border: none; font-size: 0.8125rem; font-weight: 600; cursor: pointer; text-align: left;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="9" cy="21" r="1"></circle>
              <circle cx="20" cy="21" r="1"></circle>
              <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>
            </svg>
            <span class="admin-nav-label">Orders & Logistics</span>
          </button>

          <button type="button" class="admin-tab-btn" data-tab="returns" style="display: flex; align-items: center; gap: 10px; width: 100%; padding: 10px 12px; border-radius: 6px; background: transparent; color: rgba(255, 255, 255, 0.7); border: none; font-size: 0.8125rem; font-weight: 600; cursor: pointer; text-align: left;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="1 4 1 10 7 10"></polyline>
              <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path>
            </svg>
            <span class="admin-nav-label">Returns & Refunds</span>
          </button>

          <button type="button" class="admin-tab-btn" data-tab="coupons" style="display: flex; align-items: center; gap: 10px; width: 100%; padding: 10px 12px; border-radius: 6px; background: transparent; color: rgba(255, 255, 255, 0.7); border: none; font-size: 0.8125rem; font-weight: 600; cursor: pointer; text-align: left;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"></path>
              <line x1="7" y1="7" x2="7.01" y2="7"></line>
            </svg>
            <span class="admin-nav-label">Coupons & Promos</span>
          </button>

          <button type="button" class="admin-tab-btn" data-tab="expenses" style="display: flex; align-items: center; gap: 10px; width: 100%; padding: 10px 12px; border-radius: 6px; background: transparent; color: rgba(255, 255, 255, 0.7); border: none; font-size: 0.8125rem; font-weight: 600; cursor: pointer; text-align: left;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 1v22M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
            </svg>
            <span class="admin-nav-label">Business Expenses</span>
          </button>

          <button type="button" class="admin-tab-btn" data-tab="analytics" style="display: flex; align-items: center; gap: 10px; width: 100%; padding: 10px 12px; border-radius: 6px; background: transparent; color: rgba(255, 255, 255, 0.7); border: none; font-size: 0.8125rem; font-weight: 600; cursor: pointer; text-align: left;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="20" x2="18" y2="10"></line>
              <line x1="12" y1="20" x2="12" y2="4"></line>
              <line x1="6" y1="20" x2="6" y2="14"></line>
            </svg>
            <span class="admin-nav-label">P&L & Analytics</span>
          </button>

          <button type="button" class="admin-tab-btn" data-tab="settings" style="display: flex; align-items: center; gap: 10px; width: 100%; padding: 10px 12px; border-radius: 6px; background: transparent; color: rgba(255, 255, 255, 0.7); border: none; font-size: 0.8125rem; font-weight: 600; cursor: pointer; text-align: left;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="3"></circle>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
            </svg>
            <span class="admin-nav-label">Store Settings</span>
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
            <input type="number" id="dispatch-shipping-cost" value="250" min="0" step="0.01" style="width: 100%; padding: 8px 12px; background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 6px; font-size: 0.8125rem;" />
          </div>
          <div>
            <label style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); display: block; margin-bottom: 2px;">Tracking Web URL (Optional)</label>
            <input type="url" id="dispatch-tracking-url" placeholder="https://trax.pk/tracking?num=..." style="width: 100%; padding: 8px 12px; background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 6px; font-size: 0.8125rem;" />
          </div>
          <div id="dispatch-error" style="display: none; color: #F87171; font-size: 0.75rem; font-weight: 600;"></div>
          <div style="display: flex; gap: 8px; justify-content: flex-end; margin-top: 10px;">
            <button type="button" id="btn-cancel-dispatch" class="btn btn-secondary" style="padding: 6px 12px; font-size: 0.8125rem;">Cancel</button>
            <button type="submit" id="btn-submit-dispatch" class="btn btn-primary" style="padding: 6px 14px; font-size: 0.8125rem;">Dispatch order</button>
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

  if (page) {
    const nav = modal.querySelector('nav');
    const labels = [
      ['overview', 'Overview'], ['products', 'Products & Catalog'], ['collections', 'Collections'],
      ['hero', 'Homepage Hero'], ['media', 'Media Library'], ['inventory', 'Inventory & Stock'],
      ['suppliers', 'Suppliers'], ['orders', 'Orders and payments'],
      ['returns', 'Returns and exchanges'], ['coupons', 'Coupons & Promos'],
      ['expenses', 'Business Expenses'],
      ['analytics', 'Reports & Analytics']
    ];
    const icons = new Map([...nav.querySelectorAll('.admin-tab-btn')].map(button =>
      [button.getAttribute('data-tab'), button.querySelector('svg')?.outerHTML || '']));
    nav.innerHTML = labels.map(([tab, label]) => `<button type="button" class="admin-tab-btn" data-tab="${tab}">${icons.get(tab) || '<span aria-hidden="true">·</span>'}<span class="admin-nav-label">${label}</span></button>`).join('');
    const returnLink = document.createElement('a');
    returnLink.href = '/'; returnLink.textContent = 'Return to store';
    returnLink.className = 'admin-return-link';
    modal.querySelector('header').appendChild(returnLink);
    modal.querySelector('.drawer-backdrop').hidden = true;
    modal.querySelector('#admin-close-btn').hidden = true;
    modal.querySelector('[data-tab="orders"] .admin-nav-label').textContent = 'Orders and payments';
    modal.querySelector('[data-tab="returns"] .admin-nav-label').textContent = 'Returns and exchanges';
    modal.querySelector('[data-tab="analytics"] .admin-nav-label').textContent = 'Reports & Analytics';
    returnLink.addEventListener('click', event => { if (!canLeave()) event.preventDefault(); });
    for (const type of ['input', 'change']) modal.addEventListener(type, event => {
      const form = event.target?.closest?.('form');
      if (authenticated && form && !['admin-order-filters','admin-return-filters'].includes(form.id)) dirty = true;
    });
  }

  function canLeave() {
    return !page || !dirty || window.confirm('Discard your unsaved changes?');
  }

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

  function updateNavigation() {
    const titles = {
      overview: 'Store overview', products: 'Products & Catalog', collections: 'Collections',
      hero: 'Homepage Hero Playlist', media: 'Media Library', orders: 'Orders and payments',
      inventory: 'Inventory and stock', coupons: 'Coupons & Promos', returns: 'Returns and exchanges',
      suppliers: 'Suppliers', expenses: 'Business Expenses & Freight', analytics: 'Reports & Analytics',
      settings: 'Store Configuration & Admin Preferences'
    };
    viewTitle.textContent = titles[activeTab] || 'Section not found';
    tabBtns.forEach(button => {
      const selected = button.getAttribute('data-tab') === activeTab;
      button.setAttribute('aria-current', selected ? 'page' : 'false');
      button.setAttribute('title', titles[button.getAttribute('data-tab')] || '');
      button.style.background = selected ? 'rgba(20, 92, 68, 0.4)' : 'transparent';
      button.style.color = selected ? '#FFFFFF' : 'rgba(255, 255, 255, 0.7)';
    });
  }

  function selectTab(tab, { checkDirty = true } = {}) {
    if (checkDirty && !canLeave()) return false;
    activeTab = tab;
    dirty = false;
    closeDispatch(); closeRemittance();
    updateNavigation();
    loadActiveTabData();
    return true;
  }
  updateNavigation();

  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const tab = btn.getAttribute('data-tab');
      if (tab === activeTab) return;
      if (page) { if (canLeave()) onNavigate(tab); return; }
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
        expenses: 'Operating Costs & Transport Expenses',
        analytics: 'Gross Profit, COGS & Attribution',
        settings: 'Store Configuration & Admin Preferences',
      };
      if (viewTitle) viewTitle.textContent = titles[tab] || 'Store Management';

      loadActiveTabData();
    });
  });

  modal.querySelector('#btn-refresh-admin-tab')?.addEventListener('click', () => {
    if (canLeave()) loadActiveTabData();
  });

  modal.querySelector('#btn-admin-logout')?.addEventListener('click', async () => {
    if (!canLeave()) return;
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
    settlementGeneration++;
    stockHoldViews.forEach(view => view.destroy()); stockHoldViews = [];
    catalogView?.destroy(); catalogView = null;
    authGeneration++;
    viewGeneration++;
    authenticated = false;
    dirty = false;
    closeDispatch(); closeRemittance();
    modal.querySelector('#admin-dispatch-form').reset?.();
    modal.querySelector('#admin-remittance-form').reset?.();
    modal.querySelector('#remit-history').textContent = '';
    modal.querySelector('#remit-summary').textContent = '';
    showSessionMessage(message);
    if (page) sidebar.hidden = true;
    modal.querySelector('#btn-refresh-admin-tab').hidden = true;
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
        await applyOwnerPreferences();
        if (page) sidebar.hidden = false;
        modal.querySelector('#btn-refresh-admin-tab').hidden = false;
        showSessionMessage('');
        modal.querySelector('#btn-admin-logout').hidden = false;
        await loadActiveTabData();
      } catch (error) {
        passwordInput.value = '';
        if (generation === authGeneration) form.querySelector('#admin-login-error').textContent = error.message || 'Unable to sign in.';
      } finally { button.disabled = false; }
    });
  }

  const unsubscribeSession = onOwnerSessionExpired(() => {
    authenticated = false;
    renderLogin('Your session has ended. Sign in again to continue.');
  });

  async function loadActiveTabData() {
    if (!contentArea) return;
    if (!authenticated) { renderLogin(); return; }
    const generation = authGeneration;
    const view = ++viewGeneration;
    stockHoldViews.forEach(v => v.destroy()); stockHoldViews = [];
    catalogView?.destroy(); catalogView = null;
    dirty = false;
    contentArea.innerHTML = '<div style="text-align: center; color: rgba(255, 255, 255, 0.5); padding: 40px 0;">Loading data...</div>';

    try {
      if (activeTab === 'overview') {
        await renderOverviewTab(contentArea, view);
      } else if (activeTab === 'orders') {
        await renderOrdersTab(contentArea, view);
      } else if (activeTab === 'inventory') {
        await renderInventoryTab(contentArea, view);
      } else if (activeTab === 'coupons') {
        await renderCouponsTab(contentArea, view);
      } else if (activeTab === 'returns') {
        await renderReturnsTab(contentArea, view);
      } else if (activeTab === 'suppliers') {
        await renderSuppliersTab(contentArea, view);
      } else if (activeTab === 'expenses') {
        await renderBusinessExpenses(contentArea, view);
      } else if (activeTab === 'analytics') {
        await renderAnalyticsTab(contentArea, view);
      } else if (activeTab === 'settings') {
        await renderSettingsTab(contentArea, view);
      } else if (['products', 'collections', 'media', 'hero'].includes(activeTab)) {
        catalogView = mountCatalogSection(activeTab, contentArea, {
          isCurrent: () => view === viewGeneration && authenticated,
          setDirty: value => { if (view === viewGeneration) dirty = value; },
          canLeave,
          onNavigate: (tab, payload) => {
            activeTab = tab;
            updateNavigation();
            renderTab();
          },
        });
        await catalogView.ready;
      } else {
        contentArea.innerHTML = '<section class="admin-empty-state"><h3>Section not found</h3><p>Choose a section from the owner navigation.</p></section>';
      }
      if (view !== viewGeneration) return;
      if (authenticated) await applyOwnerPreferences();
      if (generation !== authGeneration && !authenticated) renderLogin('Sign in again to continue.');
    } catch (err) {
      if (err.status === 401) {
        authenticated = false;
        renderLogin('Your session has ended. Sign in again to continue.');
        return;
      }
      if (generation !== authGeneration || view !== viewGeneration) return;

      contentArea.innerHTML = `
        <div style="padding: 16px; background: rgba(220, 38, 38, 0.15); border: 1px solid rgba(220, 38, 38, 0.3); border-radius: 6px; color: #FCA5A5; font-size: 0.875rem;">
          Failed to load administrative data: ${escapeHtml(err.message)}
        </div>
      `;
    }
  }

  // 1. Overview Tab
  async function renderOverviewTab(container, view) {
    const data = await fetchAdminOverview();
    if (view !== viewGeneration) return;
    container.innerHTML = `
      <div class="admin-financial-overview">${[['Cash received after refunds',data.cash_received_minor],['Courier-held COD',data.courier_held_cod_minor],['Refund outstanding',data.refund_outstanding_minor],['Estimated contribution',data.estimated_contribution_minor]].map(([label,amount])=>`<div><span>${label}</span><strong>${escapeHtml(formatPkr(amount ?? 0))}</strong></div>`).join('')}</div>
      <div id="owner-kpi-cards" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px;">
        <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 16px;">
          <div style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.5); text-transform: uppercase; font-weight: 600; margin-bottom: 4px;">Delivered Sales</div>
          <div style="font-size: 1.5rem; font-weight: 800; color: #4ADE80;">${escapeHtml(data.formatted_gross_revenue)}</div>
          <div style="font-size: 0.7rem; color: rgba(255, 255, 255, 0.4); margin-top: 4px;">Bank prepayments and courier-held COD are separate in Analytics</div>
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
    const cards = container.querySelector('#owner-kpi-cards');
    const ids = ['sales', 'orders', 'inventory', 'low_stock'];
    if (cards) {
      const nodes = Array.from(cards.children);
      const layout = ownerPreferences?.dashboard_layout?.cards || ids.map(id => ({ id, visible: true }));
      for (const card of layout) {
        const node = nodes[ids.indexOf(card.id)];
        if (node) { node.hidden = !card.visible; cards.append(node); }
      }
    }
  }

  async function openSettlement(shipmentId, opener, view) {
    if(opener.disabled || !authenticated || view!==viewGeneration || !canLeave())return;
    const request=++settlementGeneration;
    remitOpener=opener; opener.disabled=true;
    try {
      const shipment=await fetchAdminShipmentSettlement(shipmentId);
      if(!authenticated || view!==viewGeneration || request!==settlementGeneration)return;
      currentRemitOutstandingMinor=shipment.settlement_outstanding_minor;
      modal.querySelector('#remit-shipment-id').value=shipmentId;
      modal.querySelector('#remit-summary').textContent=`Gross COD ${formatPkr(shipment.cod_amount_minor)} · Bank receipts ${formatPkr(shipment.cod_remitted_amount_minor)} · Deductions ${formatPkr(shipment.settlement_deductions_minor)} · Outstanding ${formatPkr(shipment.settlement_outstanding_minor)}`;
      modal.querySelector('#remit-history').textContent=(shipment.settlement_entries || []).map(entry=>`${entry.entry_type}: ${formatPkr(entry.amount_minor)} (${entry.reference})`).join(' | ') || 'No settlement entries yet.';
      modal.querySelector('#remit-error').style.display='none';
      modal.querySelector('#admin-remittance-modal').style.display='flex';
      setPageBackgroundInert(true);modal.querySelector('#remit-amount-pkr').focus();
    } catch(error) {if(authenticated && view===viewGeneration)showSessionMessage(error.message || 'Unable to load settlement');}
    finally {opener.disabled=false;}
  }

  // 2. Orders Tab
  async function renderOrdersTab(container, view) {
    const orderId = new URLSearchParams(window.location?.search || '').get('order_id');
    const res = await fetchAdminOrders({ orderId, page:ordersPage, status:ordersStatus, search:ordersSearch });
    if (view !== viewGeneration) return;
    const orders = res.orders || [];

    const isCurrent = () => authenticated && view === viewGeneration;

    const rowsHtml = orders.map(o => {
      const isBank = o.payment_method === 'bank_transfer';
      const isPaid = o.payment_status === 'verified';
      const isDelivered = o.order_status === 'delivered';
      const isCancelled = o.order_status === 'cancelled';
      const shipment = o.shipments?.find(s => !s.replacement_return_id) || null;
      const hasShipment = Boolean(shipment);

      return `
        <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.06); font-size: 0.8125rem;">
          <td style="padding: 12px 8px; font-weight: 700; color: #4ADE80;">${escapeHtml(o.order_number)}${orderEvidence(o)}</td>
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
                Review Bank Transfer
              </button>
            ` : ''}
            ${o.order_status === 'placed' && !isCancelled ? `
              <button class="btn btn-secondary btn-confirm-supplier" data-order-id="${o.id}" style="padding: 4px 8px; font-size: 0.7rem; margin-right: 4px; border-color: rgba(74, 222, 128, 0.4); color: #4ADE80;">
                Confirm Supplier
              </button>
            ` : ''}
            ${o.order_status === 'confirmed' && !o.supplier_picked_up_at ? `<button class="btn btn-secondary btn-confirm-pickup" data-order-id="${o.id}">Record physical pickup</button>` : ''}
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
            ${o.order_status === 'dispatched' && shipment?.stock_reconciliation_status !== 'legacy_review' ? `
              ${shipment?.status === 'dispatched' ? `<button class="btn btn-secondary btn-update-shipment" data-shipment-id="${shipment.id}" data-next="in_transit" style="padding: 4px 8px; font-size: .7rem;">In Transit</button>` : ''}
              ${['dispatched', 'in_transit'].includes(shipment?.status) ? `<button class="btn btn-secondary btn-update-shipment" data-shipment-id="${shipment.id}" data-next="out_for_delivery" style="padding: 4px 8px; font-size: .7rem;">Out for Delivery</button>` : ''}
              <button class="btn btn-primary btn-mark-delivered" data-shipment-id="${shipment?.id || ''}" style="padding: 4px 8px; font-size: .7rem;">Mark Delivered</button>
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
      <form id="admin-order-filters" class="catalog-toolbar"><label>Order number or phone<input name="search" maxlength="100" value="${escapeHtml(ordersSearch)}"></label>
        <label>Order status<select name="status"><option value="">All statuses</option>${['placed','confirmed','dispatched','delivered','rto','cancelled'].map(s=>`<option value="${s}" ${s===ordersStatus?'selected':''}>${s}</option>`).join('')}</select></label>
        <button type="submit" class="btn btn-secondary">Apply order filters</button>${orderId ? '<a class="admin-return-link" href="/admin/orders">Show all orders</a>' : ''}</form>
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
          <tbody>${rowsHtml || '<tr><td colspan="6">No orders match this view. Clear filters to see other orders.</td></tr>'}</tbody>
        </table>
      </div>
      <div class="catalog-toolbar"><button type="button" class="btn btn-secondary" data-orders-prev ${ordersPage<=1?'disabled':''}>Previous orders</button><span>Page ${ordersPage} · ${res.total ?? orders.length} orders</span><button type="button" class="btn btn-secondary" data-orders-next ${ordersPage*(res.page_size || 20)>=(res.total ?? orders.length)?'disabled':''}>Next orders</button></div>
      <div id="payment-workflow-panel" role="region" aria-live="polite"></div>
    `;

    const filter = container.querySelector('#admin-order-filters');
    filter.addEventListener('submit',event=>{event.preventDefault();if(!isCurrent() || !canLeave())return;ordersSearch=filter.querySelector('[name="search"]').value.trim();ordersStatus=filter.querySelector('[name="status"]').value;ordersPage=1;loadActiveTabData();});
    for (const [selector,delta] of [['[data-orders-prev]',-1],['[data-orders-next]',1]]) container.querySelector(selector).addEventListener('click',event=>{if(event.currentTarget?.disabled || !isCurrent() || !canLeave())return;ordersPage+=delta;loadActiveTabData();});

    container.querySelectorAll('.btn-recover-order-access').forEach(b => b.addEventListener('click', async () => {
      if(!isCurrent() || !canLeave())return;
      mountAccessRecovery(container.querySelector('#payment-workflow-panel'),orders.find(o=>o.id===b.getAttribute('data-order-id')),{isCurrent,onIssued:()=>{dirty=false;}});
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
      await openSettlement(shipmentId,b,view);
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
          if(!isCurrent())return;
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
            if(submit.disabled || !isCurrent())return;
            if(!form.elements.confirmed_sent.checked || form.elements.reference.value.trim().length<3){form.querySelector('.payment-workflow-feedback').textContent='Confirm successful handoff and enter its reference.';return;}
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
          if(submit.disabled || !isCurrent())return;
          if(!form.elements.funds_checked.checked || form.elements.note.value.trim().length<5){form.querySelector('.payment-workflow-feedback').textContent='Confirm you checked funds and enter a review note.';return;}
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
        if(!isCurrent() || !canLeave())return;
        mountFundsReview(workflowPanel,orders.find(o=>o.id===orderId),{isCurrent,onSaved:loadActiveTabData});
      });
    });

    container.querySelectorAll('.btn-confirm-pickup').forEach(button => button.addEventListener('click', async () => {
      if (!window.confirm('Confirm the goods have physically been collected? This may record a vendor payable under the snapshotted agreement.')) return;
      button.disabled = true;
      try { await confirmSupplierPickup(button.dataset.orderId); await loadActiveTabData(); }
      catch (error) { showSessionMessage(error.message); button.disabled = false; }
    }));
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
          if(costInput === null)return;
          const costMinor = parseCatalogPkr(costInput || '0');
          if(costMinor === null){alert('Enter a nonnegative PKR courier cost with up to two decimals.');return;}
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
        dispatchOpener = b;
        const orderId = b.getAttribute('data-order-id');
        const modalEl = modal.querySelector('#admin-dispatch-modal');
        const idInput = modal.querySelector('#dispatch-order-id');
        if (modalEl && idInput) {
          modal.querySelector('#admin-dispatch-form').reset();
          modal.querySelector('#dispatch-error').style.display = 'none';
          idInput.value = orderId;
          modalEl.style.display = 'flex';
          setPageBackgroundInert(true);
          modal.querySelector('#dispatch-courier-code').focus();
        }
      });
    });
    container.querySelectorAll('.btn-mark-delivered').forEach(b => b.addEventListener('click', async () => {
      const shipmentId = b.getAttribute('data-shipment-id');
      if (!shipmentId || !confirm('Confirm the courier delivered this parcel and collected COD, if applicable?')) return;
      b.disabled = true;
      try { await updateAdminShipmentStatus(shipmentId, { status: 'delivered' }); await loadActiveTabData(); }
      catch (error) { alert(error.message || 'Unable to mark delivery'); b.disabled = false; }
    }));
    container.querySelectorAll('.btn-update-shipment').forEach(b => b.addEventListener('click', async () => {
      b.disabled = true;
      try {
        await updateAdminShipmentStatus(b.getAttribute('data-shipment-id'), { status: b.getAttribute('data-next') });
        await loadActiveTabData();
      } catch (error) { alert(error.message || 'Unable to update courier status'); b.disabled = false; }
    }));
  }

  // 3. Inventory Tab
  async function renderInventoryTab(container, view) {
    const res = await fetchAdminInventory();
    if (view !== viewGeneration) return;
    const items = res.items || [];

    const rowsHtml = items.map(it => `
      <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.06); font-size: 0.8125rem;">
        <td style="padding: 12px 8px; font-weight: 600;">${escapeHtml(it.product_title)}<div style="font-size: .7rem; opacity: .7;">${escapeHtml(it.supplier_name || '')}</div></td>
        <td style="padding: 12px 8px; font-family: monospace; color: rgba(255, 255, 255, 0.7);">${escapeHtml(it.sku)} ${escapeHtml([it.size, it.color].filter(Boolean).join(' / '))}</td>
        <td style="padding: 12px 8px;">${it.physical_on_hand}</td>
        <td style="padding: 12px 8px; color: #FBBF24;">${it.held_reservations}<details><summary>See reserved orders</summary><div data-inventory-holds="${it.supplier_variant_id}"></div></details></td>
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
      ${items.length ? `<form id="inventory-adjust-form" style="margin-top: 16px; display: flex; flex-wrap: wrap; gap: 8px; align-items: end;">
        <label>Supplier / variant <select id="inventory-target" required>${items.map(it => `<option value="${it.supplier_variant_id}">${escapeHtml(it.supplier_name || '')} / ${escapeHtml(it.sku)} / ${escapeHtml([it.size, it.color].filter(Boolean).join(' / '))}</option>`).join('')}</select></label>
        <label>Quantity change <input id="inventory-delta" type="number" required step="1" placeholder="+ received / - loss"></label>
        <label>Reason <select id="inventory-reason" required><option value="supplier_receipt">Supplier receipt</option><option value="manual_count">Physical count</option><option value="adjustment_correction">Damage or correction</option></select></label>
        <label>Invoice / audit ref <input id="inventory-reference" maxlength="100"></label>
        <button type="submit" class="btn btn-primary">Save adjustment</button>
        <p id="inventory-adjust-feedback" role="status" style="width: 100%;"></p>
      </form>` : '<p>No active supplier variants. Assign a catalog variant to a supplier first.</p>'}
    `;
    const form = container.querySelector('#inventory-adjust-form');
    for (const item of items) stockHoldViews.push(mountStockHolds(container.querySelector(`[data-inventory-holds="${item.supplier_variant_id}"]`), item.supplier_variant_id, null, () => view === viewGeneration && authenticated));
    form?.addEventListener('submit', async event => {
      event.preventDefault();
      const button = form.querySelector('button[type="submit"]');
      if (button.disabled) return;
      const feedback = form.querySelector('#inventory-adjust-feedback');
      const item = items.find(row => row.supplier_variant_id === form.querySelector('#inventory-target').value);
      const delta = Number(form.querySelector('#inventory-delta').value);
      const reason = form.querySelector('#inventory-reason').value.trim();
      if (!item || !Number.isSafeInteger(delta) || delta === 0 || reason.length < 3) {
        feedback.textContent = 'Select a supplier variant, a nonzero whole-unit change, and a reason.'; return;
      }
      button.disabled = true;
      button.textContent = 'Saving...';
      feedback.textContent = '';
      try {
        await adjustAdminInventory({ supplier_variant_id: item.supplier_variant_id,
          quantity_delta: delta, expected_version: item.version, reason,
          reference_id: form.querySelector('#inventory-reference').value.trim() || null });
        await loadActiveTabData();
        showSessionMessage('Inventory adjustment saved; physical, held, and available stock refreshed.');
      } catch (error) {
        feedback.textContent = error.status === 409
          ? 'Stock changed since this page loaded. Refresh inventory and retry with the current balance.'
          : error.message || 'Unable to adjust inventory.';
        button.disabled = false;
        button.textContent = 'Save adjustment';
      }
    });
  }

  // 4. Coupons Tab
  async function renderCouponsTab(container, view) {
    const coupons = await fetchAdminCoupons();
    if (view !== viewGeneration) return;

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
                <input type="number" id="cpn-val" required min="0" step="0.01" value="10" style="width: 100%; padding: 8px 12px; background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 6px; font-size: 0.8125rem;" />
              </div>
            </div>
            <div>
              <label style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); display: block; margin-bottom: 2px;">Min Subtotal (PKR)</label>
              <input type="number" id="cpn-min-pkr" value="0" min="0" step="0.01" style="width: 100%; padding: 8px 12px; background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 6px; font-size: 0.8125rem;" />
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
          try { await deleteAdminCoupon(id); await loadActiveTabData(); }
          catch (error) { alert(error.message || 'Unable to delete coupon.'); b.disabled = false; }
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
      if(saveBtn.disabled)return;
      const rawValue = container.querySelector('#cpn-val').value.trim();
      const val = discountType === 'fixed_amount' ? parseCatalogPkr(rawValue) : discountType === 'free_shipping' ? 0 : Number(rawValue);
      const minimum = parseCatalogPkr(container.querySelector('#cpn-min-pkr').value || '0');
      const limitRaw = container.querySelector('#cpn-limit').value.trim();
      const usageLimit = limitRaw ? Number(limitRaw) : null;
      if(val === null || minimum === null || (discountType === 'percentage' && (!Number.isInteger(val) || val<1 || val>100)) || (usageLimit !== null && (!Number.isInteger(usageLimit) || usageLimit<1 || usageLimit>2147483647))){cpnError.textContent='Use exact PKR amounts, a whole percentage from 1–100 and a positive whole usage limit.';cpnError.style.display='block';return;}

      saveBtn.disabled = true;
      saveBtn.textContent = 'Creating...';
      cpnError.style.display = 'none';

      try {
        await createAdminCoupon({
          code,
          discount_type: discountType,
          discount_value: val,
          min_subtotal_minor: minimum,
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
  async function renderReturnsTab(container, view) {
    const returns = await fetchAdminReturns({status:returnsStatus});
    if (view !== viewGeneration) return;

    const rowsHtml = returns.map(r => `
      <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.06); font-size: 0.8125rem;">
        <td style="padding: 12px 8px; font-family: monospace; color: rgba(255, 255, 255, 0.7);">${escapeHtml(String(r.id).slice(0, 8))}${returnEvidence(r)}</td>
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
          ` : ''}
          ${['requested','approved'].includes(r.status) && !r.received_quantity ? `<button class="btn btn-secondary btn-reject-ret" data-ret-id="${r.id}">Reject / withdraw approval</button>` : ''}
          ${['approved', 'item_received', 'inspected_passed'].includes(r.status) ? `
            ${r.status === 'approved' && r.inspection_state !== 'legacy_review' && r.received_quantity === 0 ? `<button class="btn btn-secondary btn-receive-ret" data-ret-id="${r.id}" style="padding: 4px 8px; font-size: .7rem;">Record Receipt</button>` : ''}
            ${r.inspection_state !== 'legacy_review' && r.received_quantity > r.sellable_quantity + r.damaged_quantity ? `<button class="btn btn-secondary btn-inspect-ret" data-ret-id="${r.id}" style="padding: 4px 8px; font-size: .7rem;">Inspect Units</button>` : ''}
            ${r.received_quantity > 0 && r.sellable_quantity + r.damaged_quantity === r.received_quantity ? `<button class="btn btn-primary btn-complete-ret" data-ret-id="${r.id}" style="padding: 4px 8px; font-size: 0.7rem;">Complete Return</button>` : ''}
          ` : ''}
          ${r.return_type === 'size_exchange' && ['inspected_passed', 'completed'].includes(r.status) && r.received_quantity === r.quantity && !r.replacement_shipment_id ? `<button class="btn btn-primary btn-dispatch-replacement" data-ret-id="${r.id}" style="padding: 4px 8px; font-size: .7rem;">Dispatch Replacement</button>` : ''}
          ${r.return_type === 'refund_bank_transfer' && r.status === 'completed' && r.refund_outstanding.minor > 0 ? `<button class="btn btn-primary btn-record-refund" data-ret-id="${r.id}" style="padding: 4px 8px; font-size: .7rem;">Record Paid Refund</button>` : ''}
          ${r.replacement_shipment_id ? `<div style="font-size: .7rem;">Replacement: ${escapeHtml(r.replacement_shipment_status)}</div>
            ${r.replacement_shipment_status === 'dispatched' ? `<button class="btn btn-secondary btn-replacement-status" data-ret-id="${r.id}" data-next="in_transit">In Transit</button>` : ''}
            ${['dispatched','in_transit'].includes(r.replacement_shipment_status) ? `<button class="btn btn-secondary btn-replacement-status" data-ret-id="${r.id}" data-next="out_for_delivery">Out for Delivery</button>` : ''}
            ${['dispatched', 'in_transit', 'out_for_delivery'].includes(r.replacement_shipment_status) ? `<button class="btn btn-secondary btn-replacement-status" data-ret-id="${r.id}" data-next="delivered">Mark Delivered</button><button class="btn btn-secondary btn-replacement-status" data-ret-id="${r.id}" data-next="rto_initiated">Start RTO</button>` : ''}
            ${r.replacement_shipment_status === 'rto_initiated' ? `<button class="btn btn-secondary btn-replacement-status" data-ret-id="${r.id}" data-next="rto_delivered">Receive RTO</button>` : ''}
            ${r.replacement_shipment_status === 'rto_delivered' && !r.replacement_rto_inspected_at && r.replacement_stock_reconciliation_status !== 'legacy_review' ? `<button class="btn btn-secondary btn-inspect-replacement-rto" data-ret-id="${r.id}">Inspect RTO</button>` : ''}
            ${r.replacement_rto_inspected_at ? '<div>Replacement RTO inspection completed</div>' : ''}
            ${r.replacement_shipment_status === 'delivered' && r.replacement_charge?.minor>0 ? `<button class="btn btn-secondary btn-remit-replacement" data-shipment-id="${r.replacement_shipment_id}">Replacement COD settlement</button>` : ''}` : ''}
        </td>
      </tr>
    `).join('');

    container.innerHTML = `
      <div>
        <h3 style="font-size: 0.9375rem; font-weight: 700; margin-bottom: 12px;">Customer Return & Size Exchange Inquiries</h3>
        <form id="admin-return-filters" class="catalog-toolbar"><label>Return status<select name="status"><option value="">All statuses</option>${['requested','approved','item_received','inspected_passed','completed','rejected'].map(s=>`<option value="${s}" ${s===returnsStatus?'selected':''}>${s}</option>`).join('')}</select></label><button type="submit" class="btn btn-secondary">Filter returns</button></form>
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

    const returnFilter=container.querySelector('#admin-return-filters');
    returnFilter.addEventListener('submit',event=>{event.preventDefault();if(!canLeave())return;returnsStatus=returnFilter.querySelector('select').value;loadActiveTabData();});
    container.querySelectorAll('.btn-remit-replacement').forEach(button=>button.addEventListener('click',()=>openSettlement(button.getAttribute('data-shipment-id'),button,view)));
    container.querySelectorAll('.btn-approve-ret').forEach(b => {
      b.addEventListener('click', async () => {
        const id = b.getAttribute('data-ret-id');
        const ret = returns.find(item => item.id === id);
        const payload = {};
        if (ret?.return_type === 'size_exchange') {
          const charge = prompt('Additional replacement charge in PKR (default 0; original COD is never charged again):', '0');
          if (charge === null) return;
          const amount = parseCatalogPkr(charge);
          if (amount === null) {
            alert('Enter a non-negative amount in PKR.');
            return;
          }
          payload.replacement_charge_minor = amount;
        }
        b.disabled = true;
        try { await approveAdminReturn(id, payload); await loadActiveTabData(); }
        catch (error) { alert(error.message || 'Failed to approve return'); b.disabled = false; }
      });
    });

    container.querySelectorAll('.btn-reject-ret').forEach(b => {
      b.addEventListener('click', async () => {
        const id = b.getAttribute('data-ret-id');
        if(!confirm('Reject this return and release any unused replacement reservation?'))return;
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
      const amountMinor = parseCatalogPkr(amountValue);
      if (amountMinor === null || amountMinor <= 0 || amountMinor > ret.refund_outstanding.minor) {
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
      const value = prompt(`Actual received quantity, recorded once (requested ${ret.quantity}):`, String(ret.quantity));
      if (value === null) return;
      const quantity = Number(value);
      if (!Number.isInteger(quantity) || quantity <= 0 || quantity < ret.received_quantity || quantity > ret.quantity) {
        alert('Enter a positive whole quantity no greater than the requested quantity. This receipt is recorded once.');
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
  async function renderSuppliersTab(container, view) {
    const [res, variants] = await Promise.all([fetchAdminSuppliers(), fetchAdminCatalogVariants()]);
    if (view !== viewGeneration) return;
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
        <td style="padding: 12px 8px; text-align: right; white-space: nowrap;">
          <button type="button" class="btn btn-manage-finance" data-supplier-id="${s.id}" style="background: rgba(20, 92, 68, 0.4); border: 1px solid #145C44; color: #FFF; padding: 4px 10px; border-radius: 4px; font-size: 0.75rem; cursor: pointer; margin-right: 6px;">
            Finance &amp; Ledger
          </button>
          <button type="button" class="btn btn-manage-stock-users" data-supplier-id="${s.id}" style="background: rgba(59, 130, 246, 0.25); border: 1px solid #3B82F6; color: #93C5FD; padding: 4px 10px; border-radius: 4px; font-size: 0.75rem; cursor: pointer;">
            🔑 Stock Logins
          </button>
        </td>
      </tr>
    `).join('');

    container.innerHTML = `
      <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 20px;">
        <div>
          <h3 style="font-size: 0.9375rem; font-weight: 700; margin-bottom: 12px;">Registered Local Suppliers</h3>
          <div style="overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse; text-align: left;">
              <thead>
                <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.12); font-size: 0.75rem; color: rgba(255, 255, 255, 0.5); text-transform: uppercase;">
                  <th style="padding: 8px;">Supplier Name</th>
                  <th style="padding: 8px;">Identifier Slug</th>
                  <th style="padding: 8px;">Status</th>
                  <th style="padding: 8px;">Terms / Notes</th>
                  <th style="padding: 8px; text-align: right;">Actions</th>
                </tr>
              </thead>
              <tbody>${rowsHtml.length ? rowsHtml : '<tr><td colspan="5" style="padding: 20px 8px; text-align: center; color: rgba(255,255,255,0.4);">No suppliers registered yet.</td></tr>'}</tbody>
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
      <form id="supplier-variant-form" style="margin-top: 18px; display: flex; flex-wrap: wrap; gap: 8px; align-items: end;">
        <h3 style="width: 100%;">Assign supplier and product cost</h3>
        <label>Supplier <select id="mapping-supplier" required>${suppliers.filter(s => s.status === 'active').map(s => `<option value="${s.id}">${escapeHtml(s.name)}</option>`).join('')}</select></label>
        <label>Catalog variant <select id="mapping-variant" required>${variants.map(v => `<option value="${v.id}">${escapeHtml(v.product_title)} / ${escapeHtml(v.sku)}${v.active_supplier_id ? ' (mapped)' : ' (unmapped)'}</option>`).join('')}</select></label>
        <label>Wholesale cost PKR <input id="mapping-cost" type="number" required min="0" step="0.01" placeholder="0.00"></label>
        <button type="submit" class="btn btn-primary" ${!suppliers.some(s => s.status === 'active') || !variants.length ? 'disabled' : ''}>Save cost mapping</button>
        <p id="mapping-feedback" role="status" style="width: 100%;">${!suppliers.length || !variants.length ? 'Register a supplier and catalog variant to enable mapping.' : ''}</p>
      </form>
    `;

    const mappingForm = container.querySelector('#supplier-variant-form');
    mappingForm?.addEventListener('submit', async event => {
      event.preventDefault();
      const button = mappingForm.querySelector('button[type="submit"]');
      if (button.disabled) return;
      const costMinor = parseCatalogPkr(mappingForm.querySelector('#mapping-cost').value);
      const feedback = mappingForm.querySelector('#mapping-feedback');
      if (costMinor === null) {
        feedback.textContent = 'Enter a nonnegative wholesale cost in PKR.'; return;
      }
      button.disabled = true;
      button.textContent = 'Saving...';
      feedback.textContent = '';
      try {
        await assignSupplierVariant(mappingForm.querySelector('#mapping-supplier').value, {
          variant_id: Number(mappingForm.querySelector('#mapping-variant').value),
          supplier_cost_minor: costMinor, active: true,
        });
        await loadActiveTabData();
        showSessionMessage('Supplier cost mapping saved and refreshed.');
      } catch (error) {
        feedback.textContent = error.message || 'Unable to map supplier and variant.';
        button.disabled = false;
        button.textContent = 'Save cost mapping';
      }
    });

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

    // Wire Finance & Ledger modal buttons
    container.querySelectorAll('.btn-manage-finance').forEach(btn => {
      btn.addEventListener('click', () => {
        const supId = btn.getAttribute('data-supplier-id');
        const sup = suppliers.find(s => String(s.id) === String(supId));
        if (sup) {
          const financeModal = createSupplierFinanceView(sup, {
            onClose: () => {
              if (activeTab === 'suppliers') renderSuppliersTab(container, viewGeneration);
            }
          });
          document.body.appendChild(financeModal);
        }
      });
    });

    // Wire Stock Logins modal buttons
    container.querySelectorAll('.btn-manage-stock-users').forEach(btn => {
      btn.addEventListener('click', () => {
        const supId = btn.getAttribute('data-supplier-id');
        const sup = suppliers.find(s => String(s.id) === String(supId));
        if (sup) {
          const usersModal = createVendorUsersModal(sup, {
            onClose: () => {
              if (activeTab === 'suppliers') renderSuppliersTab(container, viewGeneration);
            }
          });
          document.body.appendChild(usersModal);
        }
      });
    });
  }

  // 7. Analytics & Financial Reports Tab (VF4)
  async function renderAnalyticsTab(container, view) {
    await renderFinancialReports(container, view, ownerPreferences);
  }

  // 8. Store Settings & Preferences Tab (VF6)
  async function renderSettingsTab(container, view) {
    container.innerHTML = '';
    const settingsComp = createStoreSettingsComponent();
    container.appendChild(settingsComp);
  }


  async function open() {
    if (!page) overlay.open();
    if (page) sidebar.hidden = true;
    modal.querySelector('#btn-admin-logout').hidden = true;
    modal.querySelector('#btn-refresh-admin-tab').hidden = true;
    const generation = ++authGeneration;
    contentArea.innerHTML = '<p role="status">Checking owner session...</p>';
    try {
      await fetchOwnerSession();
      if (generation !== authGeneration) return;
      authenticated = true;
      await applyOwnerPreferences();
      if (page) sidebar.hidden = false;
      modal.querySelector('#btn-refresh-admin-tab').hidden = false;
      modal.querySelector('#btn-admin-logout').hidden = false;
      showSessionMessage('');
      await loadActiveTabData();
    } catch (error) {
      if (generation !== authGeneration) return;
      authenticated = false;
      renderLogin(error.status === 401 ? '' : 'Unable to reach the store. You can try signing in again.');
    }
  }

  function close() {
    authGeneration++; viewGeneration++;
    if (!page) overlay.close();
  }

  function setPageBackgroundInert(value) {
    if (page) modal.querySelector('.modal-content').inert = value;
  }
  const closeDispatch = () => {
    modal.querySelector('#admin-dispatch-modal').style.display = 'none';
    if (modal.querySelector('#admin-remittance-modal').style.display !== 'flex') setPageBackgroundInert(false);
    dispatchOpener?.focus?.();
  };
  const closeRemittance = () => {
    modal.querySelector('#admin-remittance-modal').style.display = 'none';
    if (modal.querySelector('#admin-dispatch-modal').style.display !== 'flex') setPageBackgroundInert(false);
    remitOpener?.focus?.();
  };
  modal.querySelector('#btn-cancel-dispatch').addEventListener('click', closeDispatch);
  modal.querySelector('#admin-dispatch-modal').addEventListener('click', event => {
    if (event.target === event.currentTarget) closeDispatch();
  });
  modal.querySelector('#admin-dispatch-form').addEventListener('submit', async event => {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector('#btn-submit-dispatch');
    if (button.disabled) return;
    const error = form.querySelector('#dispatch-error');
    const tracking = form.querySelector('#dispatch-tracking-number').value.trim();
    const costMinor = parseCatalogPkr(form.querySelector('#dispatch-shipping-cost').value || '0');
    const trackingUrl = form.querySelector('#dispatch-tracking-url').value.trim();
    if (tracking.length < 3 || costMinor === null) {
      error.textContent = 'Enter a tracking number and a nonnegative courier fee.';
      error.style.display = 'block'; return;
    }
    error.style.display = 'none';
    button.disabled = true;
    button.textContent = 'Dispatching...';
    try {
      await dispatchAdminOrder(form.querySelector('#dispatch-order-id').value, {
        courier_code: form.querySelector('#dispatch-courier-code').value,
        tracking_number: tracking, shipping_cost_minor: costMinor,
        tracking_url: trackingUrl || null,
      });
      closeDispatch();
      await loadActiveTabData();
    } catch (requestError) {
      error.textContent = requestError.message || 'Unable to dispatch this order.';
      error.style.display = 'block';
    } finally {
      button.disabled = false;
      button.textContent = 'Dispatch order';
    }
  });
  modal.querySelector('#btn-cancel-remit').addEventListener('click', closeRemittance);
  modal.querySelector('#admin-remittance-modal').addEventListener('click', event => {
    if (event.target === event.currentTarget) closeRemittance();
  });
  modal.querySelector('#admin-remittance-form').addEventListener('submit', async event => {
    event.preventDefault();
    const form = event.currentTarget;
    const submit = form.querySelector('#btn-submit-remit');
    if (submit.disabled) return;
    const error = form.querySelector('#remit-error');
    const cashMinor = parseCatalogPkr(form.querySelector('#remit-amount-pkr').value || '0');
    const deductionType = form.querySelector('#remit-deduction-type').value;
    const deductionMinor = parseCatalogPkr(form.querySelector('#remit-deduction-pkr').value || '0');
    const cashRef = form.querySelector('#remit-ref').value.trim();
    const deductionRef = form.querySelector('#remit-deduction-ref').value.trim();
    const deductionNote = form.querySelector('#remit-deduction-note').value.trim();
    const invalid = cashMinor === null || deductionMinor === null
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
      closeRemittance();
      await loadActiveTabData();
    } catch (requestError) {
      error.textContent = requestError.message || 'Unable to record settlement.';
      error.style.display = 'block';
    } finally {
      submit.disabled = false;
      submit.textContent = 'Record settlement';
    }
  });

  const overlay = page ? null : createOverlay({ element: modal, onEscape: () => {
    if (modal.querySelector('#admin-dispatch-modal').style.display === 'flex') { closeDispatch(); return true; }
    if (modal.querySelector('#admin-remittance-modal').style.display === 'flex') { closeRemittance(); return true; }
    return false;
  }, onClose: () => {
    modal.querySelector('#admin-dispatch-modal').style.display = 'none';
    modal.querySelector('#admin-remittance-modal').style.display = 'none';
  } });

  modal.querySelector('.drawer-backdrop').addEventListener('click', close);
  modal.querySelector('#admin-close-btn').addEventListener('click', close);

  function pageKeyDown(event) {
    const panel = ['#admin-dispatch-modal', '#admin-remittance-modal']
      .map(selector => modal.querySelector(selector)).find(node => node.style.display === 'flex');
    if (!panel) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      if (canLeave()) { closeDispatch(); closeRemittance(); dirty = false; }
    } else if (event.key === 'Tab') {
      const nodes = [...panel.querySelectorAll('button, input, select, textarea')]
        .filter(node => !node.disabled && node.type !== 'hidden');
      if (event.shiftKey && (document.activeElement === nodes[0] || !panel.contains(document.activeElement))) {
        event.preventDefault(); nodes.at(-1)?.focus();
      } else if (!event.shiftKey && (document.activeElement === nodes.at(-1) || !panel.contains(document.activeElement))) {
        event.preventDefault(); nodes[0]?.focus();
      }
    }
  }
  const beforeUnload = event => {
    if (dirty) { event.preventDefault(); event.returnValue = ''; }
  };
  if (page) {
    for (const selector of ['#admin-dispatch-modal', '#admin-remittance-modal']) {
      const panel = modal.querySelector(selector);
      panel.setAttribute('role', 'dialog');
      panel.setAttribute('aria-modal', 'true');
      panel.setAttribute('aria-label', selector.includes('dispatch') ? 'Dispatch order' : 'COD settlement');
    }
    document.addEventListener('keydown', pageKeyDown);
    window.addEventListener('beforeunload', beforeUnload);
  }

  return {
    element: modal,
    open,
    close,
    selectTab,
    canLeave,
    destroy() {
      stockHoldViews.forEach(v => v.destroy()); stockHoldViews = [];
      catalogView?.destroy(); catalogView = null;
      close(); unsubscribeSession();
      document.removeEventListener('keydown', pageKeyDown);
      if (page) window.removeEventListener('beforeunload', beforeUnload);
    },
  };
}
