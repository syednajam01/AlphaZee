import { createFeaturedProducts } from './FeaturedProducts.js';

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
    load({ collectionId = null } = {}) {
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
      featured.setFilter(collectionId || 'all');
    },
    destroy() {
      // Clean up if needed
    }
  };
}
