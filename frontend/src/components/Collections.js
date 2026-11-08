import { fetchCollections } from '../utils/api.js';
import { escapeHtml, sanitizeMediaUrl, createSafeImageElement } from '../utils/dom.js';

export function createCollectionsSection(onSelectCollection, { limit = 3, onNavigate } = {}) {
  const section = document.createElement('section');
  section.className = 'section';
  section.id = 'collections';

  const container = document.createElement('div');
  container.className = 'container';

  container.innerHTML = `
    <div class="section-header">
      <h2 class="section-title">Shop by collection</h2>
      <p class="section-subtitle">A place for every part of your wardrobe.</p>
    </div>

    <div class="collections-grid" id="collections-grid-container">
      <!-- Rendered dynamically -->
    </div>

    <div id="collections-more-container" style="display: flex; justify-content: center; margin-top: 32px;">
      <!-- More collections button rendered when total > limit -->
    </div>
  `;

  section.appendChild(container);

  const grid = container.querySelector('#collections-grid-container');
  const moreContainer = container.querySelector('#collections-more-container');

  async function loadCollections() {
    try {
      const res = await fetchCollections();
      const list = Array.isArray(res) ? res : (Array.isArray(res?.collections) ? res.collections : []);
      if (!list || list.length === 0) {
        grid.innerHTML = `
          <div class="catalog-status-box" style="grid-column: 1 / -1;">
            <div class="catalog-status-title">No Collections Configured</div>
            <div class="catalog-status-desc">Active catalog collections will appear here.</div>
          </div>
        `;
        if (moreContainer) moreContainer.innerHTML = '';
        return;
      }

      const displayList = (limit && list.length > limit) ? list.slice(0, limit) : list;

      grid.innerHTML = displayList.map(col => {
        const safeName = escapeHtml(col.name);
        const safeDesc = col.description ? escapeHtml(col.description) : 'Explore pieces';
        const safeId = escapeHtml(col.id);
        const targetSlug = col.slug || col.id;
        const targetHref = `/collections/${encodeURIComponent(targetSlug)}`;

        return `
          <a href="${targetHref}" class="collection-card" data-collection="${safeId}" data-slug="${escapeHtml(targetSlug)}">
            <div class="collection-card-overlay"></div>
            <div class="collection-card-content">
              <span class="collection-caption">The collection</span>
              <h3 class="collection-card-title">${safeName}</h3>
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

      displayList.forEach(col => {
        const card = grid.querySelector(`[data-collection="${col.id}"]`);
        if (card) {
          card.prepend(
            createSafeImageElement({
              src: col.image_url,
              fallback: '/images/storefront-empty.svg',
              alt: col.name || 'Collection',
              className: 'collection-img',
              loading: 'lazy',
              width: 400,
              height: 300,
            })
          );
        }
      });

      if (moreContainer) {
        if (limit && list.length > limit) {
          moreContainer.innerHTML = `
            <a href="/collections" class="btn btn-secondary btn-more-collections" id="btn-more-collections" style="min-width: 220px;">
              View all collections (${list.length}) →
            </a>
          `;
          moreContainer.querySelector('#btn-more-collections')?.addEventListener('click', (e) => {
            if (e && (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey)) return;
            e.preventDefault();
            if (onNavigate) {
              onNavigate('/collections');
            }
          });
        } else {
          moreContainer.innerHTML = '';
        }
      }

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
      if (moreContainer) moreContainer.innerHTML = '';
      grid.querySelector('.btn-retry')?.addEventListener('click', () => {
        loadCollections();
      });
    }
  }

  loadCollections();

  section.reload = loadCollections;
  return section;
}
