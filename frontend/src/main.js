import './styles/main.css';
import { createHeader } from './components/Header.js';
import { createHero } from './components/Hero.js';
import { createCollectionsSection } from './components/Collections.js';
import { createFeaturedProducts } from './components/FeaturedProducts.js';
import { createReassuranceAndFooter } from './components/ReassuranceFooter.js';
import { createCartDrawer } from './components/CartDrawer.js';
import { createProductModal } from './components/ProductModal.js';
import { createMobileNavDrawer } from './components/MobileNavDrawer.js';
import { createCheckoutView } from './components/CheckoutView.js';
import { createAdminPreviewModal } from './components/AdminPreview.js';
import { productsData } from './data/products.js';

function initApp() {
  const app = document.getElementById('app');
  if (!app) return;

  app.innerHTML = '';

  // 1. Create Overlays & Modals
  const checkoutView = createCheckoutView();
  const adminPreview = createAdminPreviewModal();
  const cartDrawer = createCartDrawer(() => {
    checkoutView.open();
  });
  const mobileNav = createMobileNavDrawer();
  const productModal = createProductModal(() => {
    cartDrawer.open();
  });

  // 2. Create Section Components
  const header = createHeader();

  const featuredProducts = createFeaturedProducts((product) => {
    productModal.open(product);
  });

  const hero = createHero((productId) => {
    const product = productsData.find(p => p.id === productId);
    if (product) {
      productModal.open(product);
    }
  });

  const collections = createCollectionsSection((collectionId) => {
    featuredProducts.setFilter(collectionId);
    const featuredEl = document.getElementById('featured');
    if (featuredEl) {
      featuredEl.scrollIntoView({ behavior: 'smooth' });
    }
  });

  const footer = createReassuranceAndFooter();

  // 3. Connect Header Triggers
  header.querySelector('#btn-cart')?.addEventListener('click', () => {
    cartDrawer.open();
  });

  header.querySelector('#btn-mobile-menu')?.addEventListener('click', () => {
    mobileNav.open();
  });

  header.querySelector('#btn-search')?.addEventListener('click', () => {
    const featuredEl = document.getElementById('featured');
    if (featuredEl) {
      featuredEl.scrollIntoView({ behavior: 'smooth' });
    }
  });

  // 4. Assemble Application DOM in Order specified in design.md
  app.appendChild(header);

  const main = document.createElement('main');
  main.id = 'main-content';

  main.appendChild(hero);
  main.appendChild(collections);
  main.appendChild(featuredProducts.element);
  
  app.appendChild(main);
  app.appendChild(footer);

  // Connect Admin Preview trigger in footer
  footer.querySelector('a[href="#admin"]')?.addEventListener('click', (e) => {
    e.preventDefault();
    adminPreview.open();
  });

  // Append overlay dialogs
  app.appendChild(cartDrawer.backdrop);
  app.appendChild(cartDrawer.drawer);
  app.appendChild(mobileNav.backdrop);
  app.appendChild(mobileNav.drawer);
  app.appendChild(productModal.element);
  app.appendChild(checkoutView.element);
  app.appendChild(adminPreview.element);
}

document.addEventListener('DOMContentLoaded', initApp);
