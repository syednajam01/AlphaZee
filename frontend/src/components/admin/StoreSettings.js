/**
 * StoreSettings.js — Phase VF6 Store Configuration, Legal Policies & Admin Preferences.
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
      <div class="settings-header" style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
        <div>
          <h2 style="font-size: 1.5rem; font-weight: 700; color: #fff; margin: 0 0 6px 0;">⚙️ Store Settings & Admin Preferences</h2>
          <p style="font-size: 0.875rem; color: rgba(255, 255, 255, 0.6); margin: 0;">
            Manage storefront appearance, announcement banners, legal policies, operational thresholds, and your personal console preferences.
          </p>
        </div>
        ${currentSettings ? `
          <div style="display: flex; align-items: center; gap: 10px; background: rgba(255, 255, 255, 0.05); padding: 6px 14px; border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.1);">
            <span style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.5); text-transform: uppercase; letter-spacing: 0.05em;">Current Revision:</span>
            <span id="settings-revision-badge" style="font-size: 0.875rem; font-weight: 700; color: #60a5fa;">v${currentSettings.version}</span>
          </div>
        ` : ''}
      </div>

      <!-- Navigation Tabs -->
      <div class="settings-tabs" style="display: flex; gap: 8px; border-bottom: 1px solid rgba(255, 255, 255, 0.1); margin-bottom: 24px; overflow-x: auto; padding-bottom: 2px;">
        <button type="button" class="settings-tab-btn ${activeTab === 'storefront' ? 'active' : ''}" data-tab="storefront">
          🎨 Storefront & Branding
        </button>
        <button type="button" class="settings-tab-btn ${activeTab === 'shipping' ? 'active' : ''}" data-tab="shipping">
          🚚 Shipping & Thresholds
        </button>
        <button type="button" class="settings-tab-btn ${activeTab === 'policies' ? 'active' : ''}" data-tab="policies">
          📜 Legal & Policies
        </button>
        <button type="button" class="settings-tab-btn ${activeTab === 'audit' ? 'active' : ''}" data-tab="audit">
          ⏱️ Revision History
        </button>
        <button type="button" class="settings-tab-btn ${activeTab === 'preferences' ? 'active' : ''}" data-tab="preferences">
          👤 Admin Preferences
        </button>
      </div>

      <!-- Status Alert Banner -->
      <div id="settings-alert" style="display: none; margin-bottom: 20px; padding: 12px 16px; border-radius: 8px; font-size: 0.875rem;"></div>

      <!-- Tab Content Area -->
      <div class="settings-tab-body">
        ${renderActiveTab()}
      </div>
    `;

    attachEvents();
  }

  function renderActiveTab() {
    if (!currentSettings || !currentPreferences) {
      return `
        <div style="padding: 40px; text-align: center; color: rgba(255, 255, 255, 0.5);">
          <div class="spinner" style="margin-bottom: 12px;"></div>
          Loading configuration...
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
    return `
      <form id="form-storefront-settings" style="display: flex; flex-direction: column; gap: 24px; max-width: 800px;">
        <!-- Announcement Bar Section -->
        <div class="settings-card" style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 20px;">
          <h3 style="font-size: 1.125rem; font-weight: 600; color: #fff; margin: 0 0 16px 0; display: flex; align-items: center; justify-content: space-between;">
            <span>📢 Store Announcement Bar</span>
            <label style="display: flex; align-items: center; gap: 8px; font-size: 0.875rem; font-weight: 400; cursor: pointer;">
              <input type="checkbox" id="input-announcement-enabled" ${s.announcement_banner_enabled ? 'checked' : ''} style="cursor: pointer; width: 16px; height: 16px;">
              <span>Enabled on Storefront</span>
            </label>
          </h3>
          
          <div style="display: flex; flex-direction: column; gap: 14px;">
            <div>
              <label style="display: block; font-size: 0.8125rem; color: rgba(255, 255, 255, 0.7); margin-bottom: 6px;">Announcement Text</label>
              <input type="text" id="input-announcement-text" value="${escapeHtml(s.announcement_banner_text || '')}" class="admin-input" style="width: 100%;" required>
            </div>
            <div>
              <label style="display: block; font-size: 0.8125rem; color: rgba(255, 255, 255, 0.7); margin-bottom: 6px;">Banner Link (optional, e.g. #featured or /track)</label>
              <input type="text" id="input-announcement-link" value="${escapeHtml(s.announcement_banner_link || '')}" class="admin-input" style="width: 100%;" placeholder="#featured">
            </div>

            <!-- Live Preview -->
            <div style="margin-top: 10px; background: rgba(0, 0, 0, 0.4); padding: 12px; border-radius: 8px; border: 1px dashed rgba(255, 255, 255, 0.2);">
              <span style="font-size: 0.6875rem; text-transform: uppercase; letter-spacing: 0.08em; color: rgba(255, 255, 255, 0.4); display: block; margin-bottom: 6px;">Live Banner Preview:</span>
              <div id="preview-announcement-bar" style="background: ${s.accent_color || '#111827'}; color: #fff; padding: 8px 14px; text-align: center; border-radius: 6px; font-size: 0.8125rem; font-weight: 500;">
                ${escapeHtml(s.announcement_banner_text || 'Store announcement banner')}
              </div>
            </div>
          </div>
        </div>

        <!-- Branding & Presentation Tokens -->
        <div class="settings-card" style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 20px;">
          <h3 style="font-size: 1.125rem; font-weight: 600; color: #fff; margin: 0 0 16px 0;">🎨 Brand Identity & Theme Tokens</h3>
          
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px;">
            <div>
              <label style="display: block; font-size: 0.8125rem; color: rgba(255, 255, 255, 0.7); margin-bottom: 6px;">Brand Name</label>
              <input type="text" id="input-brand-name" value="${escapeHtml(s.brand_name || 'AlphaZee')}" class="admin-input" style="width: 100%;" required>
            </div>
            <div>
              <label style="display: block; font-size: 0.8125rem; color: rgba(255, 255, 255, 0.7); margin-bottom: 6px;">Tagline</label>
              <input type="text" id="input-tagline" value="${escapeHtml(s.tagline || '')}" class="admin-input" style="width: 100%;">
            </div>
            <div>
              <label style="display: block; font-size: 0.8125rem; color: rgba(255, 255, 255, 0.7); margin-bottom: 6px;">Primary Accent Color</label>
              <div style="display: flex; align-items: center; gap: 10px;">
                <input type="color" id="input-accent-color-picker" value="${s.accent_color || '#111827'}" style="width: 44px; height: 38px; border: none; border-radius: 6px; cursor: pointer; background: transparent;">
                <input type="text" id="input-accent-color" value="${escapeHtml(s.accent_color || '#111827')}" class="admin-input" style="flex: 1; font-family: monospace;" pattern="^#[0-9a-fA-F]{6}$" required>
              </div>
            </div>
            <div>
              <label style="display: block; font-size: 0.8125rem; color: rgba(255, 255, 255, 0.7); margin-bottom: 6px;">Store Typography</label>
              <select id="select-font-family" class="admin-input" style="width: 100%;">
                <option value="Inter, sans-serif" ${s.font_family === 'Inter, sans-serif' ? 'selected' : ''}>Inter (Modern Sans)</option>
                <option value="Outfit, sans-serif" ${s.font_family === 'Outfit, sans-serif' ? 'selected' : ''}>Outfit (Geometric Premium)</option>
                <option value="Playfair Display, serif" ${s.font_family === 'Playfair Display, serif' ? 'selected' : ''}>Playfair Display (Editorial Serif)</option>
                <option value="System-UI, sans-serif" ${s.font_family === 'System-UI, sans-serif' ? 'selected' : ''}>System UI Default</option>
              </select>
            </div>
            <div>
              <label style="display: block; font-size: 0.8125rem; color: rgba(255, 255, 255, 0.7); margin-bottom: 6px;">Button Border Radius</label>
              <select id="select-border-radius" class="admin-input" style="width: 100%;">
                <option value="none" ${s.border_radius === 'none' ? 'selected' : ''}>Sharp (0px)</option>
                <option value="sm" ${s.border_radius === 'sm' ? 'selected' : ''}>Slight Curve (4px)</option>
                <option value="md" ${s.border_radius === 'md' ? 'selected' : ''}>Modern Medium (8px)</option>
                <option value="lg" ${s.border_radius === 'lg' ? 'selected' : ''}>Rounded Large (12px)</option>
                <option value="full" ${s.border_radius === 'full' ? 'selected' : ''}>Pill / Fully Rounded</option>
              </select>
            </div>
            <div>
              <label style="display: block; font-size: 0.8125rem; color: rgba(255, 255, 255, 0.7); margin-bottom: 6px;">Layout Spacing Density</label>
              <select id="select-spacing-density" class="admin-input" style="width: 100%;">
                <option value="compact" ${s.spacing_density === 'compact' ? 'selected' : ''}>Compact (High density)</option>
                <option value="comfortable" ${s.spacing_density === 'comfortable' ? 'selected' : ''}>Comfortable (Balanced)</option>
                <option value="spacious" ${s.spacing_density === 'spacious' ? 'selected' : ''}>Spacious (Airy Editorial)</option>
              </select>
            </div>
          </div>
        </div>

        <!-- Reason & Submit -->
        <div style="display: flex; gap: 12px; align-items: center; justify-content: flex-end;">
          <input type="text" id="input-change-reason" placeholder="Change reason (e.g. Seasonal Theme Update)" class="admin-input" style="max-width: 320px;">
          <button type="submit" id="btn-save-storefront" class="btn btn-primary" style="padding: 10px 24px; font-weight: 600;">
            💾 Save Storefront Settings
          </button>
        </div>
      </form>
    `;
  }

  function renderShippingTab() {
    const s = currentSettings;
    const stdPkr = Math.round(s.standard_shipping_fee_minor / 100);
    const freePkr = s.free_shipping_threshold_minor ? Math.round(s.free_shipping_threshold_minor / 100) : '';

    return `
      <form id="form-shipping-settings" style="display: flex; flex-direction: column; gap: 24px; max-width: 800px;">
        <div class="settings-card" style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 20px;">
          <h3 style="font-size: 1.125rem; font-weight: 600; color: #fff; margin: 0 0 16px 0;">🚚 Shipping Coverage & Rates</h3>
          <p style="font-size: 0.8125rem; color: rgba(255, 255, 255, 0.6); margin: 0 0 16px 0;">
            AlphaZee strictly bears 100% of RTO and return transit expenses. Configure customer-facing delivery coverage and flat standard charges below.
          </p>
          
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px;">
            <div>
              <label style="display: block; font-size: 0.8125rem; color: rgba(255, 255, 255, 0.7); margin-bottom: 6px;">Coverage Area</label>
              <input type="text" id="input-shipping-coverage" value="${escapeHtml(s.shipping_coverage_area || 'All Pakistan')}" class="admin-input" style="width: 100%;" required>
            </div>
            <div>
              <label style="display: block; font-size: 0.8125rem; color: rgba(255, 255, 255, 0.7); margin-bottom: 6px;">Standard Delivery Fee (PKR)</label>
              <input type="number" id="input-shipping-fee-pkr" value="${stdPkr}" min="0" step="10" class="admin-input" style="width: 100%;" required>
            </div>
            <div>
              <label style="display: block; font-size: 0.8125rem; color: rgba(255, 255, 255, 0.7); margin-bottom: 6px;">Free Delivery Threshold (PKR, leave blank if none)</label>
              <input type="number" id="input-free-shipping-pkr" value="${freePkr}" min="0" step="100" class="admin-input" style="width: 100%;" placeholder="e.g. 5000">
            </div>
          </div>
        </div>

        <div class="settings-card" style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 20px;">
          <h3 style="font-size: 1.125rem; font-weight: 600; color: #fff; margin: 0 0 16px 0;">⚠️ Operational Alerts & Stock Thresholds</h3>
          
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px;">
            <div>
              <label style="display: block; font-size: 0.8125rem; color: rgba(255, 255, 255, 0.7); margin-bottom: 6px;">Low-Stock Warning (Units)</label>
              <input type="number" id="input-low-stock-threshold" value="${s.low_stock_threshold}" min="0" step="1" class="admin-input" style="width: 100%;" required>
              <small style="color: rgba(255, 255, 255, 0.4); font-size: 0.75rem;">Variants at or below this count trigger low-stock alerts.</small>
            </div>
            <div>
              <label style="display: block; font-size: 0.8125rem; color: rgba(255, 255, 255, 0.7); margin-bottom: 6px;">Stock Staleness Warning (Days)</label>
              <input type="number" id="input-staleness-threshold" value="${s.stock_staleness_threshold_days}" min="1" step="1" class="admin-input" style="width: 100%;" required>
              <small style="color: rgba(255, 255, 255, 0.4); font-size: 0.75rem;">Unverified vendor stock triggers staleness warning after N days.</small>
            </div>
          </div>
        </div>

        <div style="display: flex; gap: 12px; align-items: center; justify-content: flex-end;">
          <button type="submit" id="btn-save-shipping" class="btn btn-primary" style="padding: 10px 24px; font-weight: 600;">
            💾 Save Logistics & Thresholds
          </button>
        </div>
      </form>
    `;
  }

  function renderPoliciesTab() {
    const s = currentSettings;
    const policyMap = {
      delivery: {
        title: '🚚 Delivery & Shipping Policy',
        content: s.delivery_policy_content || '',
        status: s.delivery_policy_status,
        publishedAt: s.delivery_policy_published_at,
      },
      return: {
        title: '🔄 Return & Exchange Policy',
        content: s.return_policy_content || '',
        status: s.return_policy_status,
        publishedAt: s.return_policy_published_at,
      },
      terms: {
        title: '⚖️ Terms of Service',
        content: s.terms_policy_content || '',
        status: s.terms_policy_status,
        publishedAt: s.terms_policy_published_at,
      },
      privacy: {
        title: '🔒 Privacy Policy',
        content: s.privacy_policy_content || '',
        status: s.privacy_policy_status,
        publishedAt: s.privacy_policy_published_at,
      },
    };

    const pol = policyMap[activePolicy];
    const isPublished = pol.status === 'published';

    return `
      <div style="display: flex; flex-direction: column; gap: 20px; max-width: 900px;">
        <!-- Policy Switcher Sub-nav -->
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
          ${Object.keys(policyMap).map(k => {
            const p = policyMap[k];
            const active = k === activePolicy;
            return `
              <button type="button" class="btn ${active ? 'btn-primary' : 'btn-secondary'} sub-policy-tab" data-policy="${k}" style="padding: 6px 14px; font-size: 0.8125rem;">
                ${p.title.split(' ')[0]} ${p.title.split(' ')[1]}
                <span style="font-size: 0.6875rem; padding: 2px 6px; border-radius: 4px; margin-left: 6px; ${p.status === 'published' ? 'background: rgba(34, 197, 94, 0.2); color: #4ade80;' : 'background: rgba(234, 179, 8, 0.2); color: #facc15;'}">
                  ${p.status.toUpperCase()}
                </span>
              </button>
            `;
          }).join('')}
        </div>

        <!-- Policy Editor Card -->
        <div class="settings-card" style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 20px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 10px;">
            <div>
              <h3 style="font-size: 1.125rem; font-weight: 600; color: #fff; margin: 0 0 4px 0;">${pol.title}</h3>
              <div style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.5);">
                Status: <strong style="color: ${isPublished ? '#4ade80' : '#facc15'}; text-transform: uppercase;">${pol.status}</strong>
                ${pol.publishedAt ? ` • Last published: ${new Date(pol.publishedAt).toLocaleString()}` : ''}
              </div>
            </div>

            <!-- Publish / Unpublish actions -->
            <div style="display: flex; gap: 10px;">
              ${isPublished ? `
                <button type="button" id="btn-unpublish-policy" class="btn btn-secondary" style="font-size: 0.8125rem;">
                  Revert to Draft
                </button>
              ` : `
                <button type="button" id="btn-publish-policy" class="btn btn-primary" style="background: #16a34a; border-color: #16a34a; font-size: 0.8125rem;">
                  🚀 Publish to Storefront
                </button>
              `}
            </div>
          </div>

          <div>
            <label style="display: block; font-size: 0.8125rem; color: rgba(255, 255, 255, 0.7); margin-bottom: 6px;">Policy Content (Markdown / Plain Text)</label>
            <textarea id="textarea-policy-content" class="admin-input" style="width: 100%; min-height: 240px; font-family: monospace; font-size: 0.875rem; line-height: 1.5;" placeholder="Enter legal terms, delivery commitments, or return rules...">${escapeHtml(pol.content)}</textarea>
          </div>

          <div style="display: flex; justify-content: flex-end; margin-top: 16px;">
            <button type="button" id="btn-save-policy-draft" class="btn btn-secondary" style="padding: 8px 18px; font-size: 0.8125rem;">
              💾 Save Draft
            </button>
          </div>
        </div>
      </div>
    `;
  }

  function renderAuditTab() {
    return `
      <div class="settings-card" style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 20px;">
        <h3 style="font-size: 1.125rem; font-weight: 600; color: #fff; margin: 0 0 16px 0;">⏱️ Configuration Revision History</h3>
        
        ${auditLogs.length === 0 ? `
          <div style="padding: 24px; text-align: center; color: rgba(255, 255, 255, 0.4);">
            No configuration changes recorded yet. Initial baseline is Revision 1.
          </div>
        ` : `
          <div style="overflow-x: auto;">
            <table class="admin-table" style="width: 100%; border-collapse: collapse; font-size: 0.8125rem;">
              <thead>
                <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.1); text-align: left; color: rgba(255, 255, 255, 0.6);">
                  <th style="padding: 10px;">Revision</th>
                  <th style="padding: 10px;">Timestamp</th>
                  <th style="padding: 10px;">Reason</th>
                  <th style="padding: 10px;">Modified Fields</th>
                </tr>
              </thead>
              <tbody>
                ${auditLogs.map(log => `
                  <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.05);">
                    <td style="padding: 10px; font-weight: 700; color: #60a5fa;">v${log.version}</td>
                    <td style="padding: 10px; color: rgba(255, 255, 255, 0.7);">${new Date(log.created_at).toLocaleString()}</td>
                    <td style="padding: 10px; color: rgba(255, 255, 255, 0.9);">${escapeHtml(log.change_reason || '—')}</td>
                    <td style="padding: 10px; font-family: monospace; font-size: 0.75rem; color: #a78bfa;">
                      ${Object.keys(log.changed_fields || {}).join(', ') || '—'}
                    </td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        `}
      </div>
    `;
  }

  function renderPreferencesTab() {
    const p = currentPreferences;
    return `
      <form id="form-admin-preferences" style="display: flex; flex-direction: column; gap: 24px; max-width: 800px;">
        <div class="settings-card" style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 20px;">
          <h3 style="font-size: 1.125rem; font-weight: 600; color: #fff; margin: 0 0 16px 0;">👤 Personal Console Preferences</h3>
          <p style="font-size: 0.8125rem; color: rgba(255, 255, 255, 0.6); margin: 0 0 16px 0;">
            Preferences are isolated to your owner account. Changes here do not alter storefront behavior or other administrators' consoles.
          </p>

          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px;">
            <div>
              <label style="display: block; font-size: 0.8125rem; color: rgba(255, 255, 255, 0.7); margin-bottom: 6px;">Interface Theme</label>
              <select id="select-pref-theme" class="admin-input" style="width: 100%;">
                <option value="system" ${p.theme === 'system' ? 'selected' : ''}>System Default</option>
                <option value="dark" ${p.theme === 'dark' ? 'selected' : ''}>OLED Dark</option>
                <option value="light" ${p.theme === 'light' ? 'selected' : ''}>Light Theme</option>
              </select>
            </div>
            <div>
              <label style="display: block; font-size: 0.8125rem; color: rgba(255, 255, 255, 0.7); margin-bottom: 6px;">Table Display Density</label>
              <select id="select-pref-density" class="admin-input" style="width: 100%;">
                <option value="comfortable" ${p.table_density === 'comfortable' ? 'selected' : ''}>Comfortable (Standard)</option>
                <option value="compact" ${p.table_density === 'compact' ? 'selected' : ''}>Compact (Dense)</option>
              </select>
            </div>
            <div>
              <label style="display: block; font-size: 0.8125rem; color: rgba(255, 255, 255, 0.7); margin-bottom: 6px;">Default Analytics Period</label>
              <select id="select-pref-date" class="admin-input" style="width: 100%;">
                <option value="today" ${p.default_date_range === 'today' ? 'selected' : ''}>Today</option>
                <option value="this_month" ${p.default_date_range === 'this_month' ? 'selected' : ''}>This Month</option>
                <option value="last_month" ${p.default_date_range === 'last_month' ? 'selected' : ''}>Last Month</option>
                <option value="all_time" ${p.default_date_range === 'all_time' ? 'selected' : ''}>All Time</option>
              </select>
            </div>
          </div>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: center; gap: 12px;">
          <button type="button" id="btn-reset-preferences" class="btn btn-secondary" style="color: #ef4444; border-color: rgba(239, 68, 68, 0.4);">
            🔄 Reset to System Defaults
          </button>
          <button type="submit" id="btn-save-preferences" class="btn btn-primary" style="padding: 10px 24px; font-weight: 600;">
            💾 Save Preferences
          </button>
        </div>
      </form>
    `;
  }

  function showAlert(message, type = 'success') {
    const alert = container.querySelector('#settings-alert');
    if (!alert) return;
    alert.style.display = 'block';
    if (type === 'success') {
      alert.style.background = 'rgba(34, 197, 94, 0.15)';
      alert.style.color = '#4ade80';
      alert.style.border = '1px solid rgba(34, 197, 94, 0.3)';
    } else {
      alert.style.background = 'rgba(239, 68, 68, 0.15)';
      alert.style.color = '#f87171';
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

    // Color picker sync
    const picker = container.querySelector('#input-accent-color-picker');
    const hexInput = container.querySelector('#input-accent-color');
    const previewBar = container.querySelector('#preview-announcement-bar');

    if (picker && hexInput) {
      picker.addEventListener('input', (e) => {
        hexInput.value = e.target.value;
        if (previewBar) previewBar.style.background = e.target.value;
      });
      hexInput.addEventListener('input', (e) => {
        if (/^#[0-9a-fA-F]{6}$/.test(e.target.value)) {
          picker.value = e.target.value;
          if (previewBar) previewBar.style.background = e.target.value;
        }
      });
    }

    // Announcement text preview sync
    const announceInput = container.querySelector('#input-announcement-text');
    if (announceInput && previewBar) {
      announceInput.addEventListener('input', (e) => {
        previewBar.textContent = e.target.value || 'Store announcement banner';
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
          const res = await updateAdminStoreSettings(payload);
          currentSettings = res;
          showAlert(`Storefront settings saved! Revision v${res.version} is now active.`);
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
            free_shipping_threshold_minor: freePkr !== null ? Math.round(freePkr * 100) : null,
            low_stock_threshold: parseInt(container.querySelector('#input-low-stock-threshold').value, 10),
            stock_staleness_threshold_days: parseInt(container.querySelector('#input-staleness-threshold').value, 10),
          };
          const res = await updateAdminStoreSettings(payload);
          currentSettings = res;
          showAlert(`Logistics and operational thresholds updated (Revision v${res.version}).`);
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
          showAlert(`${activePolicy.toUpperCase()} policy draft saved.`);
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
          // First save draft content to be sure
          const key = `${activePolicy}_policy_content`;
          await updateAdminStoreSettings({ [key]: text });
          const res = await publishStorePolicy(activePolicy, true);
          currentSettings = res;
          showAlert(`🚀 ${activePolicy.toUpperCase()} policy published to public storefront!`);
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
          showAlert(`${activePolicy.toUpperCase()} policy reverted to draft.`);
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
          const res = await updateAdminPreferences(payload);
          currentPreferences = res;
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
        <div style="padding: 30px; background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 8px; color: #f87171;">
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
