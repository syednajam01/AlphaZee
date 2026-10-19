import { fetchProducts, fetchCollections } from '../utils/api.js';
import { formatDisplayPrice, extractPriceMinor } from '../utils/money.js';
import { escapeHtml, sanitizeMediaUrl, createSafeImageElement } from '../utils/dom.js';

export function createFeaturedProducts(onOpenProductModal) {
  const section = document.createElement('section');
  section.className = 'section';
  section.id = 'featured';

  let activeCategory = 'all';
  let activeSort = 'featured';
  try {
    const savedFilter = window?.sessionStorage?.getItem('alphazee_catalog_filter');
    if (savedFilter) activeCategory = savedFilter;
    const savedSort = window?.sessionStorage?.getItem('alphazee_catalog_sort');
    if (savedSort) activeSort = savedSort;
  } catch {}

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
        <h2 class="section-title">Featured Pieces</h2>
        <p class="section-subtitle">Architectural streetwear crafted with heavyweight fabrics in Karachi, Pakistan.</p>
      </div>
      
      <!-- Category Filter Tabs & Sorting Controls -->
      <div class="catalog-controls-bar">
        <div class="filter-tabs" id="filter-tabs-container" role="tablist">
          <button class="option-pill is-selected" data-filter="all" role="tab" aria-selected="true">All Products</button>
        </div>
        <div class="catalog-sort-group">
          <label for="catalog-sort" class="form-label" style="margin: 0; font-size: 0.85rem; color: var(--color-text-muted);">Sort By</label>
          <select id="catalog-sort" class="form-select sort-select" aria-label="Sort catalog pieces">
            <option value="featured">Featured</option>
            <option value="price-asc">Price: Low to High</option>
            <option value="price-desc">Price: High to Low</option>
            <option value="name-asc">Name: A to Z</option>
          </select>
        </div>
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
  const sortSelect = container.querySelector('#catalog-sort');
  if (sortSelect) {
    sortSelect.value = activeSort;
    sortSelect.addEventListener('change', () => {
      activeSort = sortSelect.value;
      try { window?.sessionStorage?.setItem('alphazee_catalog_sort', activeSort); } catch {}
      renderGrid();
    });
  }

  function sortProducts(items, sortKey) {
    const list = [...items];
    if (sortKey === 'price-asc') {
      list.sort((a, b) => {
        const pa = extractPriceMinor(a.min_price ?? a.min_price_minor) ?? 0;
        const pb = extractPriceMinor(b.min_price ?? b.min_price_minor) ?? 0;
        return pa - pb;
      });
    } else if (sortKey === 'price-desc') {
      list.sort((a, b) => {
        const pa = extractPriceMinor(a.min_price ?? a.min_price_minor) ?? 0;
        const pb = extractPriceMinor(b.min_price ?? b.min_price_minor) ?? 0;
        return pb - pa;
      });
    } else if (sortKey === 'name-asc') {
      list.sort((a, b) => (a.title || '').localeCompare(b.title || ''));
    }
    return list;
  }

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
        try { window?.sessionStorage?.setItem('alphazee_catalog_filter', activeCategory); } catch {}
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

    const displayProducts = sortProducts(products, activeSort);

    grid.innerHTML = displayProducts.map(product => {
      const safeTitle = escapeHtml(product.title);
      const safeBadge = product.badge ? escapeHtml(product.badge) : null;
      const formattedPrice = formatDisplayPrice(product.min_price ?? product.min_price_minor);
      const productHref = `/products/${encodeURIComponent(product.slug)}`;

      return `
        <article class="product-card" id="product-${escapeHtml(product.id)}">
          <a href="${productHref}" data-slug="${escapeHtml(product.slug)}" class="product-card-media-link" aria-label="View ${safeTitle}">
            <div class="product-card-img-wrapper">
              ${safeBadge ? `<span class="badge badge-neutral product-card-badge">${safeBadge}</span>` : ''}
            </div>
          </a>
          <div class="product-card-info">
            <h3 class="product-card-title">
              <a href="${productHref}" data-slug="${escapeHtml(product.slug)}" class="product-card-title-link">${safeTitle}</a>
            </h3>
            <div class="product-card-price-row">
              <span class="product-card-price price-tabular">${formattedPrice}</span>
              ${product.availability === 'unavailable' ? '<span class="badge badge-neutral">Currently unavailable</span>' : ''}
            </div>
            <a 
              href="${productHref}"
              class="btn btn-secondary product-card-btn" 
              data-slug="${escapeHtml(product.slug)}"
              data-id="${escapeHtml(product.id)}"
              aria-label="View options for ${safeTitle}">
              View Options
            </a>
          </div>
        </article>
      `;
    }).join('');

    // Prepend safe images with 3:4 aspect ratio and hover crossfade via DOM properties
    displayProducts.forEach(product => {
      const card = grid.querySelector(`#product-${product.id}`);
      const wrapper = card?.querySelector('.product-card-img-wrapper');
      if (wrapper && !wrapper.querySelector('.product-card-img')) {
        const hoverUrl = product.hover_image_url || product.secondary_image_url || null;

        const primaryImg = createSafeImageElement({
          src: product.image_url,
          alt: product.image_alt || product.title || 'Product',
          className: 'product-card-img product-card-img-primary' + (hoverUrl ? ' has-secondary' : ''),
          loading: 'lazy',
          width: 320,
          height: 426,
        });
        wrapper.appendChild(primaryImg);

        if (hoverUrl) {
          const secondaryImg = createSafeImageElement({
            src: hoverUrl,
            alt: `${product.title} alternate view`,
            className: 'product-card-img product-card-img-secondary',
            loading: 'lazy',
            width: 320,
            height: 426,
          });
          wrapper.appendChild(secondaryImg);
        }
      }
    });

    // Attach quick view modal only to .product-card-btn; title and media links navigate to /products/:slug
    grid.querySelectorAll('.product-card-btn').forEach(link => {
      link.addEventListener('click', (e) => {
        if (e && (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey)) return;
        const slug = link.dataset?.slug || (link.getAttribute ? link.getAttribute('data-slug') : null);
        const prod = products.find(p => p.slug === slug);
        if (onOpenProductModal) {
          if (e?.preventDefault) e.preventDefault();
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

