import { createBrandLogo } from './BrandLogo.js';

export function createMobileNavDrawer() {
  const backdrop = document.createElement('div');
  backdrop.className = 'drawer-backdrop';
  backdrop.id = 'mobile-nav-backdrop';

  const drawer = document.createElement('div');
  drawer.className = 'drawer';
  drawer.id = 'mobile-nav-drawer';
  drawer.setAttribute('role', 'dialog');
  drawer.setAttribute('aria-label', 'Navigation Menu');

  drawer.innerHTML = `
    <div class="drawer-header">
      <div id="mobile-drawer-logo-slot"></div>
      <button class="btn-icon" id="mobile-nav-close-btn" aria-label="Close menu">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </button>
    </div>

    <div class="drawer-body">
      <nav class="mobile-nav-list" aria-label="Mobile Navigation">
        <a href="#featured" class="mobile-nav-link">
          <span>Shop All</span>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
        </a>
        <a href="#collections" class="mobile-nav-link">
          <span>Collections</span>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
        </a>
        <a href="#reassurance" class="mobile-nav-link">
          <span>Delivery & Security</span>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
        </a>
        <a href="#faq" class="mobile-nav-link">
          <span>FAQ & Support</span>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
        </a>
      </nav>

      <div style="margin-top: 32px; padding: 20px; background-color: var(--color-bg); border-radius: var(--radius-card); border: 1px solid var(--color-border);">
        <p style="font-size: 0.875rem; font-weight: 600; margin-bottom: 8px;">Direct Assistance</p>
        <p style="font-size: 0.75rem; color: var(--color-text-muted); margin-bottom: 16px;">
          Need immediate support or custom sizing help?
        </p>
        <a href="https://wa.me/yourwhatsapp" target="_blank" rel="noopener noreferrer" class="btn btn-primary" style="width: 100%; min-height: 44px; font-size: 0.875rem; background-color: #25D366; border-color: #25D366;">
          Chat on WhatsApp
        </a>
      </div>
    </div>
  `;

  // Mount Brand Logo in Mobile Nav Drawer
  const drawerLogoSlot = drawer.querySelector('#mobile-drawer-logo-slot');
  if (drawerLogoSlot) {
    const drawerLogo = createBrandLogo({
      variant: 'combined',
      surface: 'light',
      width: 140,
      ariaLabel: 'AlphaZee home',
    });
    drawerLogoSlot.appendChild(drawerLogo);
  }

  function open() {
    backdrop.classList.add('is-open');
    drawer.classList.add('is-open');
    document.body.style.overflow = 'hidden';
  }

  function close() {
    backdrop.classList.remove('is-open');
    drawer.classList.remove('is-open');
    document.body.style.overflow = '';
  }

  backdrop.addEventListener('click', close);
  drawer.querySelector('#mobile-nav-close-btn').addEventListener('click', close);
  drawer.querySelectorAll('.mobile-nav-link').forEach(link => {
    link.addEventListener('click', close);
  });

  return {
    backdrop,
    drawer,
    open,
    close
  };
}
