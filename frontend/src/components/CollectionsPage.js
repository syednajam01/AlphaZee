import { fetchCollections, fetchPublicStoreSettings } from '../utils/api.js';
import { escapeHtml, sanitizeMediaUrl, createSafeImageElement, toVariantUrl } from '../utils/dom.js';

export function createCollectionsPage({ onSelectCollection, onNavigate }) {
  const container = document.createElement('div');
  container.className = 'container section collections-page-container';

  container.innerHTML = `
    <div class="product-breadcrumb">
      <a href="/" data-nav="/">Home</a>
      <span class="product-breadcrumb-sep">/</span>
      <span class="product-breadcrumb-current">Collections</span>
    </div>

    <div class="section-header" style="margin-top: 16px;">
      <h1 class="section-title">All Collections</h1>
      <p class="section-subtitle">Explore our complete range of curated wardrobe edits.</p>
    </div>

    <div class="collections-grid" id="all-collections-grid">
      <!-- Collections rendered here -->
    </div>
  `;

  const grid = container.querySelector('#all-collections-grid');

  async function load() {
    if (typeof document !== 'undefined') {
      document.title = 'All Collections — AlphaZee';
      let descMeta = document.querySelector('meta[name="description"]');
      if (descMeta) {
        descMeta.setAttribute('content', 'Browse all clothing and wardrobe collections from AlphaZee.');
      }
      let canonical = document.querySelector('link[rel="canonical"]');
      if (canonical && typeof window !== 'undefined') {
        canonical.setAttribute('href', `${window.location.origin}/collections`);
      }
    }

    grid.innerHTML = `
      <div class="catalog-status-box" style="grid-column: 1 / -1;">
        <div class="catalog-status-title">Loading collections...</div>
      </div>
    `;

    try {
      const [res, settings] = await Promise.all([
        fetchCollections(),
        fetchPublicStoreSettings().catch(() => null)
      ]);

      if (settings) {
        const pageTitle = settings.collections_page_title || 'All Collections';
        const pageSubtitle = settings.collections_page_subtitle || 'Explore our complete range of curated wardrobe edits.';
        const titleEl = container.querySelector('.section-title');
        const subtitleEl = container.querySelector('.section-subtitle');
        if (titleEl) titleEl.textContent = pageTitle;
        if (subtitleEl) subtitleEl.textContent = pageSubtitle;
        if (typeof document !== 'undefined') {
          document.title = `${pageTitle} — AlphaZee`;
        }
      }

      const list = Array.isArray(res) ? res : (Array.isArray(res?.collections) ? res.collections : []);
      if (!list || list.length === 0) {
        grid.innerHTML = `
          <div class="catalog-status-box" style="grid-column: 1 / -1;">
            <div class="catalog-status-title">No Collections Found</div>
            <div class="catalog-status-desc">Active catalog collections will appear here.</div>
          </div>
        `;
        return;
      }

      grid.innerHTML = list.map(col => {
        const safeName = escapeHtml(col.name);
        const safeDesc = col.description ? escapeHtml(col.description) : 'Explore pieces';
        const targetSlug = col.slug || col.id;
        const targetHref = `/collections/${encodeURIComponent(targetSlug)}`;

        return `
          <a href="${targetHref}" class="collection-card" data-collection="${escapeHtml(col.id)}" data-slug="${escapeHtml(targetSlug)}">
            <div class="collection-card-overlay"></div>
            <div class="collection-card-content">
              <span class="collection-caption">The collection</span>
              <h2 class="collection-card-title">${safeName}</h2>
              <p class="collection-description">${safeDesc}</p>
              <span class="collection-card-cta">
                Explore collection
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="5" y1="12" x2="19" y2="12"></line>
                  <polyline points="12 5 19 12 12 19"></polyline>
                </svg>
              </span>
            </div>
          </a>
        `;
      }).join('');

      list.forEach(col => {
        const card = grid.querySelector(`[data-collection="${col.id}"]`);
        if (card) {
          const colImg = createSafeImageElement({
            src: toVariantUrl(col.image_url, 'card'),
            fallback: '/images/storefront-empty.svg',
            alt: col.name || 'Collection',
            className: 'collection-img',
            loading: 'lazy',
            shimmer: true,
            width: 450,
            height: 800,
          });
          const fx = col.focal_x != null ? col.focal_x : 50;
          const fy = col.focal_y != null ? col.focal_y : 50;
          const zm = col.zoom_scale != null ? col.zoom_scale : 1.0;
          if (colImg.style?.setProperty) {
            colImg.style.setProperty('--card-focal', `${fx}% ${fy}%`);
            colImg.style.setProperty('--card-zoom', String(zm));
          } else if (colImg.style) {
            colImg.style['--card-focal'] = `${fx}% ${fy}%`;
            colImg.style['--card-zoom'] = String(zm);
          }
          card.prepend(colImg);
        }
      });

      grid.querySelectorAll('.collection-card').forEach(card => {
        card.addEventListener('click', (e) => {
          if (e && (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey)) return;
          e.preventDefault();
          const targetSlug = card.dataset.slug || card.dataset.collection;
          if (onSelectCollection) {
            onSelectCollection(targetSlug);
          } else if (onNavigate) {
            onNavigate(`/collections/${encodeURIComponent(targetSlug)}`);
          }
        });
      });
    } catch {
      grid.innerHTML = `
        <div class="catalog-status-box is-error" style="grid-column: 1 / -1;">
          <div class="catalog-status-title">Collections Unavailable</div>
          <div class="catalog-status-desc">We could not load the collections. Please try again.</div>
          <button class="btn btn-secondary btn-retry" style="margin-top: 8px;">Try again</button>
        </div>
      `;
      grid.querySelector('.btn-retry')?.addEventListener('click', () => load());
    }
  }

  return {
    element: container,
    load,
    destroy() {}
  };
}

