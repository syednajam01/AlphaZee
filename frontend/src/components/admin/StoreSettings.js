/**
 * StoreSettings.js — Phase VF6 Store Configuration, Legal Policies & Admin Preferences.
 * Unslopped Redesign: High-density executive console, interactive live mockup,
 * compact semantic icons with hover tooltips, and zero visible scrollbars.
 */
import {
  fetchAdminStoreSettings,
  updateAdminStoreSettings,
  publishStorePolicy,
  fetchSettingsAuditLogs,
  fetchAdminPreferences,
  updateAdminPreferences,
  resetAdminPreferences,
} from '../../utils/api.js';

export function createStoreSettingsComponent() {
  const container = document.createElement('div');
  container.className = 'admin-settings-container';

  let currentSettings = null;
  let currentPreferences = null;
  let auditLogs = [];
  let activeTab = 'storefront'; // 'storefront' | 'shipping' | 'policies' | 'audit' | 'preferences'
  let activePolicy = 'delivery'; // 'delivery' | 'return' | 'terms' | 'privacy'

  function render() {
    container.innerHTML = `
      <!-- Executive Settings Header -->
      <div class="set-header">
        <div>
          <h2 class="set-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: #10B981;"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
            Store Settings & Preferences
          </h2>
          <p class="set-subtitle">
            Configure brand tokens, announcement banner, delivery rates, legal contracts, and personal console preferences.
          </p>
        </div>
        ${currentSettings ? `
          <div class="set-revision-badge">
            <span class="set-sync-dot"></span>
            <span style="font-size: 0.75rem; color: var(--admin-text-secondary);">Baseline:</span>
            <span id="settings-revision-badge" style="font-weight: 600; font-family: monospace; color: #10B981;">v${currentSettings.version}</span>
          </div>
        ` : ''}
      </div>

      <!-- Modern Tab Pill Navigation -->
      <div class="settings-tabs set-tabs-bar">
        <button type="button" class="settings-tab-btn set-tab-btn ${activeTab === 'storefront' ? 'active' : ''}" data-tab="storefront">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="13.5" cy="6.5" r=".5" fill="currentColor"/><circle cx="17.5" cy="10.5" r=".5" fill="currentColor"/><circle cx="8.5" cy="7.5" r=".5" fill="currentColor"/><circle cx="6.5" cy="12.5" r=".5" fill="currentColor"/><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z"/></svg>
          Storefront & Branding
        </button>
        <button type="button" class="settings-tab-btn set-tab-btn ${activeTab === 'shipping' ? 'active' : ''}" data-tab="shipping">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="14" height="10" x="1" y="5" rx="2"/><circle cx="5.5" cy="17.5" r="2.5"/><circle cx="17.5" cy="17.5" r="2.5"/><path d="M15 8h4.28a2 2 0 0 1 1.79 1.11l2.09 4.18A2 2 0 0 1 23 14.18V17h-3"/><path d="M1 12h14"/></svg>
          Shipping & Thresholds
        </button>
        <button type="button" class="settings-tab-btn set-tab-btn ${activeTab === 'policies' ? 'active' : ''}" data-tab="policies">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><line x1="10" y1="9" x2="8" y2="9"/></svg>
          Legal Policies
        </button>
        <button type="button" class="settings-tab-btn set-tab-btn ${activeTab === 'audit' ? 'active' : ''}" data-tab="audit">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/></svg>
          Revision History
        </button>
        <button type="button" class="settings-tab-btn set-tab-btn ${activeTab === 'preferences' ? 'active' : ''}" data-tab="preferences">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/></svg>
          Admin Preferences
        </button>
      </div>

      <!-- Status Alert Banner -->
      <div id="settings-alert" style="display: none; margin-bottom: 20px; padding: 12px 16px; border-radius: var(--admin-radius-control); font-size: 0.8125rem;"></div>

      <!-- Tab Content Area -->
      <div class="settings-tab-body set-tab-body">
        ${renderActiveTab()}
      </div>
    `;

    attachEvents();
  }

  function renderActiveTab() {
    if (!currentSettings || !currentPreferences) {
      return `
        <div style="padding: 60px 20px; text-align: center; color: rgba(255, 255, 255, 0.45);">
          <div class="spinner" style="margin: 0 auto 16px auto; width: 28px; height: 28px; border-width: 2px;"></div>
          Loading store configuration...
        </div>
      `;
    }

    switch (activeTab) {
      case 'storefront':
        return renderStorefrontTab();
      case 'shipping':
        return renderShippingTab();
      case 'policies':
        return renderPoliciesTab();
      case 'audit':
        return renderAuditTab();
      case 'preferences':
        return renderPreferencesTab();
      default:
        return '';
    }
  }

  function renderStorefrontTab() {
    const s = currentSettings;
    const accent = s.accent_color || '#10B981';
    const font = s.font_family || 'Outfit, sans-serif';
    const radiusMap = { none: '0px', sm: '4px', md: '8px', lg: '12px', full: '999px' };
    const radiusVal = radiusMap[s.border_radius] || '8px';

    return `
      <form id="form-storefront-settings" style="display: flex; flex-direction: column; gap: 20px;">
        <div class="set-grid-2col">
          <!-- Left Column: Form Controls -->
          <div style="display: flex; flex-direction: column; gap: 16px;">
            <!-- Brand Identity Card -->
            <div class="set-card">
              <div class="set-card-header">
                <h3 class="set-card-title">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: #10B981;"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>
                  Brand Identity & Theme Tokens
                </h3>
              </div>
              
              <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px;">
                <div>
                  <label style="display: block; font-size: 0.75rem; color: var(--admin-text-secondary); margin-bottom: 6px;">Brand Name</label>
                  <input type="text" id="input-brand-name" value="${escapeHtml(s.brand_name || 'AlphaZee')}" class="admin-input" style="width: 100%;" required>
                </div>
                <div>
                  <label style="display: block; font-size: 0.75rem; color: var(--admin-text-secondary); margin-bottom: 6px;">Store Tagline</label>
                  <input type="text" id="input-tagline" value="${escapeHtml(s.tagline || '')}" class="admin-input" style="width: 100%;" placeholder="e.g. Curated Contemporary Silhouettes">
                </div>
                <div>
                  <label style="display: block; font-size: 0.75rem; color: var(--admin-text-secondary); margin-bottom: 6px;">Primary Accent Color</label>
                  <div style="display: flex; align-items: center; gap: 8px;">
                    <input type="color" id="input-accent-color-picker" value="${accent}" style="width: 36px; height: 36px; border: none; border-radius: 6px; cursor: pointer; background: transparent; padding: 0;">
                    <input type="text" id="input-accent-color" value="${escapeHtml(accent)}" class="admin-input" style="flex: 1; font-family: monospace; font-size: 0.8125rem;" pattern="^#[0-9a-fA-F]{6}$" required>
                  </div>
                </div>
                <div>
                  <label style="display: block; font-size: 0.75rem; color: var(--admin-text-secondary); margin-bottom: 6px;">Storefront Typography</label>
                  <select id="select-font-family" class="admin-input" style="width: 100%;">
                    <option value="Outfit, sans-serif" ${s.font_family === 'Outfit, sans-serif' ? 'selected' : ''}>Outfit (Geometric Premium)</option>
                    <option value="Inter, sans-serif" ${s.font_family === 'Inter, sans-serif' ? 'selected' : ''}>Inter (Modern Sans)</option>
                    <option value="Playfair Display, serif" ${s.font_family === 'Playfair Display, serif' ? 'selected' : ''}>Playfair Display (Editorial Serif)</option>
                    <option value="System-UI, sans-serif" ${s.font_family === 'System-UI, sans-serif' ? 'selected' : ''}>System UI Default</option>
                  </select>
                </div>
                <div>
                  <label style="display: block; font-size: 0.75rem; color: var(--admin-text-secondary); margin-bottom: 6px;">Button Border Radius</label>
                  <select id="select-border-radius" class="admin-input" style="width: 100%;">
                    <option value="none" ${s.border_radius === 'none' ? 'selected' : ''}>Sharp (0px)</option>
                    <option value="sm" ${s.border_radius === 'sm' ? 'selected' : ''}>Slight Curve (4px)</option>
                    <option value="md" ${s.border_radius === 'md' ? 'selected' : ''}>Modern Medium (8px)</option>
                    <option value="lg" ${s.border_radius === 'lg' ? 'selected' : ''}>Rounded Large (12px)</option>
                    <option value="full" ${s.border_radius === 'full' ? 'selected' : ''}>Pill / Fully Rounded</option>
                  </select>
                </div>
                <div>
                  <label style="display: block; font-size: 0.75rem; color: var(--admin-text-secondary); margin-bottom: 6px;">Layout Spacing Density</label>
                  <select id="select-spacing-density" class="admin-input" style="width: 100%;">
                    <option value="compact" ${s.spacing_density === 'compact' ? 'selected' : ''}>Compact (High density)</option>
                    <option value="comfortable" ${s.spacing_density === 'comfortable' ? 'selected' : ''}>Comfortable (Balanced)</option>
                    <option value="spacious" ${s.spacing_density === 'spacious' ? 'selected' : ''}>Spacious (Airy Editorial)</option>
                  </select>
                </div>
              </div>
            </div>

            <!-- Announcement Bar Section -->
            <div class="set-card">
              <div class="set-card-header">
                <h3 class="set-card-title">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: #38BDF8;"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                  Store Announcement Banner
                </h3>
                <label style="display: flex; align-items: center; gap: 8px; font-size: 0.75rem; color: var(--admin-text-secondary); cursor: pointer;">
                  <input type="checkbox" id="input-announcement-enabled" ${s.announcement_banner_enabled ? 'checked' : ''} style="cursor: pointer; width: 15px; height: 15px;">
                  <span>Active on storefront</span>
                </label>
              </div>

              <div style="display: flex; flex-direction: column; gap: 12px;">
                <div>
                  <label style="display: block; font-size: 0.75rem; color: var(--admin-text-secondary); margin-bottom: 6px;">Announcement Text</label>
                  <input type="text" id="input-announcement-text" value="${escapeHtml(s.announcement_banner_text || '')}" class="admin-input" style="width: 100%;" placeholder="e.g. Complimentary shipping across Pakistan on orders over PKR 5,000" required>
                </div>
                <div>
                  <label style="display: block; font-size: 0.75rem; color: var(--admin-text-secondary); margin-bottom: 6px;">Banner Link (optional, e.g. #featured or /track)</label>
                  <input type="text" id="input-announcement-link" value="${escapeHtml(s.announcement_banner_link || '')}" class="admin-input" style="width: 100%;" placeholder="#featured">
                </div>
                <!-- Hidden compatibility anchor for legacy preview tests if any -->
                <div id="preview-announcement-bar" style="display: none;">${escapeHtml(s.announcement_banner_text || '')}</div>
              </div>
            </div>
          </div>

          <!-- Right Column: Interactive Live Mockup Preview Card -->
          <div class="set-preview-mockup">
            <div class="set-mockup-browser-bar">
              <span class="set-mockup-dot red"></span>
              <span class="set-mockup-dot yellow"></span>
              <span class="set-mockup-dot green"></span>
              <span class="set-mockup-url">alphazee.tech</span>
            </div>

            <!-- Live Announcement Header -->
            <div id="mockup-announcement" class="set-mockup-announcement" style="background: ${accent}; color: #ffffff; display: ${s.announcement_banner_enabled ? 'block' : 'none'};">
              ${escapeHtml(s.announcement_banner_text || 'Complimentary delivery nationwide')}
            </div>

            <!-- Live Store Header -->
            <div class="set-mockup-header">
              <span id="mockup-brand" class="set-mockup-brand" style="font-family: ${font};">${escapeHtml(s.brand_name || 'AlphaZee')}</span>
              <div style="display: flex; gap: 10px; font-size: 0.6875rem; color: rgba(255, 255, 255, 0.6);">
                <span>Catalog</span>
                <span>Collections</span>
                <span>Track</span>
              </div>
            </div>

            <!-- Mockup Body Content -->
            <div class="set-mockup-body">
              <span id="mockup-tagline" class="set-mockup-tagline">${escapeHtml(s.tagline || 'Curated Contemporary Silhouettes')}</span>
              
              <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: ${radiusVal}; padding: 14px; margin-top: 4px;">
                <div style="font-size: 0.8125rem; font-weight: 600; color: #fff; margin-bottom: 4px; font-family: ${font};" id="mockup-specimen-title">Contemporary Tailoring Specimen</div>
                <div style="font-size: 0.6875rem; color: rgba(255, 255, 255, 0.5); line-height: 1.4;">Precision crafted apparel cut from heavyweight luxury cotton with exact seam allowances.</div>
                
                <button type="button" id="mockup-sample-btn" class="set-mockup-cta-sample" style="background: ${accent}; border-radius: ${radiusVal}; font-family: ${font};">
                  Explore Capsule
                </button>
              </div>

              <!-- Live Token Chips -->
              <div class="set-mockup-token-badges">
                <span id="mockup-chip-font" class="set-mockup-chip">Font: ${s.font_family?.split(',')[0] || 'Outfit'}</span>
                <span id="mockup-chip-radius" class="set-mockup-chip">Radius: ${s.border_radius || 'md'}</span>
                <span id="mockup-chip-accent" class="set-mockup-chip">Accent: ${accent}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Sticky Executive Action Bar (Rule 2: Compact Semantic Icons & Micro-tooltips) -->
        <div class="set-action-bar">
          <div style="display: flex; align-items: center; gap: 10px; flex: 1; max-width: 360px;">
            <input type="text" id="input-change-reason" placeholder="Audit change reason (e.g. Winter Campaign Refresh)" class="admin-input" style="width: 100%; font-size: 0.8125rem;">
          </div>
          <div class="set-action-group">
            <button type="submit" id="btn-save-storefront" class="set-action-btn is-save" data-tooltip="Save storefront branding tokens & banner" aria-label="Save storefront branding settings" title="Save storefront settings">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
            </button>
          </div>
        </div>
      </form>
    `;
  }

  function renderShippingTab() {
    const s = currentSettings;
    const stdPkr = s.standard_shipping_fee_minor / 100;
    const freePkr = s.free_shipping_threshold_minor ? s.free_shipping_threshold_minor / 100 : '';

    return `
      <form id="form-shipping-settings" style="display: flex; flex-direction: column; gap: 20px;">
        <!-- Verification Banner -->
        <div class="set-verify-banner">
          <input id="confirm-shipping-rules" type="checkbox" ${s.shipping_rules_configured ? 'checked' : ''} style="width: 17px; height: 17px; cursor: pointer;">
          <label for="confirm-shipping-rules" style="font-size: 0.8125rem; font-weight: 500; color: #fff; cursor: pointer; margin: 0; display: flex; align-items: center; gap: 8px;">
            <span>Customer delivery commitments verified for live storefront dispatch.</span>
            <span style="font-size: 0.6875rem; padding: 2px 8px; border-radius: 4px; background: rgba(16, 185, 129, 0.15); color: #34D399;">AlphaZee bears 100% RTO</span>
          </label>
        </div>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px;">
          <!-- Shipping Rates Card -->
          <div class="set-card">
            <div class="set-card-header">
              <h3 class="set-card-title">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: #10B981;"><rect width="14" height="10" x="1" y="5" rx="2"/><circle cx="5.5" cy="17.5" r="2.5"/><circle cx="17.5" cy="17.5" r="2.5"/><path d="M15 8h4.28a2 2 0 0 1 1.79 1.11l2.09 4.18A2 2 0 0 1 23 14.18V17h-3"/><path d="M1 12h14"/></svg>
                Coverage & Shipping Rates
              </h3>
            </div>
            
            <div style="display: flex; flex-direction: column; gap: 14px;">
              <div>
                <label style="display: block; font-size: 0.75rem; color: var(--admin-text-secondary); margin-bottom: 6px;">Coverage Area</label>
                <input type="text" id="input-shipping-coverage" value="${escapeHtml(s.shipping_coverage_area || 'All Pakistan')}" class="admin-input" style="width: 100%;" required>
              </div>
              <div>
                <label style="display: block; font-size: 0.75rem; color: var(--admin-text-secondary); margin-bottom: 6px;">Standard Delivery Fee (PKR)</label>
                <input type="number" id="input-shipping-fee-pkr" value="${stdPkr}" min="0" step="10" class="admin-input" style="width: 100%; font-variant-numeric: tabular-nums;" required>
              </div>
              <div>
                <label style="display: block; font-size: 0.75rem; color: var(--admin-text-secondary); margin-bottom: 6px;">Free Delivery Threshold (PKR, leave empty for none)</label>
                <input type="number" id="input-free-shipping-pkr" value="${freePkr}" min="0" step="100" class="admin-input" style="width: 100%; font-variant-numeric: tabular-nums;" placeholder="e.g. 5000">
              </div>
            </div>
          </div>

          <!-- Operational Alert Thresholds Card -->
          <div class="set-card">
            <div class="set-card-header">
              <h3 class="set-card-title">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: #F59E0B;"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                Inventory Alert Thresholds
              </h3>
            </div>
            
            <div style="display: flex; flex-direction: column; gap: 14px;">
              <div>
                <label style="display: block; font-size: 0.75rem; color: var(--admin-text-secondary); margin-bottom: 6px;">Low-Stock Warning (Units)</label>
                <input type="number" id="input-low-stock-threshold" value="${s.low_stock_threshold}" min="0" step="1" class="admin-input" style="width: 100%; font-variant-numeric: tabular-nums;" required>
                <p class="set-card-desc">SKUs at or below this sellable count trigger inventory warning badges.</p>
              </div>
              <div>
                <label style="display: block; font-size: 0.75rem; color: var(--admin-text-secondary); margin-bottom: 6px;">Stock Staleness Period (Days)</label>
                <input type="number" id="input-staleness-threshold" value="${s.stock_staleness_threshold_days}" min="1" step="1" class="admin-input" style="width: 100%; font-variant-numeric: tabular-nums;" required>
                <p class="set-card-desc">Unverified vendor stock records trigger verification alerts after N days.</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Action Bar (Rule 2) -->
        <div class="set-action-bar">
          <span style="font-size: 0.75rem; color: var(--admin-text-muted);">Configures authoritative logistics and inventory thresholds across the store.</span>
          <div class="set-action-group">
            <button type="submit" id="btn-save-shipping" class="set-action-btn is-save" data-tooltip="Save shipping rates & operational thresholds" aria-label="Save logistics and thresholds" title="Save shipping settings">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
            </button>
          </div>
        </div>
      </form>
    `;
  }

  function renderPoliciesTab() {
    const s = currentSettings;
    const policyMap = {
      delivery: {
        title: 'Delivery & Shipping Policy',
        content: s.delivery_policy_content || '',
        status: s.delivery_policy_status,
        publishedAt: s.delivery_policy_published_at,
      },
      return: {
        title: 'Return & Exchange Policy',
        content: s.return_policy_content || '',
        status: s.return_policy_status,
        publishedAt: s.return_policy_published_at,
      },
      terms: {
        title: 'Terms of Service',
        content: s.terms_policy_content || '',
        status: s.terms_policy_status,
        publishedAt: s.terms_policy_published_at,
      },
      privacy: {
        title: 'Privacy Policy',
        content: s.privacy_policy_content || '',
        status: s.privacy_policy_status,
        publishedAt: s.privacy_policy_published_at,
      },
    };

    const pol = policyMap[activePolicy];
    const isPublished = pol.status === 'published';

    return `
      <div style="display: flex; flex-direction: column; gap: 16px;">
        <!-- Policy Switcher Sub-nav -->
        <div class="set-policy-pills">
          ${Object.keys(policyMap).map(k => {
            const p = policyMap[k];
            const active = k === activePolicy;
            const pub = p.status === 'published';
            return `
              <button type="button" class="btn sub-policy-tab set-policy-pill ${active ? 'active' : ''}" data-policy="${k}">
                <span class="set-status-dot ${pub ? 'is-pub' : 'is-draft'}"></span>
                <span>${escapeHtml(p.title)}</span>
                <span style="font-size: 0.6875rem; padding: 1px 6px; border-radius: 4px; font-family: monospace; ${pub ? 'background: rgba(16, 185, 129, 0.15); color: #34D399;' : 'background: rgba(245, 158, 11, 0.15); color: #FBBF24;'}">
                  ${p.status}
                </span>
              </button>
            `;
          }).join('')}
        </div>

        <!-- Policy Editor Card -->
        <div class="set-card">
          <div class="set-card-header">
            <div>
              <h3 class="set-card-title">${escapeHtml(pol.title)}</h3>
              <div style="font-size: 0.75rem; color: var(--admin-text-muted); margin-top: 2px;">
                Status: <strong style="color: ${isPublished ? '#34D399' : '#FBBF24'}; text-transform: capitalize;">${pol.status}</strong>
                ${pol.publishedAt ? ` • Last published: ${new Date(pol.publishedAt).toLocaleString()}` : ''}
              </div>
            </div>

            <!-- Compact Icon Actions for Policies (Rule 2) -->
            <div class="set-action-group">
              ${isPublished ? `
                <button type="button" id="btn-unpublish-policy" class="set-action-btn is-draft" data-tooltip="Revert policy to draft" aria-label="Revert policy to draft" title="Revert to draft">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><line x1="9" y1="15" x2="15" y2="15"/></svg>
                </button>
              ` : `
                <button type="button" id="btn-publish-policy" class="set-action-btn is-publish" data-tooltip="Publish policy to live storefront" aria-label="Publish policy to storefront" title="Publish to storefront">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/><polyline points="16 16 12 12 8 16"/></svg>
                </button>
              `}
              <button type="button" id="btn-save-policy-draft" class="set-action-btn is-save" data-tooltip="Save policy draft changes" aria-label="Save policy draft" title="Save draft">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
              </button>
            </div>
          </div>

          <div>
            <textarea id="textarea-policy-content" class="admin-input" style="width: 100%; min-height: 280px; font-family: monospace; font-size: 0.8125rem; line-height: 1.6; padding: 14px;" placeholder="Draft legal terms, shipping commitments, or return guarantees in Markdown or Plain Text...">${escapeHtml(pol.content)}</textarea>
          </div>
        </div>
      </div>
    `;
  }

  function renderAuditTab() {
    return `
      <div class="set-card">
        <div class="set-card-header">
          <h3 class="set-card-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: #38BDF8;"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/></svg>
            Configuration Revision Ledger
          </h3>
          <span style="font-size: 0.75rem; color: var(--admin-text-muted);">${auditLogs.length} revisions recorded</span>
        </div>
        
        ${auditLogs.length === 0 ? `
          <div style="padding: 40px 20px; text-align: center; color: var(--admin-text-muted);">
            No configuration alterations recorded yet. Initial baseline is Revision 1.
          </div>
        ` : `
          <!-- Desktop Table View -->
          <div class="set-table-wrap set-table-desktop">
            <table class="admin-table">
              <thead>
                <tr>
                  <th style="width: 100px;">Revision</th>
                  <th style="width: 180px;">Timestamp</th>
                  <th>Change Reason</th>
                  <th>Modified Fields</th>
                </tr>
              </thead>
              <tbody>
                ${auditLogs.map(log => `
                  <tr>
                    <td><span class="set-version-tag">v${log.version}</span></td>
                    <td style="color: var(--admin-text-secondary); font-variant-numeric: tabular-nums; font-size: 0.75rem;">${new Date(log.created_at).toLocaleString()}</td>
                    <td style="color: #ffffff; font-weight: 500;">${escapeHtml(log.change_reason || '—')}</td>
                    <td class="set-audit-fields">
                      ${Object.keys(log.changed_fields || {}).map(f => `<span style="display: inline-block; padding: 2px 6px; margin: 1px; border-radius: 3px; background: rgba(255, 255, 255, 0.05);">${escapeHtml(f)}</span>`).join('') || '—'}
                    </td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>

          <!-- Mobile Cards View (Rule 1: Zero horizontal scroll) -->
          <div class="set-cards-mobile">
            ${auditLogs.map(log => `
              <div class="set-audit-card">
                <div class="set-audit-header">
                  <span class="set-version-tag">Revision v${log.version}</span>
                  <span class="set-audit-time">${new Date(log.created_at).toLocaleDateString()}</span>
                </div>
                <div class="set-audit-reason">${escapeHtml(log.change_reason || 'Configuration update')}</div>
                <div class="set-audit-fields">
                  ${Object.keys(log.changed_fields || {}).join(', ') || '—'}
                </div>
              </div>
            `).join('')}
          </div>
        `}
      </div>
    `;
  }

  const NAV_METADATA = {
    overview: { name: 'Store Overview', desc: 'Financial KPIs & active orders summary' },
    products: { name: 'Products & Catalog', desc: 'Catalog management, pricing & stock' },
    collections: { name: 'Collections', desc: 'Grouping and sorting product collections' },
    hero: { name: 'Homepage Hero', desc: 'Slide sequencing, video & hero playlists' },
    media: { name: 'Media Library', desc: 'Durable image & video asset repository' },
    inventory: { name: 'Inventory & Stock', desc: 'Physical balances, holds & adjustments' },
    suppliers: { name: 'Suppliers & Vendors', desc: 'Agreements, costs & vendor credentials' },
    orders: { name: 'Orders & Payments', desc: 'Fulfillment, bank verify & courier dispatch' },
    returns: { name: 'Returns & Refunds', desc: 'Size exchanges, inspections & refunds' },
    coupons: { name: 'Coupons & Promos', desc: 'Discount vouchers, fixed & percent promos' },
    expenses: { name: 'Business Expenses', desc: 'Freight, packaging & overhead ledgers' },
    analytics: { name: 'Reports & Analytics', desc: 'P&L statements, COGS, attribution & export' },
    settings: { name: 'Store Settings', desc: 'Branding, shipping policies & console setup' },
  };

  const CARD_METADATA = {
    sales: { title: 'Delivered Sales', desc: 'Gross delivered revenue & realized sales' },
    orders: { title: 'Total Orders', desc: 'Total order volume and pending action count' },
    inventory: { title: 'Active Catalog SKUs', desc: 'Total active variants linked to suppliers' },
    low_stock: { title: 'Low Stock Alerts', desc: 'Variants with ≤ 2 units available to sell' },
  };

  function renderPreferencesTab() {
    const p = currentPreferences;
    const navItems = p.nav_order || [];
    const dashboardCards = p.dashboard_layout?.cards || [];

    return `
      <form id="form-admin-preferences" style="display: flex; flex-direction: column; gap: 20px;">
        <!-- Theme & Display Density Card -->
        <div class="set-card">
          <div class="set-card-header">
            <h3 class="set-card-title">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: #10B981;"><line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/></svg>
              Personal Console Environment
            </h3>
          </div>
          <p class="set-card-desc" style="margin-bottom: 14px;">
            Personal preferences are scoped to your authenticated owner account without altering public storefront attributes.
          </p>

          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px;">
            <div>
              <label style="display: block; font-size: 0.75rem; color: var(--admin-text-secondary); margin-bottom: 6px;">Interface Theme</label>
              <select id="select-pref-theme" class="admin-input" style="width: 100%;">
                <option value="system" ${p.theme === 'system' ? 'selected' : ''}>System Default</option>
                <option value="dark" ${p.theme === 'dark' ? 'selected' : ''}>OLED Dark</option>
                <option value="light" ${p.theme === 'light' ? 'selected' : ''}>Clean Light</option>
              </select>
            </div>
            <div>
              <label style="display: block; font-size: 0.75rem; color: var(--admin-text-secondary); margin-bottom: 6px;">Table Display Density</label>
              <select id="select-pref-density" class="admin-input" style="width: 100%;">
                <option value="comfortable" ${p.table_density === 'comfortable' ? 'selected' : ''}>Comfortable (Standard)</option>
                <option value="compact" ${p.table_density === 'compact' ? 'selected' : ''}>Compact (High density)</option>
              </select>
            </div>
            <div>
              <label style="display: block; font-size: 0.75rem; color: var(--admin-text-secondary); margin-bottom: 6px;">Default Analytics Period</label>
              <select id="select-pref-date" class="admin-input" style="width: 100%;">
                <option value="today" ${p.default_date_range === 'today' ? 'selected' : ''}>Today</option>
                <option value="this_month" ${p.default_date_range === 'this_month' ? 'selected' : ''}>This Month</option>
                <option value="last_month" ${p.default_date_range === 'last_month' ? 'selected' : ''}>Last Month</option>
                <option value="all_time" ${p.default_date_range === 'all_time' ? 'selected' : ''}>All Time</option>
              </select>
            </div>
          </div>
        </div>

        <!-- Sidebar Navigation Order Fieldset -->
        <fieldset class="settings-card set-card" style="padding: 20px;">
          <legend style="display: flex; align-items: center; gap: 8px; font-size: 0.9375rem; font-weight: 500; color: #fff; padding: 0 4px;">
            Sidebar Navigation Ordering
          </legend>
          <p class="set-card-desc" style="margin: 4px 0 16px 0;">
            Assign numeric display priority (1–20) for each operational section to tailor the admin navigation to your daily workflow.
          </p>
          <div class="pref-items-grid set-reorder-list">
            ${navItems.map((id, index) => {
              const meta = NAV_METADATA[id] || { name: id, desc: `Section ${id}` };
              return `
                <div class="pref-item-card set-reorder-item">
                  <div class="pref-item-info">
                    <div class="pref-item-text">
                      <span class="pref-item-name set-reorder-title">${escapeHtml(meta.name)}</span>
                      <p class="pref-item-desc set-reorder-desc">${escapeHtml(meta.desc)}</p>
                    </div>
                  </div>
                  <div style="display: flex; align-items: center; gap: 6px; flex-shrink: 0;">
                    <label style="font-size: 0.75rem; color: var(--admin-text-muted);">#</label>
                    <input class="pref-nav-position pref-number-input admin-input" data-id="${escapeHtml(id)}" type="number" min="1" max="20" value="${index + 1}" required aria-label="${escapeHtml(meta.name)} sidebar position" style="width: 44px; padding: 4px 6px; text-align: center; font-variant-numeric: tabular-nums;">
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        </fieldset>

        <!-- Overview Dashboard Cards Fieldset -->
        <fieldset class="settings-card set-card" style="padding: 20px;">
          <legend style="display: flex; align-items: center; gap: 8px; font-size: 0.9375rem; font-weight: 500; color: #fff; padding: 0 4px;">
            Store Overview KPI Metrics
          </legend>
          <p class="set-card-desc" style="margin: 4px 0 16px 0;">
            Toggle visibility and sequence (1–4) for top-level operational cards on your Store Overview dashboard.
          </p>
          <div style="display: flex; flex-direction: column; gap: 8px;">
            ${dashboardCards.map((card, index) => {
              const meta = CARD_METADATA[card.id] || { title: card.id, desc: `KPI card ${card.id}` };
              return `
                <div class="pref-card-row" style="display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; background: #1A1D24; border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 6px;">
                  <div class="pref-card-left" style="display: flex; align-items: center; gap: 10px;">
                    <input type="checkbox" class="pref-card-visible" data-id="${escapeHtml(card.id)}" id="pref-card-${escapeHtml(card.id)}" ${card.visible ? 'checked' : ''} style="width: 16px; height: 16px; cursor: pointer;">
                    <label for="pref-card-${escapeHtml(card.id)}" class="pref-card-info" style="cursor: pointer; margin: 0;">
                      <span class="pref-card-title" style="font-size: 0.8125rem; font-weight: 500; color: #fff;">${escapeHtml(meta.title)}</span>
                      <p class="pref-card-desc" style="font-size: 0.6875rem; color: rgba(255, 255, 255, 0.45); margin: 0;">${escapeHtml(meta.desc)}</p>
                    </label>
                  </div>
                  <div style="display: flex; align-items: center; gap: 6px; flex-shrink: 0;">
                    <label for="pos-${escapeHtml(card.id)}" style="font-size: 0.75rem; color: var(--admin-text-muted);">#</label>
                    <input id="pos-${escapeHtml(card.id)}" class="pref-card-position pref-number-input admin-input" data-id="${escapeHtml(card.id)}" aria-label="${escapeHtml(meta.title)} position" type="number" min="1" max="4" value="${index + 1}" required style="width: 44px; padding: 4px 6px; text-align: center; font-variant-numeric: tabular-nums;">
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        </fieldset>

        <!-- Submit & Reset Actions (Rule 2: Compact Semantic Icons & Micro-tooltips) -->
        <div class="set-action-bar">
          <div class="set-action-group">
            <button type="button" id="btn-reset-preferences" class="set-action-btn is-danger" data-tooltip="Reset personal preferences to system defaults" aria-label="Reset preferences to defaults" title="Reset preferences">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>
            </button>
          </div>
          <div class="set-action-group">
            <button type="submit" id="btn-save-preferences" class="set-action-btn is-save" data-tooltip="Save personal console preferences" aria-label="Save preferences" title="Save preferences">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
            </button>
          </div>
        </div>
      </form>
    `;
  }

  function showAlert(message, type = 'success') {
    const alert = container.querySelector('#settings-alert');
    if (!alert) return;
    alert.style.display = 'block';
    if (type === 'success') {
      alert.style.background = 'rgba(16, 185, 129, 0.15)';
      alert.style.color = '#34D399';
      alert.style.border = '1px solid rgba(16, 185, 129, 0.3)';
    } else {
      alert.style.background = 'rgba(239, 68, 68, 0.15)';
      alert.style.color = '#F87171';
      alert.style.border = '1px solid rgba(239, 68, 68, 0.3)';
    }
    alert.textContent = message;
    setTimeout(() => {
      alert.style.display = 'none';
    }, 4000);
  }

  function attachEvents() {
    // Tab switching
    container.querySelectorAll('.settings-tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        activeTab = btn.dataset.tab;
        if (activeTab === 'audit') {
          loadAuditLogs();
        } else {
          render();
        }
      });
    });

    // Color picker sync & Mockup sync
    const picker = container.querySelector('#input-accent-color-picker');
    const hexInput = container.querySelector('#input-accent-color');
    const previewBar = container.querySelector('#preview-announcement-bar');
    const mockupAnnounce = container.querySelector('#mockup-announcement');
    const mockupSampleBtn = container.querySelector('#mockup-sample-btn');
    const mockupChipAccent = container.querySelector('#mockup-chip-accent');

    function updateAccent(color) {
      if (previewBar) previewBar.style.background = color;
      if (mockupAnnounce) mockupAnnounce.style.background = color;
      if (mockupSampleBtn) mockupSampleBtn.style.background = color;
      if (mockupChipAccent) mockupChipAccent.textContent = `Accent: ${color}`;
    }

    if (picker && hexInput) {
      picker.addEventListener('input', (e) => {
        hexInput.value = e.target.value;
        updateAccent(e.target.value);
      });
      hexInput.addEventListener('input', (e) => {
        if (/^#[0-9a-fA-F]{6}$/.test(e.target.value)) {
          picker.value = e.target.value;
          updateAccent(e.target.value);
        }
      });
    }

    // Announcement text & enabled toggle sync
    const announceInput = container.querySelector('#input-announcement-text');
    const announceToggle = container.querySelector('#input-announcement-enabled');
    if (announceInput && mockupAnnounce) {
      announceInput.addEventListener('input', (e) => {
        const val = e.target.value || 'Complimentary delivery nationwide';
        if (previewBar) previewBar.textContent = val;
        mockupAnnounce.textContent = val;
      });
    }
    if (announceToggle && mockupAnnounce) {
      announceToggle.addEventListener('change', (e) => {
        mockupAnnounce.style.display = e.target.checked ? 'block' : 'none';
      });
    }

    // Brand Name & Tagline sync
    const brandInput = container.querySelector('#input-brand-name');
    const taglineInput = container.querySelector('#input-tagline');
    const mockupBrand = container.querySelector('#mockup-brand');
    const mockupTagline = container.querySelector('#mockup-tagline');
    if (brandInput && mockupBrand) {
      brandInput.addEventListener('input', (e) => {
        mockupBrand.textContent = e.target.value || 'AlphaZee';
      });
    }
    if (taglineInput && mockupTagline) {
      taglineInput.addEventListener('input', (e) => {
        mockupTagline.textContent = e.target.value || 'Curated Contemporary Silhouettes';
      });
    }

    // Typography select sync
    const fontSelect = container.querySelector('#select-font-family');
    const mockupSpecimenTitle = container.querySelector('#mockup-specimen-title');
    const mockupChipFont = container.querySelector('#mockup-chip-font');
    if (fontSelect) {
      fontSelect.addEventListener('change', (e) => {
        const val = e.target.value;
        if (mockupBrand) mockupBrand.style.fontFamily = val;
        if (mockupSpecimenTitle) mockupSpecimenTitle.style.fontFamily = val;
        if (mockupSampleBtn) mockupSampleBtn.style.fontFamily = val;
        if (mockupChipFont) mockupChipFont.textContent = `Font: ${val.split(',')[0]}`;
      });
    }

    // Radius select sync
    const radiusSelect = container.querySelector('#select-border-radius');
    const mockupChipRadius = container.querySelector('#mockup-chip-radius');
    const radiusMap = { none: '0px', sm: '4px', md: '8px', lg: '12px', full: '999px' };
    if (radiusSelect) {
      radiusSelect.addEventListener('change', (e) => {
        const val = e.target.value;
        const px = radiusMap[val] || '8px';
        if (mockupSampleBtn) mockupSampleBtn.style.borderRadius = px;
        if (mockupChipRadius) mockupChipRadius.textContent = `Radius: ${val}`;
      });
    }

    // Save Storefront Settings Form
    const formStorefront = container.querySelector('#form-storefront-settings');
    if (formStorefront) {
      formStorefront.addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
          const payload = {
            brand_name: container.querySelector('#input-brand-name').value.trim(),
            tagline: container.querySelector('#input-tagline').value.trim(),
            announcement_banner_enabled: container.querySelector('#input-announcement-enabled').checked,
            announcement_banner_text: container.querySelector('#input-announcement-text').value.trim(),
            announcement_banner_link: container.querySelector('#input-announcement-link').value.trim() || null,
            accent_color: container.querySelector('#input-accent-color').value.trim(),
            font_family: container.querySelector('#select-font-family').value,
            border_radius: container.querySelector('#select-border-radius').value,
            spacing_density: container.querySelector('#select-spacing-density').value,
            change_reason: container.querySelector('#input-change-reason').value.trim() || undefined,
          };
          payload.expected_version = currentSettings.version;
          const res = await updateAdminStoreSettings(payload);
          currentSettings = res;
          showAlert(`Storefront settings saved (revision v${res.version})`);
          render();
        } catch (err) {
          showAlert(err.message || 'Failed to update store settings', 'error');
        }
      });
    }

    // Save Shipping Form
    const formShipping = container.querySelector('#form-shipping-settings');
    if (formShipping) {
      formShipping.addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
          const feePkr = parseFloat(container.querySelector('#input-shipping-fee-pkr').value) || 0;
          const freePkrInput = container.querySelector('#input-free-shipping-pkr').value.trim();
          const freePkr = freePkrInput ? parseFloat(freePkrInput) : null;

          const payload = {
            shipping_coverage_area: container.querySelector('#input-shipping-coverage').value.trim(),
            standard_shipping_fee_minor: Math.round(feePkr * 100),
            shipping_rules_configured: container.querySelector('#confirm-shipping-rules').checked,
            expected_version: currentSettings.version,
            free_shipping_threshold_minor: freePkr !== null ? Math.round(freePkr * 100) : null,
            low_stock_threshold: parseInt(container.querySelector('#input-low-stock-threshold').value, 10),
            stock_staleness_threshold_days: parseInt(container.querySelector('#input-staleness-threshold').value, 10),
          };
          payload.expected_version = currentSettings.version;
          const res = await updateAdminStoreSettings(payload);
          currentSettings = res;
          showAlert(`Logistics and operational thresholds updated (revision v${res.version})`);
          render();
        } catch (err) {
          showAlert(err.message || 'Failed to update shipping settings', 'error');
        }
      });
    }

    // Policy Sub-tabs
    container.querySelectorAll('.sub-policy-tab').forEach(btn => {
      btn.addEventListener('click', () => {
        activePolicy = btn.dataset.policy;
        render();
      });
    });

    // Save Policy Draft
    const btnSaveDraft = container.querySelector('#btn-save-policy-draft');
    if (btnSaveDraft) {
      btnSaveDraft.addEventListener('click', async () => {
        const text = container.querySelector('#textarea-policy-content').value;
        const key = `${activePolicy}_policy_content`;
        try {
          const res = await updateAdminStoreSettings({
            [key]: text,
            change_reason: `Update ${activePolicy} policy draft content`,
          });
          currentSettings = res;
          showAlert(`${activePolicy} policy draft saved`);
          render();
        } catch (err) {
          showAlert(err.message || 'Failed to save policy draft', 'error');
        }
      });
    }

    // Publish Policy
    const btnPublish = container.querySelector('#btn-publish-policy');
    if (btnPublish) {
      btnPublish.addEventListener('click', async () => {
        const text = container.querySelector('#textarea-policy-content').value;
        if (!text || !text.trim()) {
          showAlert('Cannot publish an empty policy. Please write terms first.', 'error');
          return;
        }
        try {
          const key = `${activePolicy}_policy_content`;
          await updateAdminStoreSettings({ [key]: text });
          const res = await publishStorePolicy(activePolicy, true);
          currentSettings = res;
          showAlert(`${activePolicy} policy published to storefront`);
          render();
        } catch (err) {
          showAlert(err.message || 'Failed to publish policy', 'error');
        }
      });
    }

    // Unpublish Policy
    const btnUnpublish = container.querySelector('#btn-unpublish-policy');
    if (btnUnpublish) {
      btnUnpublish.addEventListener('click', async () => {
        try {
          const res = await publishStorePolicy(activePolicy, false);
          currentSettings = res;
          showAlert(`${activePolicy} policy reverted to draft`);
          render();
        } catch (err) {
          showAlert(err.message || 'Failed to revert policy', 'error');
        }
      });
    }

    // Admin Preferences Form
    const formPrefs = container.querySelector('#form-admin-preferences');
    if (formPrefs) {
      formPrefs.addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
          const payload = {
            theme: container.querySelector('#select-pref-theme').value,
            table_density: container.querySelector('#select-pref-density').value,
            default_date_range: container.querySelector('#select-pref-date').value,
          };
          const positions = Array.from(container.querySelectorAll('.pref-nav-position'));
          if (new Set(positions.map(input => input.value)).size !== positions.length) throw new Error('Choose unique sidebar positions.');
          payload.nav_order = positions.sort((a,b) => Number(a.value)-Number(b.value)).map(input => input.dataset.id);
          payload.dashboard_layout = { cards: Array.from(container.querySelectorAll('.pref-card-position')).sort((a,b) => Number(a.value)-Number(b.value)).map(input => ({ id: input.dataset.id, visible: Array.from(container.querySelectorAll('.pref-card-visible')).find(check => check.dataset.id === input.dataset.id).checked })) };
          const res = await updateAdminPreferences(payload);
          currentPreferences = res;
          container.dispatchEvent(new CustomEvent("owner-preferences-changed", { bubbles: true }));
          showAlert('Personal interface preferences saved.');
          render();
        } catch (err) {
          showAlert(err.message || 'Failed to update preferences', 'error');
        }
      });
    }

    // Reset Preferences
    const btnResetPrefs = container.querySelector('#btn-reset-preferences');
    if (btnResetPrefs) {
      btnResetPrefs.addEventListener('click', async () => {
        if (!confirm('Reset your console interface preferences back to factory defaults?')) return;
        try {
          const res = await resetAdminPreferences();
          currentPreferences = res;
          container.dispatchEvent(new CustomEvent("owner-preferences-changed", { bubbles: true }));
          showAlert('Preferences reset to system defaults.');
          render();
        } catch (err) {
          showAlert(err.message || 'Failed to reset preferences', 'error');
        }
      });
    }
  }

  async function loadAuditLogs() {
    try {
      auditLogs = await fetchSettingsAuditLogs(50);
      render();
    } catch (err) {
      console.error('Failed to load settings audit logs:', err);
      render();
    }
  }

  async function init() {
    render();
    try {
      const [settings, prefs] = await Promise.all([
        fetchAdminStoreSettings(),
        fetchAdminPreferences(),
      ]);
      currentSettings = settings;
      currentPreferences = prefs;
      render();
    } catch (err) {
      container.innerHTML = `
        <div style="padding: 30px; background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 8px; color: #F87171;">
          Failed to load store settings: ${escapeHtml(err.message)}
        </div>
      `;
    }
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  init();
  return container;
}
