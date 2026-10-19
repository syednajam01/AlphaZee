import { fetchHeroProducts, fetchHeroSlides } from '../utils/api.js';
import { formatDisplayPrice } from '../utils/money.js';
import { escapeHtml, sanitizeMediaUrl } from '../utils/dom.js';

export function createHero(onProductClick) {
  const section = document.createElement('section');
  section.className = 'hero-section';
  section.setAttribute('aria-label', 'Featured Products Showcase');

  let currentSlide = 0;
  let heroItems = [];
  let isUserPaused = false;
  let isTabHidden = false;
  let isIntersecting = true;
  let imageTimer = null;
  let generation = 0;
  let alive = true;
  let intersectionObserver = null;

  const prefersReducedMotion = typeof window !== 'undefined' &&
    window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const saveData = typeof navigator !== 'undefined' &&
    navigator.connection && navigator.connection.saveData;

  function renderFallback(message = null) {
    const statusHtml = message ? `
      <div class="hero-catalog-status" role="status" style="position: relative; z-index: 10; padding: 8px 16px; background: rgba(0, 0, 0, 0.45); font-size: 0.8125rem; display: flex; align-items: center; justify-content: space-between;">
        <span>${escapeHtml(message)}</span>
        <button type="button" class="btn btn-secondary" style="padding: 2px 8px; font-size: 0.75rem;" data-hero-retry>Retry</button>
      </div>
    ` : '';

    section.innerHTML = `
      <div class="hero-bg-container">
        <div class="hero-bg-media is-active" style="background: radial-gradient(circle at 70% 30%, #1A2621 0%, #0D1310 100%); width: 100%; height: 100%;"></div>
      </div>
      <div class="hero-overlay"></div>
      <div class="hero-motif" aria-hidden="true">AZ</div>
      ${statusHtml}
      <div class="container hero-content-wrapper" style="position: relative; z-index: 2; padding-top: var(--space-6); padding-bottom: var(--space-6);">
        <div style="max-width: 640px;">
          <span class="badge badge-accent hero-badge" style="margin-bottom: var(--space-2);">Authentic Streetwear</span>
          <h1 class="hero-title" style="font-size: clamp(1.85rem, 5vw, 2.75rem); font-weight: 800; line-height: 1.15; margin-bottom: var(--space-3); color: #FFFFFF;">
            Architectural Cuts.<br>Heavyweight Drape.
          </h1>
          <p class="hero-desc" style="font-size: clamp(0.95rem, 2.5vw, 1.125rem); color: rgba(255, 255, 255, 0.85); line-height: 1.5; margin-bottom: var(--space-5); max-width: 520px;">
            Minimalist streetwear crafted in Pakistan. Architectural cuts, structured fits, and zero compromises.
          </p>
          <div class="hero-cta-group">
            <a href="#featured" class="btn btn-hero">Explore Collection</a>
          </div>
        </div>
      </div>
    `;
    section.querySelector('[data-hero-retry]')?.addEventListener('click', loadHero);
  }

  function renderCarousel() {
    if (!heroItems || heroItems.length === 0) {
      renderFallback();
      return;
    }

    section.innerHTML = '';
    const isSingle = heroItems.length === 1;

    // 1. Media container
    const bgContainer = document.createElement('div');
    bgContainer.className = 'hero-bg-container';

    heroItems.forEach((item, index) => {
      const posterUrl = sanitizeMediaUrl(item.poster_url || item.hero_poster_url || item.image_url || item.hero_image_url, '');
      const videoUrl = sanitizeMediaUrl(item.video_url || item.hero_video_url, '');
      const imageUrl = sanitizeMediaUrl(item.image_url || item.hero_image_url || posterUrl, '');

      if (videoUrl && !prefersReducedMotion && !saveData) {
        const video = document.createElement('video');
        video.className = `hero-bg-media hero-video-media ${index === 0 ? 'is-active' : ''}`;
        if (posterUrl) video.poster = posterUrl;
        video.muted = true;
        video.playsInline = true;
        video.preload = 'none';
        video.setAttribute('aria-hidden', 'true');
        video.dataset.videoSrc = videoUrl;
        video.dataset.slideIndex = String(index);

        // Single video loops; multiple videos advance via ended event
        video.loop = isSingle;

        video.addEventListener('ended', () => {
          if (!alive || isSingle || isUserPaused) return;
          goToSlide(currentSlide + 1);
        });

        video.addEventListener('error', () => {
          console.warn(`[Hero] Video playback failed for slide #${index + 1}`);
          // If video fails, reveal poster and skip to next slide if multiple
          video.style.display = 'none';
          if (!isSingle && !isUserPaused) {
            setTimeout(() => { if (alive) goToSlide(currentSlide + 1); }, 3000);
          }
        });

        if (index === 0) {
          video.src = videoUrl;
          video.currentTime = 0;
          if (!isUserPaused && isIntersecting && !isTabHidden) {
            video.play().catch(handleAutoplayReject);
          }
        }
        bgContainer.appendChild(video);
      } else if (imageUrl) {
        const img = document.createElement('img');
        img.className = `hero-bg-media ${index === 0 ? 'is-active' : ''}`;
        img.src = imageUrl;
        img.alt = item.title || 'AlphaZee featured piece';
        img.loading = index === 0 ? 'eager' : 'lazy';
        img.dataset.slideIndex = String(index);
        bgContainer.appendChild(img);
      } else {
        const fallbackBg = document.createElement('div');
        fallbackBg.className = `hero-bg-media ${index === 0 ? 'is-active' : ''}`;
        fallbackBg.style.background = 'radial-gradient(circle at 70% 30%, #1A2621 0%, #0D1310 100%)';
        fallbackBg.dataset.slideIndex = String(index);
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
      slide.dataset.index = String(index);
      slide.setAttribute('role', 'group');
      slide.setAttribute('aria-roledescription', 'slide');
      slide.setAttribute('aria-label', `${index + 1} of ${heroItems.length}: ${item.title || 'Featured'}`);

      const safeTitle = escapeHtml(item.title || 'Architectural Drape');
      const safeBenefit = escapeHtml(item.benefit || item.hero_benefit || 'Engineered with premium materials and precision fits.');
      const priceDisplay = (item.min_price !== undefined || item.min_price_minor !== undefined)
        ? formatDisplayPrice(item.min_price ?? item.min_price_minor)
        : null;
      const priceText = priceDisplay && priceDisplay !== 'Price unavailable' ? `From ${priceDisplay}` : '';

      slide.innerHTML = `
        <div class="hero-text-content">
          <span class="badge badge-accent hero-badge">Featured Piece</span>
          <h1 class="hero-title">${safeTitle}</h1>
          <p class="hero-desc">${safeBenefit}</p>
          ${priceText ? `<div class="hero-price-tag">${priceText}</div>` : ''}
          <div class="hero-cta-group">
            <button class="btn btn-hero hero-cta-btn" data-slug="${escapeHtml(item.slug || '')}" data-id="${escapeHtml(item.id || '')}">
              ${item.slug || item.id ? 'View Product Details' : 'Explore Collection'}
            </button>
            <a href="#featured" class="btn btn-secondary" style="color: #FFFFFF; border-color: rgba(255,255,255,0.3);">
              Browse Catalog
            </a>
          </div>
        </div>
      `;

      slide.querySelector('.hero-cta-btn')?.addEventListener('click', () => {
        if (onProductClick && (item.slug || item.id)) {
          onProductClick(item.slug || item.id);
        } else {
          const featured = document.querySelector('#featured');
          if (featured) featured.scrollIntoView({ behavior: 'smooth' });
        }
      });

      track.appendChild(slide);
    });

    container.appendChild(track);

    // 3. Navigation & Accessible Playback controls
    const controls = document.createElement('div');
    controls.className = 'hero-controls';
    controls.innerHTML = `
      ${!isSingle ? '<button class="hero-ctrl-btn" id="hero-prev" aria-label="Previous Slide">‹</button>' : ''}
      <button class="hero-ctrl-btn" id="hero-play-pause" aria-label="${isUserPaused ? 'Resume hero playback' : 'Pause hero playback'}" title="${isUserPaused ? 'Resume' : 'Pause'}">
        ${isUserPaused ? '▶' : '⏸'}
      </button>
      <span class="hero-slide-indicator" id="hero-indicator">1 / ${heroItems.length}</span>
      ${!isSingle ? '<button class="hero-ctrl-btn" id="hero-next" aria-label="Next Slide">›</button>' : ''}
    `;
    container.appendChild(controls);

    controls.querySelector('#hero-prev')?.addEventListener('click', () => goToSlide(currentSlide - 1));
    controls.querySelector('#hero-next')?.addEventListener('click', () => goToSlide(currentSlide + 1));
    controls.querySelector('#hero-play-pause')?.addEventListener('click', togglePlayPause);

    section.appendChild(bgContainer);
    section.appendChild(overlay);
    section.appendChild(motif);
    section.appendChild(container);

    setupObserver();
    scheduleImageSlide();
  }

  function handleAutoplayReject() {
    // Autoplay policy prevented playback. Keep button in play state.
    isUserPaused = true;
    updatePlayPauseButton();
  }

  function updatePlayPauseButton() {
    const btn = section.querySelector('#hero-play-pause');
    if (!btn) return;
    btn.textContent = isUserPaused ? '▶' : '⏸';
    btn.setAttribute('aria-label', isUserPaused ? 'Resume hero playback' : 'Pause hero playback');
    btn.title = isUserPaused ? 'Resume' : 'Pause';
  }

  function togglePlayPause() {
    isUserPaused = !isUserPaused;
    updatePlayPauseButton();

    const activeMedia = section.querySelectorAll('.hero-bg-media')[currentSlide];
    if (activeMedia && activeMedia.tagName === 'VIDEO') {
      if (isUserPaused) {
        activeMedia.pause();
      } else {
        activeMedia.play().catch(handleAutoplayReject);
      }
    } else {
      if (isUserPaused) {
        clearImageTimer();
      } else {
        scheduleImageSlide();
      }
    }
  }

  function clearImageTimer() {
    if (imageTimer) {
      clearTimeout(imageTimer);
      imageTimer = null;
    }
  }

  function scheduleImageSlide() {
    clearImageTimer();
    if (!alive || isUserPaused || heroItems.length <= 1) return;
    const activeMedia = section.querySelectorAll('.hero-bg-media')[currentSlide];
    if (activeMedia && activeMedia.tagName !== 'VIDEO') {
      imageTimer = setTimeout(() => {
        if (alive && !isUserPaused) goToSlide(currentSlide + 1);
      }, 6000);
      if (imageTimer && typeof imageTimer.unref === 'function') {
        imageTimer.unref();
      }
    }
  }

  function goToSlide(index) {
    if (!heroItems || heroItems.length <= 1) return;
    clearImageTimer();
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
          media.currentTime = 0;
          if (!isUserPaused && isIntersecting && !isTabHidden) {
            media.play().catch(handleAutoplayReject);
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

    scheduleImageSlide();
  }

  function setupObserver() {
    if (typeof IntersectionObserver !== 'undefined' && !intersectionObserver) {
      intersectionObserver = new IntersectionObserver((entries) => {
        for (const entry of entries) {
          isIntersecting = entry.isIntersecting;
          const activeMedia = section.querySelectorAll('.hero-bg-media')[currentSlide];
          if (activeMedia && activeMedia.tagName === 'VIDEO') {
            if (!isIntersecting) {
              if (!activeMedia.paused) activeMedia.pause();
            } else if (!isUserPaused && !isTabHidden) {
              activeMedia.play().catch(handleAutoplayReject);
            }
          }
        }
      }, { threshold: 0.2 });
      intersectionObserver.observe(section);
    }
  }

  function onVisibilityChange() {
    isTabHidden = typeof document !== 'undefined' && document.hidden;
    const activeMedia = section.querySelectorAll('.hero-bg-media')[currentSlide];
    if (activeMedia && activeMedia.tagName === 'VIDEO') {
      if (isTabHidden) {
        if (!activeMedia.paused) activeMedia.pause();
      } else if (!isUserPaused && isIntersecting) {
        activeMedia.play().catch(handleAutoplayReject);
      }
    }
  }

  if (typeof document !== 'undefined' && typeof document.addEventListener === 'function') {
    document.addEventListener('visibilitychange', onVisibilityChange);
  }

  // Load hero slides from API (dedicated playlist with legacy fallback)
  async function loadHero() {
    const request = ++generation;
    try {
      let items = [];
      try {
        const slidesRes = await fetchHeroSlides();
        const slides = Array.isArray(slidesRes) ? slidesRes : (slidesRes?.slides || []);
        if (slides.length > 0) {
          items = slides.map(s => ({
            id: s.target_product_id || s.id,
            slug: s.product?.slug || null,
            title: s.title || s.product?.title || 'Architectural Drape',
            benefit: s.benefit || s.product?.hero_benefit || 'Structured fits with zero compromises.',
            video_url: s.video_url,
            poster_url: s.poster_url,
            image_url: s.image_url,
            min_price: s.product?.min_price ?? s.product?.min_price_minor,
          }));
        }
      } catch {
        // Fallback to legacy hero products route
      }

      if (!items.length) {
        const legacyItems = await fetchHeroProducts();
        items = Array.isArray(legacyItems) ? legacyItems : [];
      }

      if (!alive || request !== generation) return;
      clearImageTimer();
      section.querySelectorAll('video').forEach(video => video.pause?.());
      currentSlide = 0;
      heroItems = items;
      renderCarousel();
    } catch {
      if (!alive || request !== generation) return;
      clearImageTimer();
      section.querySelectorAll('video').forEach(video => video.pause?.());
      renderFallback('Featured products could not load. Try again.');
    }
  }

  loadHero();

  section.destroy = () => {
    alive = false;
    generation++;
    clearImageTimer();
    if (typeof document !== 'undefined' && typeof document.removeEventListener === 'function') {
      document.removeEventListener('visibilitychange', onVisibilityChange);
    }
    if (intersectionObserver) {
      intersectionObserver.disconnect();
      intersectionObserver = null;
    }
    section.querySelectorAll('video').forEach(video => {
      try { video.pause(); } catch {}
    });
  };

  section.reload = loadHero;
  return section;
}
