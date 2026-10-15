import { capabilities } from './utils/capabilities.js';
import { cart } from './utils/cart.js';
import { captureLandingUtmParams } from './utils/utm.js';
import { createHeader } from './components/Header.js';
import { createHero } from './components/Hero.js';
import { createCollectionsSection } from './components/Collections.js';
import { createFeaturedProducts } from './components/FeaturedProducts.js';
import { createReassuranceAndFooter } from './components/ReassuranceFooter.js';
import { createCartDrawer } from './components/CartDrawer.js';
import { createProductModal } from './components/ProductModal.js';
import { createMobileNavDrawer } from './components/MobileNavDrawer.js';
import { createCheckoutView } from './components/CheckoutView.js';
import { createOrderTrackingModal } from './components/OrderTrackingModal.js';

export function initApp() {
  capabilities.refresh();
  captureLandingUtmParams();
  const app = document.getElementById('app');
  if (!app) return;

  app.innerHTML = '';

  // 1. Create Overlays & Modals
  const checkoutView = createCheckoutView();
  const orderTracking = createOrderTrackingModal();
  const cartDrawer = createCartDrawer(() => {
    checkoutView.open();
  });
  const mobileNav = createMobileNavDrawer();
  const productModal = createProductModal(() => {
    cartDrawer.open();
  });

  // 2. Create Section Components
  const header = createHeader();

  const featuredProducts = createFeaturedProducts((productOrSlug) => {
    productModal.open(productOrSlug);
  });

  const hero = createHero((slugOrId) => {
    productModal.open(slugOrId);
  });

  const collections = createCollectionsSection((collectionId) => {
    featuredProducts.setFilter(collectionId);
    const featuredEl = document.getElementById('featured');
    if (featuredEl) {
      featuredEl.scrollIntoView({ behavior: 'smooth' });
    }
  });

  const footer = createReassuranceAndFooter();

  // 3. Connect Header & Navigation Triggers
  header.querySelector('#btn-cart')?.addEventListener('click', () => {
    cartDrawer.open();
  });

  header.querySelector('#btn-mobile-menu')?.addEventListener('click', () => {
    mobileNav.open();
  });

  header.querySelector('#btn-browse-catalog')?.addEventListener('click', () => {
    const featuredEl = document.getElementById('featured');
    if (featuredEl) {
      featuredEl.scrollIntoView({ behavior: 'smooth' });
    }
  });

  // 4. Assemble Application DOM
  app.appendChild(header);

  const main = document.createElement('main');
  main.id = 'main-content';

  main.appendChild(hero);
  main.appendChild(collections);
  main.appendChild(featuredProducts.element);
  
  app.appendChild(main);
  app.appendChild(footer);


  // Append overlay dialogs
  app.appendChild(cartDrawer.backdrop);
  app.appendChild(cartDrawer.drawer);
  app.appendChild(mobileNav.backdrop);
  app.appendChild(mobileNav.drawer);
  app.appendChild(productModal.element);
  app.appendChild(checkoutView.element);
  app.appendChild(orderTracking.element);

  // Header, footer and mobile links all open the same tracking flow.
  app.querySelectorAll('a[href="#track"]').forEach(link => {
    link.addEventListener('click', event => {
      event.preventDefault();
      mobileNav.close();
      orderTracking.open();
    });
  });

  // Other owner tabs announce accepted catalog changes. Focus/page restoration
  // also refetches so browser history and changes from another device recover.
  let refreshTimer;
  const refresh = () => {
    clearTimeout(refreshTimer);
    refreshTimer = setTimeout(() => {
      if (document.visibilityState === 'hidden') return;
      hero.reload(); collections.reload(); featuredProducts.reload();
      productModal.refresh(); cart.reconcileWithApi();
    }, 100);
  };
  const storage = event => { if (event.key === 'alphazee_catalog_changed') refresh(); };
  const visible = () => { if (document.visibilityState !== 'hidden') refresh(); };
  window.addEventListener?.('storage', storage);
  window.addEventListener?.('focus', refresh);
  window.addEventListener?.('pageshow', refresh);
  window.addEventListener?.('alphazee:catalog-change', refresh);
  document.addEventListener?.('visibilitychange', visible);
  return { destroy() {
    clearTimeout(refreshTimer); hero.destroy(); productModal.close();
    window.removeEventListener?.('storage', storage); window.removeEventListener?.('focus', refresh);
    window.removeEventListener?.('pageshow', refresh); window.removeEventListener?.('alphazee:catalog-change', refresh);
    document.removeEventListener?.('visibilitychange', visible);
  } };
}


