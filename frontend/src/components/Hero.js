import { fetchHeroProducts } from '../utils/api.js';
import { formatDisplayPrice } from '../utils/money.js';
import { escapeHtml, sanitizeMediaUrl } from '../utils/dom.js';

export function createHero(onProductClick) {
  const section = document.createElement('section');
  section.className = 'hero-section';
  section.setAttribute('aria-label', 'Featured Products Showcase');

  let currentSlide = 0;
  let heroItems = [];
  let autoAdvanceInterval = null;
  let isPlaying = true;
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const saveData = navigator.connection && navigator.connection.saveData;

  function renderFallback() {
    section.innerHTML = `
      <div class="hero-bg-container">
        <div class="hero-bg-media is-active" style="background: radial-gradient(circle at 70% 30%, #1A2621 0%, #0D1310 100%); width: 100%; height: 100%;"></div>
      </div>
      <div class="hero-overlay"></div>
      <div class="hero-motif" aria-hidden="true">AZ</div>
      <div class="container hero-content-wrapper" style="position: relative; z-index: 2; padding-top: var(--space-16); padding-bottom: var(--space-16);">
        <div style="max-width: 640px;">
          <span class="badge badge-accent hero-badge" style="margin-bottom: 16px;">Authentic Streetwear</span>
          <h1 class="hero-title" style="font-size: 2.75rem; font-weight: 800; line-height: 1.15; margin-bottom: 16px; color: #FFFFFF;">
            Architectural Cuts.<br>Heavyweight Drape.
          </h1>
          <p class="hero-desc" style="font-size: 1.125rem; color: rgba(255, 255, 255, 0.85); line-height: 1.6; margin-bottom: 24px;">
            Minimalist streetwear crafted in Pakistan. Premium cotton, structured fits, and zero compromises.
          </p>
          <div class="hero-cta-group">
            <a href="#featured" class="btn btn-hero">Explore Collection</a>
          </div>
        </div>
      </div>
    `;
  }

  function renderCarousel() {
    if (!heroItems || heroItems.length === 0) {
      renderFallback();
      return;
    }

    section.innerHTML = '';

    // 1. Media container
    const bgContainer = document.createElement('div');
    bgContainer.className = 'hero-bg-container';

    heroItems.forEach((item, index) => {
      const posterUrl = sanitizeMediaUrl(item.hero_poster_url || item.image_url, '');
      const videoUrl = sanitizeMediaUrl(item.hero_video_url, '');

      if (videoUrl && !prefersReducedMotion && !saveData) {
        const video = document.createElement('video');
        video.className = `hero-bg-media ${index === 0 ? 'is-active' : ''}`;
        if (posterUrl) video.poster = posterUrl;
        video.muted = true;
        video.loop = true;
        video.playsInline = true;
        video.setAttribute('aria-hidden', 'true');
        video.dataset.videoSrc = videoUrl;
        if (index === 0) {
          video.src = videoUrl;
          video.play().catch(() => {});
        }
        bgContainer.appendChild(video);
      } else if (posterUrl) {
        const img = document.createElement('img');
        img.className = `hero-bg-media ${index === 0 ? 'is-active' : ''}`;
        img.src = posterUrl;
        img.alt = item.title || 'AlphaZee featured piece';
        img.dataset.slideIndex = index;
        bgContainer.appendChild(img);
      } else {
        const fallbackBg = document.createElement('div');
        fallbackBg.className = `hero-bg-media ${index === 0 ? 'is-active' : ''}`;
        fallbackBg.style.background = 'radial-gradient(circle at 70% 30%, #1A2621 0%, #0D1310 100%)';
        fallbackBg.dataset.slideIndex = index;
        bgContainer.appendChild(fallbackBg);
      }
    });

    const overlay = document.createElement('div');
    overlay.className = 'hero-overlay';

    const motif = document.createElement('div');
    motif.className = 'hero-motif';
    motif.setAttribute('aria-hidden', 'true');
    motif.textContent = 'AZ';

    // 2. Content container
    const container = document.createElement('div');
    container.className = 'container hero-content-wrapper';

    const track = document.createElement('div');
    track.className = 'hero-slides-track';

    heroItems.forEach((item, index) => {
      const slide = document.createElement('div');
      slide.className = `hero-slide ${index === 0 ? 'is-active' : ''}`;
      slide.dataset.index = index;
      slide.setAttribute('role', 'group');
      slide.setAttribute('aria-roledescription', 'slide');
      slide.setAttribute('aria-label', `${index + 1} of ${heroItems.length}: ${item.title}`);

      const safeTitle = escapeHtml(item.title);
      const safeBenefit = escapeHtml(item.hero_benefit || 'Engineered with premium materials and precision fits.');
      const priceDisplay = formatDisplayPrice(item.min_price ?? item.min_price_minor);
      const priceText = priceDisplay === 'Price unavailable' ? 'Price unavailable' : `From ${priceDisplay}`;

      slide.innerHTML = `
        <div class="hero-text-content">
          <span class="badge badge-accent hero-badge">Featured Piece</span>
          <h1 class="hero-title">${safeTitle}</h1>
          <p class="hero-desc">${safeBenefit}</p>
          <div class="hero-price-tag">${priceText}</div>
          <div class="hero-cta-group">
            <button class="btn btn-hero hero-cta-btn" data-slug="${escapeHtml(item.slug || '')}" data-id="${escapeHtml(item.id || '')}">
              View Product Details
            </button>
            <a href="#featured" class="btn btn-secondary" style="color: #FFFFFF; border-color: rgba(255,255,255,0.3);">
              Browse Catalog
            </a>
          </div>
        </div>
      `;

      slide.querySelector('.hero-cta-btn')?.addEventListener('click', () => {
        if (onProductClick) {
          onProductClick(item.slug || item.id);
        }
      });

      track.appendChild(slide);
    });

    container.appendChild(track);

    // 3. Navigation controls
    if (heroItems.length > 1) {
      const controls = document.createElement('div');
      controls.className = 'hero-controls';
      controls.innerHTML = `
        <button class="hero-ctrl-btn" id="hero-prev" aria-label="Previous Slide">‹</button>
        <span class="hero-slide-indicator" id="hero-indicator">1 / ${heroItems.length}</span>
        <button class="hero-ctrl-btn" id="hero-next" aria-label="Next Slide">›</button>
      `;
      container.appendChild(controls);

      controls.querySelector('#hero-prev')?.addEventListener('click', () => goToSlide(currentSlide - 1));
      controls.querySelector('#hero-next')?.addEventListener('click', () => goToSlide(currentSlide + 1));
    }

    section.appendChild(bgContainer);
    section.appendChild(overlay);
    section.appendChild(motif);
    section.appendChild(container);

    startAutoPlay();
  }

  function goToSlide(index) {
    if (!heroItems || heroItems.length <= 1) return;
    const count = heroItems.length;
    currentSlide = (index + count) % count;

    section.querySelectorAll('.hero-bg-media').forEach((media, i) => {
      const isActive = i === currentSlide;
      media.classList.toggle('is-active', isActive);
      if (media.tagName === 'VIDEO') {
        if (isActive) {
          if (!media.src && media.dataset.videoSrc) {
            media.src = media.dataset.videoSrc;
          }
          if (media.paused) {
            media.play().catch(() => {});
          }
        } else {
          if (!media.paused) {
            media.pause();
          }
        }
      }
    });

    section.querySelectorAll('.hero-slide').forEach((slide, i) => {
      slide.classList.toggle('is-active', i === currentSlide);
    });

    const indicator = section.querySelector('#hero-indicator');
    if (indicator) {
      indicator.textContent = `${currentSlide + 1} / ${count}`;
    }
  }

  function startAutoPlay() {
    if (autoAdvanceInterval) clearInterval(autoAdvanceInterval);
    if (!isPlaying || heroItems.length <= 1) return;
    autoAdvanceInterval = setInterval(() => {
      goToSlide(currentSlide + 1);
    }, 6000);
    if (autoAdvanceInterval && typeof autoAdvanceInterval.unref === 'function') {
      autoAdvanceInterval.unref();
    }
  }

  // Load from API
  async function loadHero() {
    try {
      const items = await fetchHeroProducts();
      heroItems = Array.isArray(items) ? items : [];
      renderCarousel();
    } catch {
      // API unavailable — render brand fallback cleanly without breaking
      renderFallback();
    }
  }

  loadHero();

  section.destroy = () => {
    if (autoAdvanceInterval) clearInterval(autoAdvanceInterval);
  };

  return section;
}
