import { createBrandLogo } from './BrandLogo.js';

export function createAdminPreviewModal() {
  const modal = document.createElement('div');
  modal.className = 'modal-container';
  modal.id = 'admin-modal';
  modal.setAttribute('role', 'dialog');
  modal.setAttribute('aria-label', 'Admin Dashboard Preview');

  let isCollapsed = false;

  modal.innerHTML = `
    <div class="drawer-backdrop is-open" style="z-index: 1;"></div>
    <div class="modal-content" style="z-index: 2; max-width: 960px; height: 580px; padding: 0; display: flex; overflow: hidden; background: #181B19; color: #FFFFFF; border-radius: var(--radius-card); border: 1px solid rgba(255, 255, 255, 0.1);">
      
      <!-- Admin Sidebar -->
      <aside id="admin-sidebar" style="width: 240px; background: #111413; border-right: 1px solid rgba(255, 255, 255, 0.08); display: flex; flex-direction: column; transition: width 250ms ease;">
        <!-- Sidebar Brand Header -->
        <div style="height: 64px; display: flex; align-items: center; justify-content: space-between; padding: 0 16px; border-bottom: 1px solid rgba(255, 255, 255, 0.08);">
          <div id="admin-expanded-logo-slot" style="display: block;"></div>
          <div id="admin-collapsed-logo-slot" style="display: none;"></div>
          
          <button id="btn-toggle-admin-sidebar" class="btn-icon" style="color: rgba(255, 255, 255, 0.7);" aria-label="Toggle sidebar collapse">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
              <line x1="9" y1="3" x2="9" y2="21"></line>
            </svg>
          </button>
        </div>

        <!-- Sidebar Navigation -->
        <nav style="flex: 1; padding: 16px 8px; display: flex; flex-direction: column; gap: 4px;">
          <div class="admin-nav-item active" style="display: flex; align-items: center; gap: 12px; padding: 10px 12px; border-radius: 6px; background: rgba(20, 92, 68, 0.3); color: #FFFFFF; font-size: 0.875rem;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
            </svg>
            <span class="admin-nav-label">Overview</span>
          </div>

          <div class="admin-nav-item" style="display: flex; align-items: center; gap: 12px; padding: 10px 12px; border-radius: 6px; color: rgba(255, 255, 255, 0.7); font-size: 0.875rem;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="9" cy="21" r="1"></circle>
              <circle cx="20" cy="21" r="1"></circle>
              <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>
            </svg>
            <span class="admin-nav-label">Orders</span>
          </div>

          <div class="admin-nav-item" style="display: flex; align-items: center; gap: 12px; padding: 10px 12px; border-radius: 6px; color: rgba(255, 255, 255, 0.7); font-size: 0.875rem;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
              <polyline points="2 17 12 22 22 17"></polyline>
              <polyline points="2 12 12 17 22 12"></polyline>
            </svg>
            <span class="admin-nav-label">Products & Stock</span>
          </div>
        </nav>

        <div style="padding: 12px; border-top: 1px solid rgba(255, 255, 255, 0.08); font-size: 0.75rem; color: rgba(255, 255, 255, 0.5);">
          <span class="admin-nav-label">AlphaZee Admin v1.0</span>
        </div>
      </aside>

      <!-- Admin Main Content Area -->
      <main style="flex: 1; display: flex; flex-direction: column; overflow-y: auto;">
        <div style="height: 64px; display: flex; align-items: center; justify-content: space-between; padding: 0 24px; border-bottom: 1px solid rgba(255, 255, 255, 0.08);">
          <div style="font-size: 1rem; font-weight: 600;">Store Management Console</div>
          <button class="btn-icon" id="admin-close-btn" style="color: #FFFFFF;" aria-label="Close admin preview">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>

        <div style="padding: 24px; display: flex; flex-direction: column; gap: 20px;">
          <div style="background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 16px;">
            <h3 style="font-size: 0.875rem; font-weight: 600; margin-bottom: 6px; color: #FFFFFF;">Admin Logo Placement Verification</h3>
            <p style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.7); line-height: 1.4;">
              • <strong>Expanded Sidebar</strong>: Displays combined logo (AZ monogram + AlphaZee wordmark).<br/>
              • <strong>Collapsed Sidebar</strong>: Displays AZ symbol monogram only.<br/>
              Use the toggle icon at top of sidebar to switch between collapsed and expanded states.
            </p>
          </div>

          <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;">
            <div style="background: rgba(255, 255, 255, 0.03); border-radius: 8px; padding: 16px; border: 1px solid rgba(255, 255, 255, 0.06);">
              <div style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.5);">Today's Revenue</div>
              <div style="font-size: 1.25rem; font-weight: 700; margin-top: 4px; color: #FFFFFF;">PKR 64,800</div>
            </div>
            <div style="background: rgba(255, 255, 255, 0.03); border-radius: 8px; padding: 16px; border: 1px solid rgba(255, 255, 255, 0.06);">
              <div style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.5);">Active Orders</div>
              <div style="font-size: 1.25rem; font-weight: 700; margin-top: 4px; color: #FFFFFF;">14 Dispatched</div>
            </div>
            <div style="background: rgba(255, 255, 255, 0.03); border-radius: 8px; padding: 16px; border: 1px solid rgba(255, 255, 255, 0.06);">
              <div style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.5);">SKUs in Stock</div>
              <div style="font-size: 1.25rem; font-weight: 700; margin-top: 4px; color: #FFFFFF;">8 Active</div>
            </div>
          </div>
        </div>
      </main>
    </div>
  `;

  // 1. Mount Combined Logo in Expanded Sidebar (Dark surface, ~150px)
  const expandedSlot = modal.querySelector('#admin-expanded-logo-slot');
  if (expandedSlot) {
    const combinedLogo = createBrandLogo({
      variant: 'combined',
      surface: 'dark',
      width: 150,
      ariaLabel: 'AlphaZee admin home',
    });
    expandedSlot.appendChild(combinedLogo);
  }

  // 2. Mount AZ Symbol in Collapsed Sidebar (Dark surface, ~36px)
  const collapsedSlot = modal.querySelector('#admin-collapsed-logo-slot');
  if (collapsedSlot) {
    const symbolLogo = createBrandLogo({
      variant: 'symbol',
      surface: 'dark',
      width: 36,
      ariaLabel: 'AlphaZee admin home',
    });
    collapsedSlot.appendChild(symbolLogo);
  }

  // Sidebar collapse toggle logic
  const sidebar = modal.querySelector('#admin-sidebar');
  const toggleBtn = modal.querySelector('#btn-toggle-admin-sidebar');
  const navLabels = modal.querySelectorAll('.admin-nav-label');

  function updateSidebarState() {
    if (isCollapsed) {
      sidebar.style.width = '64px';
      expandedSlot.style.display = 'none';
      collapsedSlot.style.display = 'block';
      navLabels.forEach(el => el.style.display = 'none');
    } else {
      sidebar.style.width = '240px';
      expandedSlot.style.display = 'block';
      collapsedSlot.style.display = 'none';
      navLabels.forEach(el => el.style.display = 'inline');
    }
  }

  toggleBtn.addEventListener('click', () => {
    isCollapsed = !isCollapsed;
    updateSidebarState();
  });

  function open() {
    modal.classList.add('is-open');
    document.body.style.overflow = 'hidden';
  }

  function close() {
    modal.classList.remove('is-open');
    document.body.style.overflow = '';
  }

  modal.querySelector('.drawer-backdrop').addEventListener('click', close);
  modal.querySelector('#admin-close-btn').addEventListener('click', close);

  return {
    element: modal,
    open,
    close,
    setCollapsed: (val) => {
      isCollapsed = val;
      updateSidebarState();
    }
  };
}
