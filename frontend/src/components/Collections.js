import { fetchCollections } from '../utils/api.js';
import { escapeHtml, sanitizeMediaUrl, createSafeImageElement } from '../utils/dom.js';

export function createCollectionsSection(onSelectCollection) {
  const section = document.createElement('section');
  section.className = 'section';
  section.id = 'collections';

  const container = document.createElement('div');
  container.className = 'container';

  container.innerHTML = `
    <div class="section-header">
      <h2 class="section-title">Shop by Collection</h2>
      <p class="section-subtitle">Curated categories engineered for fit, fabric, and purpose.</p>
    </div>

    <div class="collections-grid" id="collections-grid-container">
      <!-- Rendered dynamically -->
    </div>
  `;

  section.appendChild(container);

  const grid = container.querySelector('#collections-grid-container');

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
        return;
      }

      grid.innerHTML = list.map(col => {
        const safeName = escapeHtml(col.name);
        const safeDesc = col.description ? escapeHtml(col.description) : 'Explore pieces';
        const safeImage = sanitizeMediaUrl(col.image_url);
        const safeId = escapeHtml(col.id);

        return `
          <a href="#featured" class="collection-card" data-collection="${safeId}">
            <div class="collection-card-overlay"></div>
            <div class="collection-card-content">
              <span class="badge badge-accent" style="margin-bottom: 8px;">Collection</span>
              <h3 class="collection-card-title">${safeName}</h3>
              <p style="font-size: 0.8rem; color: rgba(255,255,255,0.8); margin-bottom: 8px;">${safeDesc}</p>
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
          card.prepend(
            createSafeImageElement({
              src: col.image_url,
              alt: col.name || 'Collection',
              className: 'collection-img',
              loading: 'lazy',
              width: 400,
              height: 300,
            })
          );
        }
      });

      grid.querySelectorAll('.collection-card').forEach(card => {
        card.addEventListener('click', (e) => {
          e.preventDefault();
          const colId = card.dataset.collection;
          if (onSelectCollection) {
            onSelectCollection(colId);
          }
        });
      });
    } catch {
      grid.innerHTML = `
        <div class="catalog-status-box is-error" style="grid-column: 1 / -1;">
          <div class="catalog-status-title">Collections Unavailable</div>
          <div class="catalog-status-desc">Unable to load collections from server. Please check your backend connection.</div>
          <button class="btn btn-secondary btn-retry" style="margin-top: 8px;">Retry Connection</button>
        </div>
      `;
      grid.querySelector('.btn-retry')?.addEventListener('click', () => {
        loadCollections();
      });
    }
  }

  loadCollections();

  section.reload = loadCollections;
  return section;
}
