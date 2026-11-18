import { createFeaturedProducts } from './FeaturedProducts.js';
import { fetchPublicStoreSettings } from '../utils/api.js';

export function createCatalogPage({ onOpenProductModal, onNavigate }) {
  const container = document.createElement('div');
  container.className = 'container section catalog-page-container';

  container.innerHTML = `
    <div class="product-breadcrumb">
      <a href="/" data-nav="/">Home</a>
      <span class="product-breadcrumb-sep">/</span>
      <span class="product-breadcrumb-current">All Products</span>
    </div>

    <div class="section-header" style="margin-top: 16px; margin-bottom: 24px;">
      <h1 class="section-title">All Products</h1>
      <p class="section-subtitle">Find a piece that feels like you. Explore our complete catalog.</p>
    </div>

    <div id="catalog-products-host"></div>
  `;

  const featured = createFeaturedProducts(onOpenProductModal, {
    preview: false,
    pageSize: 12,
    onNavigate,
  });

  // Remove the duplicate section-header from inside featuredProducts when embedded in CatalogPage
  const innerHeader = featured.element.querySelector('.section-header > div:first-child');
  if (innerHeader) {
    innerHeader.style.display = 'none';
  }

  const host = container.querySelector('#catalog-products-host');
  host.appendChild(featured.element);

  return {
    element: container,
    async load({ collectionId = null } = {}) {
      if (typeof document !== 'undefined') {
        document.title = 'All Products — AlphaZee';
        let descMeta = document.querySelector('meta[name="description"]');
        if (descMeta) {
          descMeta.setAttribute('content', 'Explore all minimalist clothing, t-shirts, hoodies, and streetwear from AlphaZee.');
        }
        let canonical = document.querySelector('link[rel="canonical"]');
        if (canonical && typeof window !== 'undefined') {
          canonical.setAttribute('href', `${window.location.origin}/products`);
        }
      }

      try {
        const settings = await fetchPublicStoreSettings().catch(() => null);
        if (settings) {
          const pageTitle = settings.products_page_title || 'All Products';
          const pageSubtitle = settings.products_page_subtitle || 'Find a piece that feels like you. Explore our complete catalog.';
          const titleEl = container.querySelector('.section-title');
          const subtitleEl = container.querySelector('.section-subtitle');
          const crumbEl = container.querySelector('.product-breadcrumb-current');
          if (titleEl) titleEl.textContent = pageTitle;
          if (subtitleEl) subtitleEl.textContent = pageSubtitle;
          if (crumbEl) crumbEl.textContent = pageTitle;
          if (typeof document !== 'undefined') {
            document.title = `${pageTitle} — AlphaZee`;
          }
        }
      } catch (err) {
        console.warn('Could not load store settings for products page headings', err);
      }

      featured.setFilter(collectionId || 'all');
    },
    destroy() {
      // Clean up if needed
    }
  };
}

