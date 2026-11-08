import { fetchCollections, fetchProducts } from '../utils/api.js';
import { formatDisplayPrice } from '../utils/money.js';
import { escapeHtml, sanitizeMediaUrl, createSafeImageElement } from '../utils/dom.js';

export function createCollectionProductsPage({ onOpenProductModal, onNavigate }) {
  const container = document.createElement('div');
  container.className = 'container section collection-products-page-container';

  let currentSlugOrId = null;
  let currentCollection = null;
  let products = [];
  let totalProducts = 0;
  let currentPage = 1;
  const pageSize = 6; // For speed as requested
  let isLoading = false;
  let isLoadingMore = false;
  let errorState = null;
  let activeRequestId = 0;

  function renderSkeleton() {
    container.innerHTML = `
      <div class="product-breadcrumb">
        <a href="/" data-nav="/">Home</a>
        <span class="product-breadcrumb-sep">/</span>
        <a href="/collections" data-nav="/collections">Collections</a>
        <span class="product-breadcrumb-sep">/</span>
        <span class="product-breadcrumb-current">Loading...</span>
      </div>
      <div class="section-header" style="margin-top: 16px;">
        <h1 class="section-title">Loading Collection...</h1>
      </div>
      <div class="products-grid" style="margin-top: 24px;">
        ${Array.from({ length: 4 }).map(() => `
          <div class="catalog-skeleton-card">
            <div class="catalog-skeleton-img"></div>
            <div class="catalog-skeleton-text" style="width: 60%;"></div>
            <div class="catalog-skeleton-text" style="width: 40%;"></div>
          </div>
        `).join('')}
      </div>
    `;
  }

  function render() {
    const colName = currentCollection?.name || 'Collection';
    const colDesc = currentCollection?.description || 'Explore curated pieces in this collection.';

    container.innerHTML = `
      <div class="product-breadcrumb">
        <a href="/" data-nav="/">Home</a>
        <span class="product-breadcrumb-sep">/</span>
        <a href="/collections" data-nav="/collections">Collections</a>
        <span class="product-breadcrumb-sep">/</span>
        <span class="product-breadcrumb-current">${escapeHtml(colName)}</span>
      </div>

      <div class="section-header" style="margin-top: 16px;">
        <h1 class="section-title">${escapeHtml(colName)}</h1>
        <p class="section-subtitle">${escapeHtml(colDesc)}</p>
      </div>

      ${errorState ? `
        <div class="catalog-status-box is-error" style="margin-top: 24px;">
          <div class="catalog-status-title">Unable to load collection products</div>
          <div class="catalog-status-desc">${escapeHtml(errorState)}</div>
          <button class="btn btn-secondary btn-retry" style="margin-top: 8px;">Retry Connection</button>
        </div>
      ` : (!products || products.length === 0) ? `
        <div class="catalog-status-box" style="margin-top: 24px;">
          <div class="catalog-status-title">No pieces found in this collection</div>
          <div class="catalog-status-desc">Active products will appear here once added to this collection.</div>
          <a href="/products" class="btn btn-secondary" style="margin-top: 16px;">Explore all pieces</a>
        </div>
      ` : `
        <div class="products-grid" id="collection-products-grid" style="margin-top: 24px;">
          ${products.map(product => {
            const safeTitle = escapeHtml(product.title);
            const safeBadge = product.badge ? escapeHtml(product.badge) : null;
            const formattedPrice = formatDisplayPrice(product.min_price ?? product.min_price_minor);
            const productHref = `/products/${encodeURIComponent(product.slug)}`;

            return `
              <article class="product-card" id="col-product-${escapeHtml(product.id)}">
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
          }).join('')}
        </div>

        <div class="pagination-container" id="col-pagination-container" style="display: flex; justify-content: center; margin-top: 36px;">
          ${products.length < totalProducts ? `
            <button class="btn btn-secondary btn-load-more" id="btn-col-load-more" ${isLoadingMore ? 'disabled' : ''} style="min-width: 220px;">
              ${isLoadingMore ? 'Loading Pieces...' : `Load More Products (${products.length} of ${totalProducts})`}
            </button>
          ` : totalProducts > 0 ? `
            <span class="catalog-status-desc" style="color: var(--color-text-muted); font-size: 0.85rem;">
              Showing all ${totalProducts} pieces
            </span>
          ` : ''}
        </div>
      `}
    `;

    // Prepend product images
    products.forEach(product => {
      const card = container.querySelector(`#col-product-${product.id}`);
      const wrapper = card?.querySelector('.product-card-img-wrapper');
      if (wrapper && !wrapper.querySelector('.product-card-img')) {
        const hoverUrl = product.hover_image_url || product.secondary_image_url || null;

        const primaryImg = createSafeImageElement({
          src: product.image_url,
          fallback: '/images/storefront-empty.svg',
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

    // Wire up events
    container.querySelector('.btn-retry')?.addEventListener('click', () => {
      load(currentSlugOrId);
    });

    container.querySelector('#btn-col-load-more')?.addEventListener('click', () => {
      if (isLoadingMore) return;
      loadMore();
    });

    container.querySelectorAll('.product-card-btn').forEach(link => {
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
  }

  async function load(slugOrId) {
    currentSlugOrId = slugOrId;
    currentPage = 1;
    products = [];
    totalProducts = 0;
    isLoading = true;
    isLoadingMore = false;
    errorState = null;
    const thisReqId = ++activeRequestId;

    renderSkeleton();

    try {
      // 1. Fetch collections to resolve canonical collection ID and metadata
      const colsRes = await fetchCollections().catch(() => ({ collections: [] }));
      if (thisReqId !== activeRequestId) return;

      const colList = Array.isArray(colsRes) ? colsRes : (Array.isArray(colsRes?.collections) ? colsRes.collections : []);
      currentCollection = colList.find(c => c.slug === slugOrId || c.id === slugOrId) || {
        id: slugOrId,
        slug: slugOrId,
        name: slugOrId.charAt(0).toUpperCase() + slugOrId.slice(1).replace(/[-_]/g, ' '),
        description: ''
      };

      const prodRes = await fetchProducts({
        collectionId: currentCollection.id || slugOrId,
        page: currentPage,
        pageSize,
      });

      if (typeof document !== 'undefined') {
        document.title = `${currentCollection.name} — Collections — AlphaZee`;
        let descMeta = document.querySelector('meta[name="description"]');
        if (descMeta) {
          descMeta.setAttribute('content', currentCollection.description || `Browse the ${currentCollection.name} collection at AlphaZee.`);
        }
        let canonical = document.querySelector('link[rel="canonical"]');
        if (canonical && typeof window !== 'undefined') {
          canonical.setAttribute('href', `${window.location.origin}/collections/${encodeURIComponent(currentCollection.slug || currentCollection.id)}`);
        }
      }

      products = prodRes?.products || [];
      totalProducts = typeof prodRes?.total === 'number' ? prodRes.total : products.length;
      isLoading = false;
      render();
    } catch (err) {
      if (thisReqId !== activeRequestId) return;
      isLoading = false;
      errorState = err.message || 'Could not connect to collection catalog.';
      render();
    }
  }

  async function loadMore() {
    isLoadingMore = true;
    const btn = container.querySelector('#btn-col-load-more');
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Loading Pieces...';
    }

    const thisReqId = ++activeRequestId;
    const nextPage = currentPage + 1;

    try {
      const prodRes = await fetchProducts({
        collectionId: currentCollection.id,
        page: nextPage,
        pageSize,
      });

      if (thisReqId !== activeRequestId) return;

      const newItems = prodRes?.products || [];
      const existingIds = new Set(products.map(p => p.id));
      const filtered = newItems.filter(p => !existingIds.has(p.id));
      products = [...products, ...filtered];
      currentPage = nextPage;
      totalProducts = typeof prodRes?.total === 'number' ? prodRes.total : products.length;
      isLoadingMore = false;
      render();
    } catch (err) {
      if (thisReqId !== activeRequestId) return;
      isLoadingMore = false;
      render();
    }
  }

  return {
    element: container,
    load,
    destroy() {
      activeRequestId++;
    }
  };
}
