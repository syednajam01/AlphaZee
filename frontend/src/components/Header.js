import { cart } from '../utils/cart.js';
import { createBrandLogo } from './BrandLogo.js';

export function createHeader() {
  const header = document.createElement('header');
  header.className = 'site-header';
  header.id = 'site-header';

  header.innerHTML = `
    <div class="container">
      <div class="header-inner">
        <!-- Logo Container -->
        <div class="brand-logo-container" id="header-logo-slot"></div>

        <!-- Desktop Navigation -->
        <nav class="nav-desktop" aria-label="Primary navigation">
          <a href="#featured" class="nav-link">Shop</a>
          <a href="#collections" class="nav-link">Collections</a>
          <a href="#reassurance" class="nav-link">About & Delivery</a>
          <a href="#faq" class="nav-link">FAQ</a>
        </nav>

        <!-- Right Actions -->
        <div class="header-actions">
          <button class="header-action-btn" id="btn-search" aria-label="Search catalog">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
          </button>

          <button class="header-action-btn" id="btn-cart" aria-label="Open shopping cart">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"></path>
              <line x1="3" y1="6" x2="21" y2="6"></line>
              <path d="M16 10a4 4 0 0 1-8 0"></path>
            </svg>
            <span class="cart-count-badge" id="header-cart-count" style="display: none;">0</span>
          </button>

          <button class="header-action-btn menu-toggle-btn" id="btn-mobile-menu" aria-label="Toggle mobile menu" aria-expanded="false">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="3" y1="12" x2="21" y2="12"></line>
              <line x1="3" y1="6" x2="21" y2="6"></line>
              <line x1="3" y1="18" x2="21" y2="18"></line>
            </svg>
          </button>
        </div>
      </div>
    </div>
  `;

  // Mount Brand Logo (responsive: combined on desktop 150–180px, wordmark on mobile 110–135px)
  const logoSlot = header.querySelector('#header-logo-slot');
  if (logoSlot) {
    const logo = createBrandLogo({
      variant: 'responsive-header',
      surface: 'auto',
      ariaLabel: 'AlphaZee home',
    });
    logoSlot.appendChild(logo);
  }

  // Dynamic header background on scroll
  window.addEventListener('scroll', () => {
    if (window.scrollY > 40) {
      header.classList.add('is-scrolled');
    } else {
      header.classList.remove('is-scrolled');
    }
  }, { passive: true });

  // Update cart badge from store
  cart.subscribe((state) => {
    const badge = header.querySelector('#header-cart-count');
    if (badge) {
      if (state.count > 0) {
        badge.style.display = 'flex';
        badge.textContent = state.count > 99 ? '99+' : state.count;
      } else {
        badge.style.display = 'none';
      }
    }
  });

  return header;
}
