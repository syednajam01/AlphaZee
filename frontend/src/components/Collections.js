import { collectionsData } from '../data/collections.js';

export function createCollectionsSection(onSelectCollection) {
  const section = document.createElement('section');
  section.className = 'section';
  section.id = 'collections';

  section.innerHTML = `
    <div class="container">
      <div class="section-header">
        <h2 class="section-title">Shop by Collection</h2>
        <p class="section-subtitle">Curated categories engineered for fit, fabric, and purpose.</p>
      </div>

      <div class="collections-grid">
        ${collectionsData.map(col => `
          <a href="#featured" class="collection-card" data-collection="${col.id}">
            <img 
              src="${col.image}" 
              alt="${col.title}" 
              class="collection-img"
              loading="lazy"
              width="400"
              height="300"
            />
            <div class="collection-card-overlay"></div>
            <div class="collection-card-content">
              <span class="badge badge-accent" style="margin-bottom: 8px;">${col.itemCount}</span>
              <h3 class="collection-card-title">${col.title}</h3>
              <span class="collection-card-cta">
                Explore collection
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="5" y1="12" x2="19" y2="12"></line>
                  <polyline points="12 5 19 12 12 19"></polyline>
                </svg>
              </span>
            </div>
          </a>
        `).join('')}
      </div>
    </div>
  `;

  section.querySelectorAll('.collection-card').forEach(card => {
    card.addEventListener('click', (e) => {
      const colId = card.dataset.collection;
      if (onSelectCollection) {
        onSelectCollection(colId);
      }
    });
  });

  return section;
}
