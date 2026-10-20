/**
 * VendorUsersModal.js — Owner administration modal for supplier stock logins & shortages (VS2-VS3 / VF5).
 */
import { escapeHtml } from '../../utils/dom.js';
import {
  fetchSupplierVendorUsers,
  provisionVendorUser,
  resetVendorPassword,
  toggleVendorUserStatus,
  fetchShortages,
  resolveShortage,
} from '../../utils/api.js';

export function createVendorUsersModal(supplier, { onClose = () => {} } = {}) {
  const container = document.createElement('div');
  container.className = 'modal-container is-open';
  container.id = 'vendor-users-dialog';
  container.setAttribute('role', 'dialog');
  container.setAttribute('aria-modal', 'true');
  container.setAttribute('aria-label', `Stock Logins: ${supplier.name}`);
  container.style.cssText = 'position: fixed; inset: 0; z-index: 1000; display: flex; align-items: center; justify-content: center;';

  let users = [];
  let shortages = [];
  let loading = true;
  let activeTab = 'logins'; // 'logins' | 'shortages'

  container.innerHTML = `
    <div class="drawer-backdrop" style="position: fixed; inset: 0; background: rgba(0,0,0,0.75); z-index: 1001;"></div>
    <div class="modal-content" style="z-index: 1002; max-width: 900px; width: 95%; max-height: 90vh; overflow-y: auto; background: #141715; color: #FFFFFF; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.15); padding: 24px; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.8); position: relative;">
      
      <!-- Header -->
      <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px solid rgba(255, 255, 255, 0.1); padding-bottom: 16px; margin-bottom: 16px;">
        <div>
          <div style="display: flex; align-items: center; gap: 10px;">
            <h2 style="font-size: 1.25rem; font-weight: 700; margin: 0;">🔑 ${escapeHtml(supplier.name)} — Stock Portal Access</h2>
            <span class="badge ${supplier.status === 'active' ? 'badge-accent' : 'badge-neutral'}" style="font-size: 0.7rem;">
              ${escapeHtml(supplier.status)}
            </span>
          </div>
          <p style="font-size: 0.8125rem; color: rgba(255, 255, 255, 0.6); margin: 4px 0 0 0;">
            Supplier Slug: <code>${escapeHtml(supplier.slug)}</code> &bull; Store Staff Stock Management Credentials
          </p>
        </div>
        <button id="btn-close-vendor-users" class="btn-icon" style="background: none; border: none; color: rgba(255, 255, 255, 0.7); font-size: 1.5rem; cursor: pointer; padding: 4px 8px;" aria-label="Close dialog">&times;</button>
      </div>

      <!-- Navigation tabs -->
      <div style="display: flex; gap: 8px; margin-bottom: 20px; border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding-bottom: 8px;">
        <button type="button" id="tab-logins-btn" class="btn btn-sm btn-primary" style="font-size: 0.8125rem;">
          👤 Provisioned Logins
        </button>
        <button type="button" id="tab-shortages-btn" class="btn btn-sm btn-secondary" style="font-size: 0.8125rem;">
          ⚠️ Stock Shortages <span id="shortages-count-badge" class="badge" style="background: #991B1B; color: #FFF; font-size: 0.68rem; margin-left: 4px; display: none;">0</span>
        </button>
      </div>

      <div id="vendor-users-content">
        <p style="text-align: center; color: rgba(255,255,255,0.5);">Loading vendor access details...</p>
      </div>

    </div>
  `;

  async function loadData() {
    loading = true;
    try {
      const [uRes, sRes] = await Promise.all([
        fetchSupplierVendorUsers(supplier.id),
        fetchShortages(supplier.id),
      ]);
      users = uRes || [];
      shortages = sRes || [];
    } catch (err) {
      console.error('Failed to load vendor users or shortages:', err);
    } finally {
      loading = false;
      renderContent();
    }
  }

  function renderContent() {
    const badge = container.querySelector('#shortages-count-badge');
    const openShortages = shortages.filter(s => s.status === 'open');
    if (badge) {
      if (openShortages.length > 0) {
        badge.textContent = openShortages.length;
        badge.style.display = 'inline-block';
      } else {
        badge.style.display = 'none';
      }
    }

    const contentArea = container.querySelector('#vendor-users-content');
    if (!contentArea) return;

    if (loading) {
      contentArea.innerHTML = '<p style="text-align: center; color: rgba(255,255,255,0.5);">Loading...</p>';
      return;
    }

    if (activeTab === 'logins') {
      renderLoginsTab(contentArea);
    } else {
      renderShortagesTab(contentArea);
    }
  }

  function renderLoginsTab(contentArea) {
    contentArea.innerHTML = `
      <div style="display: grid; grid-template-columns: 3fr 2fr; gap: 20px;">
        <!-- Logins Table -->
        <div>
          <h3 style="font-size: 0.9375rem; font-weight: 700; margin-bottom: 12px;">Active Stock Logins</h3>
          <div style="overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 0.8125rem;">
              <thead>
                <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.12); font-size: 0.72rem; color: rgba(255, 255, 255, 0.5); text-transform: uppercase;">
                  <th style="padding: 8px;">Username</th>
                  <th style="padding: 8px;">Status</th>
                  <th style="padding: 8px;">Created</th>
                  <th style="padding: 8px; text-align: right;">Actions</th>
                </tr>
              </thead>
              <tbody>
                ${users.length === 0 ? '<tr><td colspan="4" style="padding: 20px 8px; text-align: center; color: rgba(255,255,255,0.4);">No stock users provisioned yet. Use the form to grant access.</td></tr>' : users.map(u => `
                  <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.06);">
                    <td style="padding: 10px 8px; font-weight: 600;">
                      <code>${escapeHtml(u.username)}</code>
                    </td>
                    <td style="padding: 10px 8px;">
                      <span class="badge ${u.is_active ? 'badge-accent' : 'badge-neutral'}" style="font-size: 0.68rem;">
                        ${u.is_active ? 'Active' : 'Disabled'}
                      </span>
                    </td>
                    <td style="padding: 10px 8px; color: rgba(255,255,255,0.5); font-size: 0.75rem;">
                      ${new Date(u.created_at).toLocaleDateString()}
                    </td>
                    <td style="padding: 10px 8px; text-align: right;">
                      <button type="button" class="btn btn-secondary btn-sm btn-reset-pwd" data-user-id="${u.id}" data-username="${escapeHtml(u.username)}" style="font-size: 0.72rem; padding: 4px 8px; margin-right: 4px;">
                        Reset Pwd
                      </button>
                      <button type="button" class="btn btn-secondary btn-sm btn-toggle-status" data-user-id="${u.id}" data-active="${u.is_active}" style="font-size: 0.72rem; padding: 4px 8px;">
                        ${u.is_active ? 'Disable' : 'Enable'}
                      </button>
                    </td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        </div>

        <!-- Provision Form -->
        <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 16px;">
          <h3 style="font-size: 0.9375rem; font-weight: 700; margin-bottom: 12px;">+ Provision New Stock Login</h3>
          <p style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.6); margin-top: 0; margin-bottom: 14px;">
            Grants physical inventory counting rights restricted exclusively to <strong>${escapeHtml(supplier.name)}</strong> variants.
          </p>
          <form id="provision-user-form" style="display: flex; flex-direction: column; gap: 10px;">
            <div>
              <label style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); display: block; margin-bottom: 2px;">Stock Username *</label>
              <input type="text" id="prov-username" required placeholder="e.g. ${supplier.slug}_stock_1" style="width: 100%; padding: 8px 12px; background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 6px; font-size: 0.8125rem;" />
            </div>
            <div>
              <label style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); display: block; margin-bottom: 2px;">Temporary / Initial Password *</label>
              <input type="password" id="prov-password" required minlength="12" placeholder="At least 12 characters" style="width: 100%; padding: 8px 12px; background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 6px; font-size: 0.8125rem;" />
            </div>
            <div id="prov-error" style="display: none; color: #F87171; font-size: 0.75rem; font-weight: 600;"></div>
            <button type="submit" id="btn-submit-provision" class="btn btn-primary" style="padding: 8px 14px; font-size: 0.8125rem; margin-top: 4px;">
              Create Stock Login
            </button>
          </form>
        </div>
      </div>
    `;

    // Wire provision form
    const form = contentArea.querySelector('#provision-user-form');
    const provError = contentArea.querySelector('#prov-error');
    const submitBtn = contentArea.querySelector('#btn-submit-provision');

    form?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const username = contentArea.querySelector('#prov-username').value.trim();
      const password = contentArea.querySelector('#prov-password').value;

      submitBtn.disabled = true;
      submitBtn.textContent = 'Creating...';
      provError.style.display = 'none';

      try {
        await provisionVendorUser(supplier.id, {
          username,
          password,
        });
        await loadData();
      } catch (err) {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Create Stock Login';
        provError.textContent = err.message || 'Failed to provision login.';
        provError.style.display = 'block';
      }
    });

    // Wire reset password buttons
    contentArea.querySelectorAll('.btn-reset-pwd').forEach(btn => {
      btn.addEventListener('click', async () => {
        const uId = btn.getAttribute('data-user-id');
        const uname = btn.getAttribute('data-username');
        const newPwd = prompt(`Enter new password for ${uname} (minimum 12 characters):`);
        if (!newPwd || newPwd.trim().length < 12) {
          if (newPwd !== null) alert('Password must be at least 12 characters.');
          return;
        }
        try {
          await resetVendorPassword(uId, { password: newPwd.trim() });
          alert(`Password for ${uname} reset successfully.`);
          await loadData();
        } catch (err) {
          alert(`Failed to reset password: ${err.message}`);
        }
      });
    });

    // Wire toggle status buttons
    contentArea.querySelectorAll('.btn-toggle-status').forEach(btn => {
      btn.addEventListener('click', async () => {
        const uId = btn.getAttribute('data-user-id');
        const isCurrentActive = btn.getAttribute('data-active') === 'true';
        try {
          await toggleVendorUserStatus(uId, !isCurrentActive);
          await loadData();
        } catch (err) {
          alert(`Failed to toggle user status: ${err.message}`);
        }
      });
    });
  }

  function renderShortagesTab(contentArea) {
    contentArea.innerHTML = `
      <div>
        <h3 style="font-size: 0.9375rem; font-weight: 700; margin-bottom: 12px;">Reported Stock Shortages</h3>
        <p style="font-size: 0.78rem; color: rgba(255, 255, 255, 0.6); margin-top: 0; margin-bottom: 14px;">
          When store staff reports stock below committed holds, customer reservations are safely preserved while owner investigates.
        </p>
        <div style="overflow-x: auto;">
          <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 0.8125rem;">
            <thead>
              <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.12); font-size: 0.72rem; color: rgba(255, 255, 255, 0.5); text-transform: uppercase;">
                <th style="padding: 8px;">Date</th>
                <th style="padding: 8px;">Variant ID</th>
                <th style="padding: 8px;">Reported Count</th>
                <th style="padding: 8px;">Held Holds</th>
                <th style="padding: 8px;">Status</th>
                <th style="padding: 8px;">Notes</th>
                <th style="padding: 8px; text-align: right;">Resolution</th>
              </tr>
            </thead>
            <tbody>
              ${shortages.length === 0 ? '<tr><td colspan="7" style="padding: 24px 8px; text-align: center; color: rgba(255,255,255,0.4);">No stock shortages reported for this supplier.</td></tr>' : shortages.map(s => `
                <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.06);">
                  <td style="padding: 10px 8px; color: rgba(255,255,255,0.6); font-size: 0.75rem;">
                    ${new Date(s.reported_at).toLocaleString()}
                  </td>
                  <td style="padding: 10px 8px; font-weight: 600;">
                    Variant #${s.variant_id}
                  </td>
                  <td style="padding: 10px 8px; color: #F87171; font-weight: 700;">
                    ${s.reported_count}
                  </td>
                  <td style="padding: 10px 8px; color: #FBBF24; font-weight: 700;">
                    ${s.held_reservations}
                  </td>
                  <td style="padding: 10px 8px;">
                    <span class="badge ${s.status === 'open' ? 'badge-danger' : 'badge-neutral'}" style="font-size: 0.68rem; ${s.status === 'open' ? 'background: #991B1B; color: #FFF;' : ''}">
                      ${escapeHtml(s.status)}
                    </span>
                  </td>
                  <td style="padding: 10px 8px; font-size: 0.75rem; color: rgba(255,255,255,0.7); max-width: 200px;">
                    ${escapeHtml(s.notes || '—')}
                    ${s.resolution_note ? `<div style="color: #34D399; margin-top: 4px;">Res: ${escapeHtml(s.resolution_note)}</div>` : ''}
                  </td>
                  <td style="padding: 10px 8px; text-align: right;">
                    ${s.status === 'open' ? `
                      <button type="button" class="btn btn-primary btn-sm btn-resolve-shortage" data-shortage-id="${s.id}" style="font-size: 0.72rem; padding: 4px 8px;">
                        Resolve Shortage
                      </button>
                    ` : '<span style="color: rgba(255,255,255,0.4); font-size: 0.75rem;">Resolved</span>'}
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;

    // Wire resolve shortage buttons
    contentArea.querySelectorAll('.btn-resolve-shortage').forEach(btn => {
      btn.addEventListener('click', async () => {
        const sId = btn.getAttribute('data-shortage-id');
        const resNote = prompt('Enter resolution notes (e.g. Customer notified; replacement dispatched; fresh stock received):');
        if (!resNote || resNote.trim().length < 3) {
          if (resNote !== null) alert('Please provide a resolution note (at least 3 characters).');
          return;
        }
        try {
          await resolveShortage(sId, {
            resolution_action: 'resolved',
            resolution_note: resNote.trim(),
          });
          alert('Shortage resolved successfully.');
          await loadData();
        } catch (err) {
          alert(`Failed to resolve shortage: ${err.message}`);
        }
      });
    });
  }

  // Event handlers
  container.querySelector('#tab-logins-btn')?.addEventListener('click', () => {
    activeTab = 'logins';
    container.querySelector('#tab-logins-btn').className = 'btn btn-sm btn-primary';
    container.querySelector('#tab-shortages-btn').className = 'btn btn-sm btn-secondary';
    renderContent();
  });

  container.querySelector('#tab-shortages-btn')?.addEventListener('click', () => {
    activeTab = 'shortages';
    container.querySelector('#tab-logins-btn').className = 'btn btn-sm btn-secondary';
    container.querySelector('#tab-shortages-btn').className = 'btn btn-sm btn-primary';
    renderContent();
  });

  const closeDialog = () => {
    container.remove();
    onClose();
  };

  container.querySelector('#btn-close-vendor-users')?.addEventListener('click', closeDialog);
  container.querySelector('.drawer-backdrop')?.addEventListener('click', closeDialog);

  loadData();
  return container;
}
