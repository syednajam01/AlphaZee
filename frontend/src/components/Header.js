import { cart } from '../utils/cart.js';
import { capabilities } from '../utils/capabilities.js';
import { fetchPublicStoreSettings } from '../utils/api.js';
import { createBrandLogo } from './BrandLogo.js';

export function createHeader() {
  const header = document.createElement('header');
  header.className = 'site-header';
  header.id = 'site-header';

  header.innerHTML = `
    <!-- Store Announcement Bar -->
    <div class="announcement-bar" role="region" aria-label="Store announcement" style="display: none;">
      <span>AlphaZee preview - browse and save your cart. Checkout is temporarily unavailable.</span>
    </div>

    <div class="container">
      <div class="header-inner">
        <!-- Logo Container -->
        <div class="brand-logo-container" id="header-logo-slot"></div>

        <!-- Desktop Navigation -->
        <nav class="nav-desktop" aria-label="Primary navigation">
          <a href="#featured" class="nav-link">Shop</a>
          <a href="#collections" class="nav-link">Collections</a>
          <a href="#track" id="nav-track-order" class="nav-link">Track Order</a>
          <a href="#reassurance" class="nav-link">About & Delivery</a>
          <a href="#faq" class="nav-link">FAQ</a>
        </nav>

        <!-- Right Actions -->
        <div class="header-actions">
          <button class="header-action-btn" id="btn-browse-catalog" aria-label="Browse catalog" title="Browse catalog">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="3" width="7" height="7" rx="1"></rect>
              <rect x="14" y="3" width="7" height="7" rx="1"></rect>
              <rect x="3" y="14" width="7" height="7" rx="1"></rect>
              <rect x="14" y="14" width="7" height="7" rx="1"></rect>
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

  // Dynamic header background on scroll (rAF-throttled to avoid layout reflows on every pixel)
  let isScrolled = false;
  let scrollTicking = false;
  window.addEventListener('scroll', () => {
    if (!scrollTicking) {
      window.requestAnimationFrame(() => {
        const shouldBeScrolled = window.scrollY > 40;
        if (shouldBeScrolled !== isScrolled) {
          isScrolled = shouldBeScrolled;
          if (isScrolled) {
            header.classList.add('is-scrolled');
          } else {
            header.classList.remove('is-scrolled');
          }
        }
        scrollTicking = false;
      });
      scrollTicking = true;
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

  // Dynamic Store Settings & Announcement Bar (VF6)
  let publicSettings = null;
  const announcementBar = header.querySelector('.announcement-bar');
  const announcementSpan = announcementBar?.querySelector('span');

  function updateAnnouncement(checkoutEnabled, testMode = capabilities.getState().testMode) {
    if (!announcementBar || !announcementSpan) return;

    if (!publicSettings || publicSettings.announcement_banner_enabled === false || !publicSettings.announcement_banner_text) {
      announcementBar.style.display = 'none';
      return;
    }

    announcementBar.style.display = 'block';
    if (publicSettings && publicSettings.accent_color) {
      announcementBar.style.backgroundColor = publicSettings.accent_color;
    }

    const customText = publicSettings?.announcement_banner_text;
    if (testMode) {
      announcementSpan.textContent = customText
        ? `AlphaZee SAMPLE / TEST: ${customText}`
        : 'AlphaZee SAMPLE / TEST store - no real orders';
    } else {
      announcementSpan.textContent = customText || (checkoutEnabled ? 'Discover your next piece with AlphaZee.' : 'AlphaZee preview - browse and save your cart. Checkout is temporarily unavailable.');
    }

    if (publicSettings?.announcement_banner_link) {
      announcementBar.style.cursor = 'pointer';
      announcementBar.onclick = () => {
        window.location.hash = publicSettings.announcement_banner_link;
      };
    }
  }

  fetchPublicStoreSettings().then(settings => {
    publicSettings = settings;
    const root = document.documentElement;
    if (settings.font_family) root.style.setProperty('--font-family', settings.font_family);
    const radius = { none: '0px', sm: '4px', md: '8px', lg: '16px', full: '999px' }[settings.border_radius];
    if (radius) { root.style.setProperty('--radius-btn', radius); root.style.setProperty('--radius-control', radius); }
    root.dataset.storeSpacing = settings.spacing_density || 'comfortable';
    updateAnnouncement(capabilities.getState().checkoutEnabled);
  }).catch(() => {
    // Graceful fallback to default message if offline
  });

  capabilities.subscribe(({ checkoutEnabled }) => {
    updateAnnouncement(checkoutEnabled);
  });

  // Active navigation link tracking
  function setActiveNav(targetHref) {
    const navLinks = header.querySelectorAll('.nav-desktop .nav-link');
    navLinks.forEach(link => {
      const href = link.getAttribute?.('href');
      if (targetHref && href === targetHref) {
        link.classList?.add?.('is-active');
        link.setAttribute?.('aria-current', 'page');
      } else {
        link.classList?.remove?.('is-active');
        if (typeof link.removeAttribute === 'function') {
          link.removeAttribute('aria-current');
        } else {
          link.setAttribute?.('aria-current', 'false');
        }
      }
    });
  }

  // Observe home page sections when on the storefront home
  if (typeof IntersectionObserver !== 'undefined' && typeof window !== 'undefined') {
    const sectionObserver = new IntersectionObserver((entries) => {
      if (window.location.pathname.startsWith('/products/')) {
        setActiveNav(null);
        return;
      }
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          setActiveNav(`#${entry.target.id}`);
        }
      });
    }, {
      rootMargin: '-20% 0px -65% 0px',
      threshold: 0
    });

    const observeSections = () => {
      ['featured', 'collections', 'reassurance', 'faq'].forEach(id => {
        const el = document.getElementById(id);
        if (el) sectionObserver.observe(el);
      });
    };

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', observeSections, { once: true });
    } else {
      setTimeout(observeSections, 100);
    }
  }

  header.setActiveNav = setActiveNav;

  return header;
}
