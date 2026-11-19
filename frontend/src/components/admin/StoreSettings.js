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
  let activeTab = 'storefront'; // 'storefront' | 'shipping' | 'policies' | 'faq' | 'audit' | 'preferences'
  let activePolicy = 'delivery'; // 'delivery' | 'return' | 'terms' | 'privacy'
  let faqCategoryFilter = 'all'; // 'all' | 'delivery' | 'payment' | 'returns' | 'sizing' | 'general'
  let faqSearchQuery = '';
  let editingFaqId = null; // null | 'new' | string ID
  let activeMockupFaqIndex = 0;

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
        <button type="button" class="settings-tab-btn set-tab-btn ${activeTab === 'faq' ? 'active' : ''}" data-tab="faq">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
          FAQ & Support
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
      case 'faq':
        return renderFaqTab();
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

            <!-- Storefront Homepage Sections Headings Card -->
            <div class="set-card">
              <div class="set-card-header">
                <h3 class="set-card-title">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: #38BDF8;"><polyline points="4 7 4 4 20 4 20 7"></polyline><line x1="9" y1="20" x2="15" y2="20"></line><line x1="12" y1="4" x2="12" y2="20"></line></svg>
                  Storefront Homepage Sections Copy
                </h3>
                <div class="set-action-group">
                  <button type="submit" id="btn-save-hp-headings" class="set-action-btn is-save" data-tooltip="Save storefront homepage section copy" aria-label="Save section headings" title="Save headings">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
                  </button>
                </div>
              </div>

              <div style="display: flex; flex-direction: column; gap: 14px;">
                <!-- Group 1: Collections Section -->
                <div style="background: rgba(255, 255, 255, 0.02); border: 1px solid var(--admin-border-subtle); border-radius: 6px; padding: 12px; display: flex; flex-direction: column; gap: 10px;">
                  <div style="font-size: 0.75rem; font-weight: 600; color: #fff; text-transform: uppercase; letter-spacing: 0.05em; display: flex; align-items: center; gap: 6px;">
                    <span style="display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #38BDF8;"></span>
                    1. Collections Section (Homepage)
                  </div>
                  <div>
                    <label style="display: block; font-size: 0.75rem; color: var(--admin-text-secondary); margin-bottom: 6px;">Section Heading</label>
                    <input type="text" id="input-hp-col-title" value="${escapeHtml(s.homepage_collections_title || 'Shop by collection')}" class="admin-input" style="width: 100%;" maxlength="100" placeholder="Shop by collection">
                  </div>
                  <div>
                    <label style="display: block; font-size: 0.75rem; color: var(--admin-text-secondary); margin-bottom: 6px;">Section Subtitle / Deck</label>
                    <input type="text" id="input-hp-col-subtitle" value="${escapeHtml(s.homepage_collections_subtitle || 'A place for every part of your wardrobe.')}" class="admin-input" style="width: 100%;" maxlength="255" placeholder="A place for every part of your wardrobe.">
                  </div>
                </div>

                <!-- Group 2: Featured Pieces Section -->
                <div style="background: rgba(255, 255, 255, 0.02); border: 1px solid var(--admin-border-subtle); border-radius: 6px; padding: 12px; display: flex; flex-direction: column; gap: 10px;">
                  <div style="font-size: 0.75rem; font-weight: 600; color: #fff; text-transform: uppercase; letter-spacing: 0.05em; display: flex; align-items: center; gap: 6px;">
                    <span style="display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #10B981;"></span>
                    2. Featured Pieces Section (Homepage)
                  </div>
                  <div>
                    <label style="display: block; font-size: 0.75rem; color: var(--admin-text-secondary); margin-bottom: 6px;">Section Heading</label>
                    <input type="text" id="input-hp-prod-title" value="${escapeHtml(s.homepage_products_title || 'The current edit')}" class="admin-input" style="width: 100%;" maxlength="100" placeholder="The current edit">
                  </div>
                  <div>
                    <label style="display: block; font-size: 0.75rem; color: var(--admin-text-secondary); margin-bottom: 6px;">Section Subtitle / Deck</label>
                    <input type="text" id="input-hp-prod-subtitle" value="${escapeHtml(s.homepage_products_subtitle || 'A curated selection of our latest pieces.')}" class="admin-input" style="width: 100%;" maxlength="255" placeholder="A curated selection of our latest pieces.">
                  </div>
                </div>
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
                <div style="font-size: 0.8125rem; font-weight: 600; color: #fff; margin-bottom: 2px; font-family: ${font};" id="mockup-hp-col-title">${escapeHtml(s.homepage_collections_title || 'Shop by collection')}</div>
                <div style="font-size: 0.6875rem; color: rgba(255, 255, 255, 0.5); line-height: 1.4; margin-bottom: 8px;" id="mockup-hp-col-subtitle">${escapeHtml(s.homepage_collections_subtitle || 'A place for every part of your wardrobe.')}</div>
                
                <div style="font-size: 0.8125rem; font-weight: 600; color: #fff; margin-bottom: 2px; font-family: ${font};" id="mockup-hp-prod-title">${escapeHtml(s.homepage_products_title || 'The current edit')}</div>
                <div style="font-size: 0.6875rem; color: rgba(255, 255, 255, 0.5); line-height: 1.4; margin-bottom: 12px;" id="mockup-hp-prod-subtitle">${escapeHtml(s.homepage_products_subtitle || 'A curated selection of our latest pieces.')}</div>
                
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

  async function persistFaqItems(newFaqItems, reason) {
    try {
      const payload = {
        faq_items: newFaqItems,
        expected_version: currentSettings.version,
        change_reason: reason || 'Update storefront FAQ knowledge base',
      };
      const res = await updateAdminStoreSettings(payload);
      currentSettings = res;
      showAlert('FAQ items updated successfully');
      render();
    } catch (err) {
      showAlert(err.message || 'Failed to update FAQ items', 'error');
    }
  }

  function renderFaqTab() {
    const s = currentSettings;
    const faqs = Array.isArray(s.faq_items) ? s.faq_items : [];

    const filteredFaqs = faqs.filter(item => {
      if (faqCategoryFilter !== 'all' && (item.category || '').toLowerCase() !== faqCategoryFilter.toLowerCase()) {
        return false;
      }
      if (faqSearchQuery) {
        const q = faqSearchQuery.toLowerCase();
        const qMatch = (item.question || '').toLowerCase().includes(q);
        const aMatch = (item.answer || '').toLowerCase().includes(q);
        return qMatch || aMatch;
      }
      return true;
    });

    const isNew = editingFaqId === 'new';
    const currentEditItem = isNew
      ? { id: '', question: '', answer: '', category: 'General', is_enabled: true }
      : (faqs.find(f => f.id === editingFaqId) || null);

    return `
      <div class="set-grid-2col faq-admin-container">
        <!-- Left Column: Support Channels & FAQ Management -->
        <div style="display: flex; flex-direction: column; gap: 16px;">
          <!-- Storefront FAQ Section Headings Card -->
          <div class="set-card">
            <div class="set-card-header">
              <h3 class="set-card-title">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: #F59E0B;"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                Storefront FAQ Section Headings
              </h3>
              <div class="set-action-group">
                <button type="button" id="btn-save-faq-headings" class="set-action-btn is-save" data-tooltip="Save FAQ section headings" aria-label="Save FAQ headings" title="Save FAQ headings">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
                </button>
              </div>
            </div>

            <div style="background: rgba(255, 255, 255, 0.02); border: 1px solid var(--admin-border-subtle); border-radius: 6px; padding: 12px; display: flex; flex-direction: column; gap: 10px;">
              <div>
                <label style="display: block; font-size: 0.75rem; color: var(--admin-text-secondary); margin-bottom: 6px;">FAQ Section Heading</label>
                <input type="text" id="input-faq-section-title" value="${escapeHtml(s.faq_section_title || 'Before you order')}" class="admin-input" style="width: 100%;" maxlength="100" placeholder="Before you order">
                <div style="font-size: 0.6875rem; color: var(--admin-text-muted); margin-top: 4px;">Primary heading displayed above the accordion questions on alphazee.tech.</div>
              </div>
              <div>
                <label style="display: block; font-size: 0.75rem; color: var(--admin-text-secondary); margin-bottom: 6px;">FAQ Section Subtitle / Deck</label>
                <input type="text" id="input-faq-section-subtitle" value="${escapeHtml(s.faq_section_subtitle || 'A few useful answers, all in one place.')}" class="admin-input" style="width: 100%;" maxlength="255" placeholder="A few useful answers, all in one place.">
                <div style="font-size: 0.6875rem; color: var(--admin-text-muted); margin-top: 4px;">Reassurance copy setting expectations for customers before ordering.</div>
              </div>
            </div>
          </div>

          <!-- Customer Support Channels Card -->
          <div class="set-card">
            <div class="set-card-header">
              <h3 class="set-card-title">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: #10B981;"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
                Customer Support Channels
              </h3>
            </div>

            <form id="form-support-channels" style="display: flex; flex-direction: column; gap: 14px;">
              <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px;">
                <div>
                  <label style="display: block; font-size: 0.75rem; color: var(--admin-text-secondary); margin-bottom: 6px;">Support Email</label>
                  <input type="email" id="input-support-email" value="${escapeHtml(s.support_email || '')}" class="admin-input" style="width: 100%;" placeholder="e.g. support@alphazee.tech">
                </div>
                <div>
                  <label style="display: block; font-size: 0.75rem; color: var(--admin-text-secondary); margin-bottom: 6px;">WhatsApp Phone Number</label>
                  <input type="text" id="input-support-phone" value="${escapeHtml(s.support_phone || '')}" class="admin-input" style="width: 100%; font-family: monospace;" placeholder="+92 300 1234567">
                </div>
                <div>
                  <label style="display: block; font-size: 0.75rem; color: var(--admin-text-secondary); margin-bottom: 6px;">Operating Hours</label>
                  <input type="text" id="input-support-hours" value="${escapeHtml(s.support_hours || '')}" class="admin-input" style="width: 100%;" placeholder="Mon-Sat: 10:00 AM – 7:00 PM PKT">
                </div>
              </div>

              <div style="display: flex; justify-content: flex-end; margin-top: 2px;">
                <button type="submit" id="btn-save-support-channels" class="set-action-btn is-save" data-tooltip="Save customer support channels" aria-label="Save support channels" title="Save support channels">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
                </button>
              </div>
            </form>
          </div>

          <!-- FAQ Knowledge Base Card -->
          <div class="set-card">
            <div class="set-card-header">
              <div style="display: flex; align-items: center; gap: 8px;">
                <h3 class="set-card-title">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: #38BDF8;"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                  Storefront FAQ Questions
                </h3>
                <span class="faq-count-pill">${faqs.length}</span>
              </div>

              <!-- Rule 2: Compact 34x34px action button -->
              <div class="set-action-group">
                <button type="button" id="btn-add-faq-item" class="set-action-btn is-save" data-tooltip="Add new FAQ question" aria-label="Add new FAQ question" title="Add question">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                </button>
              </div>
            </div>

            <!-- Search and Category Filters -->
            <div style="display: flex; flex-direction: column; gap: 10px; margin-bottom: 14px;">
              <div style="position: relative;">
                <input type="text" id="input-faq-search" value="${escapeHtml(faqSearchQuery)}" class="admin-input" placeholder="Search questions & answers..." style="width: 100%; padding-left: 34px; font-size: 0.8125rem;">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="position: absolute; left: 11px; top: 50%; transform: translateY(-50%); color: rgba(255, 255, 255, 0.4); pointer-events: none;"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
              </div>

              <div class="faq-filter-pills">
                <button type="button" class="faq-pill ${faqCategoryFilter === 'all' ? 'active' : ''}" data-cat="all">All (${faqs.length})</button>
                <button type="button" class="faq-pill ${faqCategoryFilter === 'delivery' ? 'active' : ''}" data-cat="delivery">Delivery (${faqs.filter(f => (f.category || '').toLowerCase() === 'delivery').length})</button>
                <button type="button" class="faq-pill ${faqCategoryFilter === 'payment' ? 'active' : ''}" data-cat="payment">Payment (${faqs.filter(f => (f.category || '').toLowerCase() === 'payment').length})</button>
                <button type="button" class="faq-pill ${faqCategoryFilter === 'returns' ? 'active' : ''}" data-cat="returns">Returns (${faqs.filter(f => (f.category || '').toLowerCase() === 'returns').length})</button>
                <button type="button" class="faq-pill ${faqCategoryFilter === 'sizing' ? 'active' : ''}" data-cat="sizing">Sizing (${faqs.filter(f => (f.category || '').toLowerCase() === 'sizing').length})</button>
                <button type="button" class="faq-pill ${faqCategoryFilter === 'general' ? 'active' : ''}" data-cat="general">General (${faqs.filter(f => (f.category || '').toLowerCase() === 'general').length})</button>
              </div>
            </div>

            <!-- Inline FAQ Editor -->
            ${currentEditItem ? `
              <div id="faq-editor-box" class="faq-editor-box">
                <div class="faq-editor-header">
                  <span style="font-size: 0.8125rem; font-weight: 600; color: #fff;">${isNew ? 'New FAQ Question' : 'Edit FAQ Question'}</span>
                  <button type="button" id="btn-cancel-faq-editor-x" class="set-action-btn" data-tooltip="Close editor" aria-label="Close editor" title="Close editor" style="width: 28px; height: 28px;">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                  </button>
                </div>
                <div style="display: flex; flex-direction: column; gap: 12px; margin-top: 12px;">
                  <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px;">
                    <div>
                      <label style="display: block; font-size: 0.75rem; color: var(--admin-text-secondary); margin-bottom: 5px;">Category</label>
                      <select id="select-faq-category" class="admin-input" style="width: 100%;">
                        <option value="Delivery" ${(currentEditItem.category || '') === 'Delivery' ? 'selected' : ''}>Delivery</option>
                        <option value="Payment" ${(currentEditItem.category || '') === 'Payment' ? 'selected' : ''}>Payment</option>
                        <option value="Returns" ${(currentEditItem.category || '') === 'Returns' ? 'selected' : ''}>Returns</option>
                        <option value="Sizing" ${(currentEditItem.category || '') === 'Sizing' ? 'selected' : ''}>Sizing</option>
                        <option value="General" ${(currentEditItem.category || '') === 'General' ? 'selected' : ''}>General</option>
                      </select>
                    </div>
                    <div style="display: flex; align-items: flex-end; padding-bottom: 8px;">
                      <label style="display: flex; align-items: center; gap: 8px; font-size: 0.75rem; color: var(--admin-text-secondary); cursor: pointer;">
                        <input type="checkbox" id="input-faq-active" ${currentEditItem.is_enabled !== false ? 'checked' : ''} style="width: 15px; height: 15px; cursor: pointer;">
                        <span>Published & active on storefront</span>
                      </label>
                    </div>
                  </div>
                  <div>
                    <label style="display: block; font-size: 0.75rem; color: var(--admin-text-secondary); margin-bottom: 5px;">Question</label>
                    <input type="text" id="input-faq-question" value="${escapeHtml(currentEditItem.question || '')}" class="admin-input" style="width: 100%;" placeholder="e.g. How long does standard delivery take?" required>
                  </div>
                  <div>
                    <label style="display: flex; justify-content: space-between; font-size: 0.75rem; color: var(--admin-text-secondary); margin-bottom: 5px;">
                      <span>Answer</span>
                      <span id="faq-char-count" style="font-family: monospace; font-size: 0.6875rem; color: rgba(255,255,255,0.4);">${(currentEditItem.answer || '').length} / 1000</span>
                    </label>
                    <textarea id="textarea-faq-answer" class="admin-input" style="width: 100%; min-height: 90px; font-size: 0.8125rem; line-height: 1.5; padding: 10px;" placeholder="Provide clear, concise information..." required maxlength="1000">${escapeHtml(currentEditItem.answer || '')}</textarea>
                  </div>
                  <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 4px;">
                    <button type="button" id="btn-cancel-faq-editor" class="admin-btn admin-btn-ghost" style="padding: 6px 14px; font-size: 0.75rem;">Cancel</button>
                    <button type="button" id="btn-save-faq-editor" class="admin-btn admin-btn-primary" style="padding: 6px 16px; font-size: 0.75rem; background: #10B981;">Save Question</button>
                  </div>
                </div>
              </div>
            ` : ''}

            <!-- FAQ Items List -->
            ${filteredFaqs.length === 0 ? `
              <div style="padding: 30px 14px; text-align: center; color: var(--admin-text-muted); font-size: 0.8125rem; background: rgba(255, 255, 255, 0.02); border-radius: 8px; border: 1px dashed rgba(255, 255, 255, 0.08);">
                No FAQ items found. Click '+' above to create a new question.
              </div>
            ` : `
              <div class="faq-admin-list">
                ${filteredFaqs.map((item) => {
                  const cat = (item.category || 'general').toLowerCase();
                  const globalIndex = faqs.findIndex(f => f.id === item.id);
                  const isFirst = globalIndex === 0;
                  const isLast = globalIndex === faqs.length - 1;
                  return `
                    <div class="faq-admin-card ${item.is_enabled === false ? 'is-disabled' : ''}" data-id="${escapeHtml(item.id)}">
                      <div class="faq-admin-card-top">
                        <div style="display: flex; align-items: center; gap: 8px;">
                          <span class="faq-item-index">#${globalIndex + 1}</span>
                          <span class="faq-cat-badge cat-${cat}">${escapeHtml(item.category || 'General')}</span>
                          <span class="faq-status-pill ${item.is_enabled !== false ? 'is-active' : 'is-disabled'}">${item.is_enabled !== false ? 'Active' : 'Disabled'}</span>
                        </div>
                        <div class="set-action-group">
                          <button type="button" class="set-action-btn btn-faq-up" data-id="${escapeHtml(item.id)}" ${isFirst ? 'disabled style="opacity:0.3; cursor:not-allowed;"' : ''} data-tooltip="Move up" aria-label="Move up" title="Move up">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="18 15 12 9 6 15"/></svg>
                          </button>
                          <button type="button" class="set-action-btn btn-faq-down" data-id="${escapeHtml(item.id)}" ${isLast ? 'disabled style="opacity:0.3; cursor:not-allowed;"' : ''} data-tooltip="Move down" aria-label="Move down" title="Move down">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
                          </button>
                          <button type="button" class="set-action-btn btn-faq-toggle" data-id="${escapeHtml(item.id)}" data-tooltip="${item.is_enabled !== false ? 'Disable question' : 'Enable question'}" aria-label="Toggle active" title="Toggle active">
                            ${item.is_enabled !== false ? `
                              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: #10B981;"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                            ` : `
                              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: rgba(255,255,255,0.4);"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                            `}
                          </button>
                          <button type="button" class="set-action-btn btn-faq-edit" data-id="${escapeHtml(item.id)}" data-tooltip="Edit question" aria-label="Edit question" title="Edit question">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                          </button>
                          <button type="button" class="set-action-btn btn-faq-delete" data-id="${escapeHtml(item.id)}" data-tooltip="Delete question" aria-label="Delete question" title="Delete question" style="color: #F87171;">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>
                          </button>
                        </div>
                      </div>
                      <div class="faq-admin-q">${escapeHtml(item.question)}</div>
                      <div class="faq-admin-a">${escapeHtml(item.answer)}</div>
                    </div>
                  `;
                }).join('')}
              </div>
            `}
          </div>
        </div>

        <!-- Right Column: Interactive Live Storefront Preview -->
        <div class="set-preview-mockup">
          <div class="set-mockup-browser-bar">
            <span class="set-mockup-dot red"></span>
            <span class="set-mockup-dot yellow"></span>
            <span class="set-mockup-dot green"></span>
            <span class="set-mockup-url">alphazee.tech/faq</span>
          </div>

          <div class="set-mockup-body" style="padding: 16px;">
            <div style="margin-bottom: 14px;">
              <div id="mockup-faq-title" style="font-size: 0.875rem; font-weight: 600; color: #fff;">${escapeHtml(s.faq_section_title || 'Before you order')}</div>
              <div id="mockup-faq-subtitle" style="font-size: 0.6875rem; color: rgba(255, 255, 255, 0.5);">${escapeHtml(s.faq_section_subtitle || 'A few useful answers, all in one place.')}</div>
            </div>

            <div class="set-mockup-faq-accordion">
              ${faqs.filter(f => f.is_enabled !== false).map((item, idx) => {
                const isOpen = idx === activeMockupFaqIndex;
                return `
                  <div class="mockup-faq-item ${isOpen ? 'is-open' : ''}" data-idx="${idx}">
                    <div class="mockup-faq-q">
                      <span>${escapeHtml(item.question)}</span>
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="transition: transform 180ms ease; transform: ${isOpen ? 'rotate(180deg)' : 'rotate(0)'}; flex-shrink: 0;"><polyline points="6 9 12 15 18 9"/></svg>
                    </div>
                    <div class="mockup-faq-a" style="display: ${isOpen ? 'block' : 'none'};">
                      ${escapeHtml(item.answer)}
                    </div>
                  </div>
                `;
              }).join('') || '<div style="font-size: 0.75rem; color: rgba(255,255,255,0.4); text-align: center; padding: 20px 0;">No active FAQ items to preview</div>'}
            </div>

            <!-- Customer Care / WhatsApp Mockup Box -->
            <div style="margin-top: 18px; padding-top: 14px; border-top: 1px solid rgba(255, 255, 255, 0.08);">
              <div style="font-size: 0.75rem; font-weight: 600; color: #fff; margin-bottom: 4px;">Need Assistance?</div>
              <div style="font-size: 0.6875rem; color: rgba(255, 255, 255, 0.5); margin-bottom: 10px; line-height: 1.4;">
                ${s.support_hours ? `Hours: ${escapeHtml(s.support_hours)}<br>` : ''}
                ${s.support_email ? `<span style="color: #38BDF8;">${escapeHtml(s.support_email)}</span>` : 'Our support team is available to assist.'}
              </div>
              <div style="display: flex; align-items: center; gap: 8px;">
                ${s.support_phone ? `
                  <div style="display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 6px; background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.3); color: #34D399; font-size: 0.6875rem; font-weight: 500;">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884-.001 2.225.651 3.891 1.746 5.634l-.999 3.648 3.742-.981z"/></svg>
                    <span>WhatsApp: ${escapeHtml(s.support_phone)}</span>
                  </div>
                ` : `
                  <div style="font-size: 0.6875rem; color: rgba(255, 255, 255, 0.4); font-style: italic;">WhatsApp support unconfigured</div>
                `}
              </div>
            </div>
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

    // Storefront Homepage Headings Sync
    const inputHpColTitle = container.querySelector('#input-hp-col-title');
    const inputHpColSubtitle = container.querySelector('#input-hp-col-subtitle');
    const inputHpProdTitle = container.querySelector('#input-hp-prod-title');
    const inputHpProdSubtitle = container.querySelector('#input-hp-prod-subtitle');
    const mockupHpColTitle = container.querySelector('#mockup-hp-col-title');
    const mockupHpColSubtitle = container.querySelector('#mockup-hp-col-subtitle');
    const mockupHpProdTitle = container.querySelector('#mockup-hp-prod-title');
    const mockupHpProdSubtitle = container.querySelector('#mockup-hp-prod-subtitle');

    if (inputHpColTitle && mockupHpColTitle) {
      inputHpColTitle.addEventListener('input', (e) => {
        mockupHpColTitle.textContent = e.target.value || 'Shop by collection';
      });
    }
    if (inputHpColSubtitle && mockupHpColSubtitle) {
      inputHpColSubtitle.addEventListener('input', (e) => {
        mockupHpColSubtitle.textContent = e.target.value || 'A place for every part of your wardrobe.';
      });
    }
    if (inputHpProdTitle && mockupHpProdTitle) {
      inputHpProdTitle.addEventListener('input', (e) => {
        mockupHpProdTitle.textContent = e.target.value || 'The current edit';
      });
    }
    if (inputHpProdSubtitle && mockupHpProdSubtitle) {
      inputHpProdSubtitle.addEventListener('input', (e) => {
        mockupHpProdSubtitle.textContent = e.target.value || 'A curated selection of our latest pieces.';
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
            homepage_collections_title: container.querySelector('#input-hp-col-title')?.value.trim() || 'Shop by collection',
            homepage_collections_subtitle: container.querySelector('#input-hp-col-subtitle')?.value.trim() || 'A place for every part of your wardrobe.',
            homepage_products_title: container.querySelector('#input-hp-prod-title')?.value.trim() || 'The current edit',
            homepage_products_subtitle: container.querySelector('#input-hp-prod-subtitle')?.value.trim() || 'A curated selection of our latest pieces.',
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

    // Save FAQ Section Headings
    const btnSaveFaqHeadings = container.querySelector('#btn-save-faq-headings');
    if (btnSaveFaqHeadings) {
      btnSaveFaqHeadings.addEventListener('click', async (e) => {
        e.preventDefault();
        try {
          const title = (container.querySelector('#input-faq-section-title')?.value || '').trim() || 'Before you order';
          const subtitle = (container.querySelector('#input-faq-section-subtitle')?.value || '').trim() || 'A few useful answers, all in one place.';
          const payload = {
            faq_section_title: title,
            faq_section_subtitle: subtitle,
            expected_version: currentSettings.version,
            change_reason: 'Update storefront FAQ section copy',
          };
          const res = await updateAdminStoreSettings(payload);
          currentSettings = res;
          showAlert('Storefront FAQ section headings updated successfully');
          render();
        } catch (err) {
          showAlert(err.message || 'Failed to update FAQ headings', 'error');
        }
      });
    }

    // FAQ Section Headings Live Mockup Sync
    const inputFaqTitle = container.querySelector('#input-faq-section-title');
    const inputFaqSubtitle = container.querySelector('#input-faq-section-subtitle');
    const mockupFaqTitle = container.querySelector('#mockup-faq-title');
    const mockupFaqSubtitle = container.querySelector('#mockup-faq-subtitle');
    if (inputFaqTitle && mockupFaqTitle) {
      inputFaqTitle.addEventListener('input', (e) => {
        mockupFaqTitle.textContent = e.target.value || 'Before you order';
      });
    }
    if (inputFaqSubtitle && mockupFaqSubtitle) {
      inputFaqSubtitle.addEventListener('input', (e) => {
        mockupFaqSubtitle.textContent = e.target.value || 'A few useful answers, all in one place.';
      });
    }

    // Customer Support Channels Form
    const formSupport = container.querySelector('#form-support-channels');
    if (formSupport) {
      formSupport.addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
          const payload = {
            support_email: container.querySelector('#input-support-email').value.trim() || null,
            support_phone: container.querySelector('#input-support-phone').value.trim() || null,
            support_hours: container.querySelector('#input-support-hours').value.trim() || null,
            expected_version: currentSettings.version,
            change_reason: 'Update customer support channels',
          };
          const res = await updateAdminStoreSettings(payload);
          currentSettings = res;
          showAlert('Support channels saved successfully');
          render();
        } catch (err) {
          showAlert(err.message || 'Failed to update support channels', 'error');
        }
      });
    }

    // FAQ Search & Filter
    const inputFaqSearch = container.querySelector('#input-faq-search');
    if (inputFaqSearch) {
      inputFaqSearch.addEventListener('input', (e) => {
        faqSearchQuery = e.target.value;
        render();
        const nextInput = container.querySelector('#input-faq-search');
        if (nextInput) {
          nextInput.focus();
          nextInput.setSelectionRange(nextInput.value.length, nextInput.value.length);
        }
      });
    }

    container.querySelectorAll('.faq-pill').forEach(btn => {
      btn.addEventListener('click', () => {
        faqCategoryFilter = btn.dataset.cat;
        render();
      });
    });

    // Add FAQ Item button
    const btnAddFaq = container.querySelector('#btn-add-faq-item');
    if (btnAddFaq) {
      btnAddFaq.addEventListener('click', () => {
        editingFaqId = 'new';
        render();
        const qInput = container.querySelector('#input-faq-question');
        if (qInput) qInput.focus();
      });
    }

    // Cancel FAQ Editor
    const btnCancelFaq = container.querySelector('#btn-cancel-faq-editor');
    const btnCancelFaqX = container.querySelector('#btn-cancel-faq-editor-x');
    if (btnCancelFaq) {
      btnCancelFaq.addEventListener('click', () => {
        editingFaqId = null;
        render();
      });
    }
    if (btnCancelFaqX) {
      btnCancelFaqX.addEventListener('click', () => {
        editingFaqId = null;
        render();
      });
    }

    // FAQ Textarea Char Counter
    const textareaFaq = container.querySelector('#textarea-faq-answer');
    const charCounter = container.querySelector('#faq-char-count');
    if (textareaFaq && charCounter) {
      textareaFaq.addEventListener('input', () => {
        charCounter.textContent = `${textareaFaq.value.length} / 1000`;
      });
    }

    // Save FAQ Item (from editor)
    const btnSaveFaqEditor = container.querySelector('#btn-save-faq-editor');
    if (btnSaveFaqEditor) {
      btnSaveFaqEditor.addEventListener('click', async () => {
        const q = (container.querySelector('#input-faq-question')?.value || '').trim();
        const a = (container.querySelector('#textarea-faq-answer')?.value || '').trim();
        const cat = container.querySelector('#select-faq-category')?.value || 'General';
        const active = container.querySelector('#input-faq-active')?.checked ?? true;

        if (!q) {
          showAlert('FAQ question cannot be empty', 'error');
          return;
        }
        if (!a) {
          showAlert('FAQ answer cannot be empty', 'error');
          return;
        }

        let items = [...(currentSettings.faq_items || [])];
        const wasNew = editingFaqId === 'new';
        if (wasNew) {
          const newId = `faq_${Date.now()}`;
          items.push({
            id: newId,
            question: q,
            answer: a,
            category: cat,
            is_enabled: active,
            display_order: items.length,
          });
        } else {
          items = items.map(f => {
            if (f.id === editingFaqId) {
              return {
                ...f,
                question: q,
                answer: a,
                category: cat,
                is_enabled: active,
              };
            }
            return f;
          });
        }

        editingFaqId = null;
        await persistFaqItems(items, wasNew ? 'Add new FAQ item' : 'Update FAQ item');
      });
    }

    // Move Up
    container.querySelectorAll('.btn-faq-up').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const id = btn.dataset.id;
        const items = [...(currentSettings.faq_items || [])];
        const idx = items.findIndex(f => f.id === id);
        if (idx > 0) {
          const temp = items[idx];
          items[idx] = items[idx - 1];
          items[idx - 1] = temp;
          items.forEach((f, i) => { f.display_order = i; });
          await persistFaqItems(items, `Move FAQ "${temp.question.slice(0, 30)}" up`);
        }
      });
    });

    // Move Down
    container.querySelectorAll('.btn-faq-down').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const id = btn.dataset.id;
        const items = [...(currentSettings.faq_items || [])];
        const idx = items.findIndex(f => f.id === id);
        if (idx >= 0 && idx < items.length - 1) {
          const temp = items[idx];
          items[idx] = items[idx + 1];
          items[idx + 1] = temp;
          items.forEach((f, i) => { f.display_order = i; });
          await persistFaqItems(items, `Move FAQ "${temp.question.slice(0, 30)}" down`);
        }
      });
    });

    // Toggle Active / Disabled
    container.querySelectorAll('.btn-faq-toggle').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const id = btn.dataset.id;
        const items = (currentSettings.faq_items || []).map(f => {
          if (f.id === id) {
            return { ...f, is_enabled: f.is_enabled === false ? true : false };
          }
          return f;
        });
        await persistFaqItems(items, 'Toggle FAQ visibility state');
      });
    });

    // Edit Item
    container.querySelectorAll('.btn-faq-edit').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        editingFaqId = btn.dataset.id;
        render();
        const qInput = container.querySelector('#input-faq-question');
        if (qInput) qInput.focus();
      });
    });

    // Delete Item
    container.querySelectorAll('.btn-faq-delete').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const id = btn.dataset.id;
        if (!confirm('Are you sure you want to delete this FAQ question?')) return;
        const items = (currentSettings.faq_items || []).filter(f => f.id !== id);
        items.forEach((f, i) => { f.display_order = i; });
        if (editingFaqId === id) editingFaqId = null;
        await persistFaqItems(items, 'Delete FAQ question');
      });
    });

    // Mockup Interactive Accordion
    container.querySelectorAll('.mockup-faq-item').forEach(item => {
      item.addEventListener('click', () => {
        const idx = parseInt(item.dataset.idx, 10);
        activeMockupFaqIndex = activeMockupFaqIndex === idx ? -1 : idx;
        render();
      });
    });

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
