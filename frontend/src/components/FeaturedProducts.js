import { fetchProducts, fetchCollections } from '../utils/api.js';
import { formatDisplayPrice } from '../utils/money.js';
import { escapeHtml, sanitizeMediaUrl, createSafeImageElement } from '../utils/dom.js';

export function createFeaturedProducts(onOpenProductModal) {
  const section = document.createElement('section');
  section.className = 'section';
  section.id = 'featured';

  let activeCategory = 'all';
  let currentPage = 1;
  const pageSize = 12;
  let totalProducts = 0;
  let isLoading = false;
  let isLoadingMore = false;
  let errorState = null;
  let products = [];
  let collections = [];
  let activeRequestId = 0;

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

    <div class="pagination-container" id="pagination-container" style="display: flex; justify-content: center; margin-top: 32px;">
      <!-- Load more button rendered dynamically -->
    </div>
  `;

  section.appendChild(container);

  const grid = container.querySelector('#products-grid-container');
  const tabsContainer = container.querySelector('#filter-tabs-container');
  const paginationContainer = container.querySelector('#pagination-container');

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
        loadProducts({ reset: true });
      });
    });
  }

  function renderPagination() {
    if (!paginationContainer) return;

    if (isLoading || errorState || !products || products.length === 0) {
      paginationContainer.innerHTML = '';
      return;
    }

    if (products.length < totalProducts) {
      paginationContainer.innerHTML = `
        <button class="btn btn-secondary btn-load-more" id="btn-load-more" ${isLoadingMore ? 'disabled' : ''} style="min-width: 200px;">
          ${isLoadingMore ? 'Loading Pieces...' : `Load More Products (${products.length} of ${totalProducts})`}
        </button>
      `;

      paginationContainer.querySelector('#btn-load-more')?.addEventListener('click', () => {
        if (isLoadingMore) return;
        currentPage++;
        loadProducts({ reset: false });
      });
    } else if (totalProducts > 0) {
      paginationContainer.innerHTML = `
        <span class="catalog-status-desc" style="color: var(--color-text-muted); font-size: 0.85rem;">
          Showing all ${totalProducts} pieces
        </span>
      `;
    } else {
      paginationContainer.innerHTML = '';
    }
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
      renderPagination();
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
        loadProducts({ reset: true });
      });
      renderPagination();
      return;
    }

    if (!products || products.length === 0) {
      grid.innerHTML = `
        <div class="catalog-status-box">
          <div class="catalog-status-title">No products found</div>
          <div class="catalog-status-desc">There are currently no active products in this collection.</div>
        </div>
      `;
      renderPagination();
      return;
    }

    grid.innerHTML = products.map(product => {
      const safeTitle = escapeHtml(product.title);
      const safeBadge = product.badge ? escapeHtml(product.badge) : null;
      const formattedPrice = formatDisplayPrice(product.min_price ?? product.min_price_minor);

      return `
        <article class="product-card" id="product-${escapeHtml(product.id)}">
          <div class="product-card-img-wrapper">
            ${safeBadge ? `<span class="badge badge-neutral product-card-badge">${safeBadge}</span>` : ''}
          </div>
          <div class="product-card-info">
            <h3 class="product-card-title">${safeTitle}</h3>
            <div class="product-card-price-row">
              <span class="product-card-price">${formattedPrice}</span>
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

    // Prepend safe images via DOM properties
    products.forEach(product => {
      const card = grid.querySelector(`#product-${product.id}`);
      const wrapper = card?.querySelector('.product-card-img-wrapper');
      if (wrapper && !wrapper.querySelector('.product-card-img')) {
        wrapper.appendChild(
          createSafeImageElement({
            src: product.image_url,
            alt: product.title || 'Product',
            className: 'product-card-img',
            loading: 'lazy',
            width: 320,
            height: 320,
          })
        );
      }
    });

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

    renderPagination();
  }

  async function loadCollections() {
    try {
      const cols = await fetchCollections();
      collections = Array.isArray(cols) ? cols : (Array.isArray(cols?.collections) ? cols.collections : []);
      renderTabs();
    } catch {
      // If collections fail, keep the "All Products" tab
    }
  }

  async function loadProducts({ reset = true } = {}) {
    if (reset) {
      currentPage = 1;
      products = [];
      totalProducts = 0;
      isLoading = true;
      isLoadingMore = false;
      errorState = null;
      renderGrid();
    } else {
      isLoadingMore = true;
      renderPagination();
    }

    const thisReqId = ++activeRequestId;

    try {
      const res = await fetchProducts({
        collectionId: activeCategory === 'all' ? null : activeCategory,
        page: currentPage,
        pageSize,
      });

      if (thisReqId !== activeRequestId) return; // Discard stale response

      const newItems = res?.products || [];
      if (reset) {
        products = newItems;
      } else {
        const existingIds = new Set(products.map(p => p.id));
        const filteredNew = newItems.filter(p => !existingIds.has(p.id));
        products = [...products, ...filteredNew];
      }

      totalProducts = typeof res?.total === 'number' ? res.total : products.length;
      isLoading = false;
      isLoadingMore = false;
      renderGrid();
    } catch (err) {
      if (thisReqId !== activeRequestId) return;
      isLoading = false;
      isLoadingMore = false;
      errorState = err.message || 'Could not connect to product catalog.';
      renderGrid();
    }
  }

  // Initial load
  loadCollections();
  loadProducts({ reset: true });

  return {
    element: section,
    setFilter: (category) => {
      activeCategory = category;
      renderTabs();
      loadProducts({ reset: true });
    },
    reload: () => {
      loadCollections();
      loadProducts({ reset: true });
    }
  };
}

