import { productsData } from '../data/products.js';
import { cart } from '../utils/cart.js';

export function createFeaturedProducts(onOpenProductModal) {
  const section = document.createElement('section');
  section.className = 'section';
  section.id = 'featured';

  let activeCategory = 'all';

  function renderGrid() {
    const filtered = activeCategory === 'all' 
      ? productsData 
      : productsData.filter(p => p.category === activeCategory);

    const grid = section.querySelector('#products-grid-container');
    if (!grid) return;

    grid.innerHTML = filtered.map(product => `
      <article class="product-card" id="product-${product.id}">
        <div class="product-card-img-wrapper">
          <span class="badge badge-neutral product-card-badge">${product.badge || product.stockStatus}</span>
          <img 
            src="${product.image}" 
            alt="${product.title}" 
            class="product-card-img" 
            loading="lazy"
            width="320"
            height="320"
          />
        </div>
        <div class="product-card-info">
          <h3 class="product-card-title">${product.title}</h3>
          <div class="product-card-price-row">
            <span class="product-card-price">${product.formattedPrice}</span>
            <span class="product-card-status">${product.stockStatus}</span>
          </div>
          <button 
            class="btn btn-secondary product-card-btn" 
            data-id="${product.id}"
            aria-label="${product.hasOptions ? 'Choose options for' : 'Add to cart'} ${product.title}">
            ${product.hasOptions ? 'Choose options' : 'Add to cart'}
          </button>
        </div>
      </article>
    `).join('');

    // Attach button listeners
    grid.querySelectorAll('.product-card-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.dataset.id;
        const product = productsData.find(p => p.id === id);
        if (!product) return;

        if (product.hasOptions) {
          if (onOpenProductModal) onOpenProductModal(product);
        } else {
          cart.addItem(product, {}, 1);
          btn.textContent = 'Added to Cart ✓';
          btn.classList.add('btn-primary');
          btn.classList.remove('btn-secondary');
          setTimeout(() => {
            btn.textContent = 'Add to cart';
            btn.classList.remove('btn-primary');
            btn.classList.add('btn-secondary');
          }, 1500);
        }
      });
    });
  }

  section.innerHTML = `
    <div class="container">
      <div class="section-header" style="display: flex; flex-direction: column; gap: 16px;">
        <div>
          <h2 class="section-title">Featured Products</h2>
          <p class="section-subtitle">Minimalist designs crafted with premium materials.</p>
        </div>
        
        <!-- Category Filter Tabs -->
        <div class="filter-tabs" role="tablist" style="display: flex; gap: 8px; overflow-x: auto; padding-bottom: 4px;">
          <button class="option-pill is-selected" data-filter="all" role="tab" aria-selected="true">All Products</button>
          <button class="option-pill" data-filter="essentials" role="tab" aria-selected="false">Essentials</button>
          <button class="option-pill" data-filter="streetwear" role="tab" aria-selected="false">Streetwear</button>
          <button class="option-pill" data-filter="accessories" role="tab" aria-selected="false">Accessories</button>
        </div>
      </div>

      <div class="products-grid" id="products-grid-container">
        <!-- Rendered dynamically -->
      </div>
    </div>
  `;

  // Filter tabs click handling
  const tabs = section.querySelectorAll('.filter-tabs button');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => {
        t.classList.remove('is-selected');
        t.setAttribute('aria-selected', 'false');
      });
      tab.classList.add('is-selected');
      tab.setAttribute('aria-selected', 'true');
      activeCategory = tab.dataset.filter;
      renderGrid();
    });
  });

  // Initial render
  setTimeout(() => renderGrid(), 0);

  return {
    element: section,
    setFilter: (category) => {
      activeCategory = category;
      tabs.forEach(t => {
        const matches = t.dataset.filter === category;
        t.classList.toggle('is-selected', matches);
        t.setAttribute('aria-selected', matches);
      });
      renderGrid();
    }
  };
}
