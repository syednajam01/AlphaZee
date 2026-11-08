import { capabilities } from './utils/capabilities.js';
import { cart } from './utils/cart.js';
import { captureLandingUtmParams } from './utils/utm.js';
import { createHeader } from './components/Header.js';
import { createHero } from './components/Hero.js';
import { createCollectionsSection } from './components/Collections.js';
import { createCollectionsPage } from './components/CollectionsPage.js';
import { createCollectionProductsPage } from './components/CollectionProductsPage.js';
import { createCatalogPage } from './components/CatalogPage.js';
import { createFeaturedProducts } from './components/FeaturedProducts.js';
import { createProductPage } from './components/ProductPage.js';
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
  app.classList?.add('storefront');

  app.innerHTML = '';

  // 1. Create Overlays & Modals
  const checkoutView = createCheckoutView();
  const orderTracking = createOrderTrackingModal();
  const cartDrawer = createCartDrawer(
    () => {
      checkoutView.open();
    },
    () => {
      if (typeof window !== 'undefined' && window.location?.pathname !== '/') {
        navigate('/');
        setTimeout(() => {
          document.getElementById('featured')?.scrollIntoView({ behavior: 'smooth' });
        }, 50);
      } else {
        document.getElementById('featured')?.scrollIntoView({ behavior: 'smooth' });
      }
    }
  );
  const mobileNav = createMobileNavDrawer();
  const productModal = createProductModal(() => {
    cartDrawer.open();
  });

  // 2. Client-side Router State & Functions
  function parseRoute() {
    if (typeof window === 'undefined' || !window.location || typeof window.location.pathname !== 'string') {
      return { type: 'home' };
    }
    const path = window.location.pathname.replace(/\/+$/, '') || '/';
    const search = window.location.search || '';
    const params = new URLSearchParams(search);

    // Single product: /products/:slug
    if (path.startsWith('/products/')) {
      const rawSlug = path.slice('/products/'.length);
      const slug = decodeURIComponent(rawSlug);
      if (slug) {
        const variantId = params.get('variant');
        return { type: 'product', slug, variantId };
      }
      return { type: 'all_products' };
    }

    // All products catalog: /products
    if (path === '/products') {
      const collectionId = params.get('collection') || null;
      return { type: 'all_products', collectionId };
    }

    // Collection products: /collections/:slugOrId
    if (path.startsWith('/collections/')) {
      const rawSlug = path.slice('/collections/'.length);
      const slugOrId = decodeURIComponent(rawSlug);
      if (slugOrId) {
        return { type: 'collection_products', slugOrId };
      }
      return { type: 'collections' };
    }

    // All collections: /collections
    if (path === '/collections') {
      return { type: 'collections' };
    }

    return { type: 'home' };
  }

  function navigate(url, { replace = false } = {}) {
    if (typeof window === 'undefined') return;
    if (replace) {
      if (typeof window.history?.replaceState === 'function') {
        window.history.replaceState(null, '', url);
      }
    } else {
      if (typeof window.history?.pushState === 'function') {
        window.history.pushState(null, '', url);
      }
    }
    // Only in mock Node test environments lacking native pushState synchronization, update mock location
    if (!window.history?.pushState && typeof window.location === 'object' && window.location !== null) {
      try {
        const u = new URL(url, 'http://localhost');
        window.location.pathname = u.pathname;
        window.location.search = u.search;
      } catch (_) {}
    }
    renderRoute();
  }

  // 3. Create Section Components
  const header = createHeader();

  const productPage = createProductPage({
    onAddedToCart: () => cartDrawer.open(),
    onNavigate: (url) => navigate(url),
  });

  const collectionsPage = createCollectionsPage({
    onSelectCollection: (slugOrId) => navigate(`/collections/${encodeURIComponent(slugOrId)}`),
    onNavigate: (url) => navigate(url),
  });

  const collectionProductsPage = createCollectionProductsPage({
    onOpenProductModal: (prodOrSlug) => productModal.open(prodOrSlug),
    onNavigate: (url) => navigate(url),
  });

  const catalogPage = createCatalogPage({
    onOpenProductModal: (prodOrSlug) => productModal.open(prodOrSlug),
    onNavigate: (url) => navigate(url),
  });

  // Homepage preview of products: 6 products, no filter tabs, no sort, with "Explore all pieces" button
  const featuredProducts = createFeaturedProducts((productOrSlug) => {
    productModal.open(productOrSlug);
  }, {
    preview: true,
    pageSize: 6,
    onNavigate: (url) => navigate(url),
  });

  const hero = createHero((slugOrId) => {
    productModal.open(slugOrId);
  });

  // Homepage collections: max 3 collections, with "View all collections" button if > 3
  const collections = createCollectionsSection((slugOrId) => {
    navigate(`/collections/${encodeURIComponent(slugOrId)}`);
  }, {
    limit: 3,
    onNavigate: (url) => navigate(url),
  });

  const footer = createReassuranceAndFooter();

  // 4. Connect Header & Navigation Triggers
  header.querySelector('#btn-cart')?.addEventListener('click', () => {
    cartDrawer.open();
  });

  header.querySelector('#btn-mobile-menu')?.addEventListener('click', () => {
    mobileNav.open();
  });

  header.querySelector('#btn-browse-catalog')?.addEventListener('click', () => {
    if (typeof window !== 'undefined' && window.location?.pathname && window.location.pathname !== '/') {
      navigate('/');
      setTimeout(() => {
        document.getElementById('featured')?.scrollIntoView({ behavior: 'smooth' });
      }, 50);
    } else {
      document.getElementById('featured')?.scrollIntoView({ behavior: 'smooth' });
    }
  });

  // 5. Assemble Application DOM
  app.appendChild(header);

  const main = document.createElement('main');
  main.id = 'main-content';
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

  // Route Rendering
  function renderRoute() {
    const route = parseRoute();
    main.innerHTML = '';
    header.setActiveNav?.(null);

    const scrollToTop = () => {
      if (typeof window !== 'undefined' && typeof window.scrollTo === 'function') {
        window.scrollTo(0, 0);
      }
    };

    if (route.type === 'product') {
      productPage.destroy();
      collectionsPage.destroy();
      collectionProductsPage.destroy();
      catalogPage.destroy();
      main.appendChild(productPage.element);
      productPage.load(route.slug, route.variantId);
      scrollToTop();
    } else if (route.type === 'collections') {
      productPage.destroy();
      collectionsPage.destroy();
      collectionProductsPage.destroy();
      catalogPage.destroy();
      main.appendChild(collectionsPage.element);
      collectionsPage.load();
      scrollToTop();
    } else if (route.type === 'collection_products') {
      productPage.destroy();
      collectionsPage.destroy();
      collectionProductsPage.destroy();
      catalogPage.destroy();
      main.appendChild(collectionProductsPage.element);
      collectionProductsPage.load(route.slugOrId);
      scrollToTop();
    } else if (route.type === 'all_products') {
      productPage.destroy();
      collectionsPage.destroy();
      collectionProductsPage.destroy();
      catalogPage.destroy();
      main.appendChild(catalogPage.element);
      catalogPage.load({ collectionId: route.collectionId });
      scrollToTop();
    } else {
      productPage.destroy();
      collectionsPage.destroy();
      collectionProductsPage.destroy();
      catalogPage.destroy();
      main.appendChild(hero);
      main.appendChild(collections);
      main.appendChild(featuredProducts.element);
      document.title = 'AlphaZee — Modern Apparel & Curated Essentials';

      // Cleanly reset route metadata
      const descMeta = document.querySelector('meta[name="description"]');
      if (descMeta) {
        descMeta.setAttribute('content', 'Minimalist streetwear crafted in Pakistan. Premium cotton, structured fits, and zero compromises.');
      }
      let canonical = document.querySelector('link[rel="canonical"]');
      if (!canonical && typeof document !== 'undefined' && document.head) {
        canonical = document.createElement('link');
        canonical.setAttribute('rel', 'canonical');
        document.head.appendChild(canonical);
      }
      if (canonical && typeof window !== 'undefined') {
        canonical.setAttribute('href', `${window.location.origin}/`);
      }
      scrollToTop();
    }
  }

  // Initial Route Render
  renderRoute();

  // Popstate Listener (Back / Forward navigation)
  const handlePopState = () => {
    renderRoute();
  };
  window.addEventListener?.('popstate', handlePopState);

  // Delegated internal link navigation (handles brand logo, Shop link, /products links, /collections links)
  const handleDelegatedLinks = (event) => {
    if (event.defaultPrevented || (event.button !== undefined && event.button !== 0) || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return;
    }
    const anchor = event.target.closest('a');
    if (!anchor) return;
    const href = anchor.getAttribute('href');
    if (!href) return;

    if (href === '/products' || href === '/collections' || href.startsWith('/collections/') || href.startsWith('/products/')) {
      if (anchor.classList.contains('product-card-btn')) {
        return;
      }
      event.preventDefault();
      mobileNav.close();
      navigate(href);
    } else if (href === '/' || anchor.getAttribute('data-nav') === '/') {
      event.preventDefault();
      mobileNav.close();
      navigate('/');
      if (typeof window !== 'undefined' && typeof window.scrollTo === 'function') {
        window.scrollTo({ top: 0, left: 0, behavior: 'smooth' });
      }
    } else if (href === '#featured' || href === '#collections' || href === '#reassurance' || href === '#faq') {
      const isSubpage = typeof window !== 'undefined' && window.location?.pathname !== '/';
      if (isSubpage) {
        event.preventDefault();
        mobileNav.close();
        navigate('/');
        const targetId = href;
        setTimeout(() => {
          document.querySelector(targetId)?.scrollIntoView({ behavior: 'smooth' });
        }, 50);
      }
    }
  };
  app.addEventListener('click', handleDelegatedLinks);

  // Header, footer and mobile links for tracking
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
      const route = parseRoute();
      if (route.type === 'product') {
        productPage.load(route.slug, route.variantId);
      } else if (route.type === 'collections') {
        collectionsPage.load();
      } else if (route.type === 'collection_products') {
        collectionProductsPage.load(route.slugOrId);
      } else if (route.type === 'all_products') {
        catalogPage.load({ collectionId: route.collectionId });
      }
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

  return {
    destroy() {
      clearTimeout(refreshTimer);
      hero.destroy();
      productModal.close();
      productPage.destroy();
      collectionsPage.destroy();
      collectionProductsPage.destroy();
      catalogPage.destroy();
      window.removeEventListener?.('popstate', handlePopState);
      app.removeEventListener?.('click', handleDelegatedLinks);
      window.removeEventListener?.('storage', storage);
      window.removeEventListener?.('focus', refresh);
      window.removeEventListener?.('pageshow', refresh);
      window.removeEventListener?.('alphazee:catalog-change', refresh);
      document.removeEventListener?.('visibilitychange', visible);
    }
  };
}
