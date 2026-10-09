import { fetchProducts, fetchCollections } from '../utils/api.js';
import { formatPkr } from '../utils/money.js';
import { escapeHtml, sanitizeMediaUrl } from '../utils/dom.js';

export function createFeaturedProducts(onOpenProductModal) {
  const section = document.createElement('section');
  section.className = 'section';
  section.id = 'featured';

  let activeCategory = 'all';
  let isLoading = false;
  let errorState = null;
  let products = [];
  let collections = [];

  const container = document.createElement('div');
  container.className = 'container';

  container.innerHTML = `
    <div class="section-header" style="display: flex; flex-direction: column; gap: 16px;">
      <div>
        <h2 class="section-title">Featured Products</h2>
        <p class="section-subtitle">Minimalist designs crafted with premium materials.</p>
      </div>
      
      <!-- Category Filter Tabs -->
      <div class="filter-tabs" id="filter-tabs-container" role="tablist" style="display: flex; gap: 8px; overflow-x: auto; padding-bottom: 4px;">
        <button class="option-pill is-selected" data-filter="all" role="tab" aria-selected="true">All Products</button>
      </div>
    </div>

    <div class="products-grid" id="products-grid-container">
      <!-- Rendered dynamically -->
    </div>
  `;

  section.appendChild(container);

  const grid = container.querySelector('#products-grid-container');
  const tabsContainer = container.querySelector('#filter-tabs-container');

  function renderTabs() {
    tabsContainer.innerHTML = `
      <button class="option-pill ${activeCategory === 'all' ? 'is-selected' : ''}" data-filter="all" role="tab" aria-selected="${activeCategory === 'all'}">All Products</button>
      ${collections.map(col => `
        <button class="option-pill ${activeCategory === col.id ? 'is-selected' : ''}" data-filter="${escapeHtml(col.id)}" role="tab" aria-selected="${activeCategory === col.id}">
          ${escapeHtml(col.name)}
        </button>
      `).join('')}
    `;

    tabsContainer.querySelectorAll('button').forEach(btn => {
      btn.addEventListener('click', () => {
        const filter = btn.dataset.filter;
        if (activeCategory === filter) return;
        activeCategory = filter;
        renderTabs();
        loadProducts();
      });
    });
  }

  function renderGrid() {
    if (isLoading) {
      grid.innerHTML = Array.from({ length: 4 }).map(() => `
        <div class="catalog-skeleton-card">
          <div class="catalog-skeleton-img"></div>
          <div class="catalog-skeleton-text" style="width: 60%;"></div>
          <div class="catalog-skeleton-text" style="width: 40%;"></div>
        </div>
      `).join('');
      return;
    }

    if (errorState) {
      grid.innerHTML = `
        <div class="catalog-status-box is-error">
          <div class="catalog-status-title">Unable to load catalog products</div>
          <div class="catalog-status-desc">${escapeHtml(errorState)}</div>
          <button class="btn btn-secondary btn-retry" style="margin-top: 8px;">
            Retry Connection
          </button>
        </div>
      `;

      grid.querySelector('.btn-retry')?.addEventListener('click', () => {
        loadProducts();
      });
      return;
    }

    if (!products || products.length === 0) {
      grid.innerHTML = `
        <div class="catalog-status-box">
          <div class="catalog-status-title">No products found</div>
          <div class="catalog-status-desc">There are currently no active products in this collection.</div>
        </div>
      `;
      return;
    }

    grid.innerHTML = products.map(product => {
      const safeTitle = escapeHtml(product.title);
      const safeImage = sanitizeMediaUrl(product.image_url, 'https://images.unsplash.com/photo-1521572267360-ee0c2909d518?auto=format&fit=crop&w=800&q=80');
      const safeBadge = product.badge ? escapeHtml(product.badge) : 'In Stock';
      const formattedPrice = formatPkr(product.min_price_minor);

      return `
        <article class="product-card" id="product-${escapeHtml(product.id)}">
          <div class="product-card-img-wrapper">
            <span class="badge badge-neutral product-card-badge">${safeBadge}</span>
            <img 
              src="${safeImage}" 
              alt="${safeTitle}" 
              class="product-card-img" 
              loading="lazy"
              width="320"
              height="320"
            />
          </div>
          <div class="product-card-info">
            <h3 class="product-card-title">${safeTitle}</h3>
            <div class="product-card-price-row">
              <span class="product-card-price">${formattedPrice}</span>
              <span class="product-card-status">Ready to ship</span>
            </div>
            <button 
              class="btn btn-secondary product-card-btn" 
              data-slug="${escapeHtml(product.slug)}"
              data-id="${escapeHtml(product.id)}"
              aria-label="View options for ${safeTitle}">
              View Options
            </button>
          </div>
        </article>
      `;
    }).join('');

    // Attach card click handlers
    grid.querySelectorAll('.product-card-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const slug = btn.dataset.slug;
        const prod = products.find(p => p.slug === slug);
        if (onOpenProductModal) {
          onOpenProductModal(prod || slug);
        }
      });
    });
  }

  async function loadCollections() {
    try {
      const cols = await fetchCollections();
      collections = Array.isArray(cols) ? cols : [];
      renderTabs();
    } catch {
      // If collections fail, keep the "All Products" tab
    }
  }

  async function loadProducts() {
    isLoading = true;
    errorState = null;
    renderGrid();

    try {
      const res = await fetchProducts({
        collectionId: activeCategory === 'all' ? null : activeCategory,
      });
      products = res?.products || [];
      isLoading = false;
      renderGrid();
    } catch (err) {
      isLoading = false;
      errorState = err.message || 'Could not connect to product catalog.';
      renderGrid();
    }
  }

  // Initial load
  loadCollections();
  loadProducts();

  return {
    element: section,
    setFilter: (category) => {
      activeCategory = category;
      renderTabs();
      loadProducts();
    },
    reload: () => {
      loadCollections();
      loadProducts();
    }
  };
}
