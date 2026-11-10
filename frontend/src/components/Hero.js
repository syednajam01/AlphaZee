import { fetchHeroProducts, fetchHeroSlides, fetchProducts } from '../utils/api.js';
import { formatDisplayPrice } from '../utils/money.js';
import { escapeHtml, sanitizeMediaUrl } from '../utils/dom.js';

function playbackIcon(paused) {
  return `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">${paused ? '<path d="m9 5 10 7-10 7z"/>' : '<path d="M8 5v14M16 5v14"/>'}</svg>`;
}
function directionIcon(next) {
  return `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="${next ? 'm9 5 7 7-7 7' : 'm15 5-7 7 7 7'}"/></svg>`;
}

export function createHero(onProductClick) {
  const section = document.createElement('section');
  section.className = 'hero-section';
  section.setAttribute('aria-label', 'Featured Products Showcase');

  let currentSlide = 0;
  let heroItems = [];
  let catalogProducts = [];
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
        <div class="hero-bg-media is-active" style="background: #eeece6; width: 100%; height: 100%;"></div>
      </div>
      <div class="hero-overlay"></div>
      <div class="hero-motif" aria-hidden="true">AZ</div>
      ${statusHtml}
      <div class="container hero-content-wrapper" style="position: relative; z-index: 2; padding-top: var(--space-6); padding-bottom: var(--space-6);">
        <div style="max-width: 640px;">
          <span class="badge badge-accent hero-badge" style="margin-bottom: var(--space-2);">Selected by AlphaZee</span>
          <h1 class="hero-title">
            Find your next<br>everyday piece
          </h1>
          <p class="hero-desc">
            Clothing and accessories selected for the way you dress. Explore the current collection.
          </p>
          <div class="hero-cta-group">
            <a href="#featured" class="btn btn-hero">Shop the collection</a>
            <a href="#collections" class="btn btn-secondary hero-secondary-btn">Browse collections</a>
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

    const isSingle = heroItems.length === 1;

    // 1. Ambient Background Media Container (Horizontal sliding media track)
    const bgContainer = document.createElement('div');
    bgContainer.className = 'hero-bg-container';

    const mediaTrack = document.createElement('div');
    mediaTrack.className = 'hero-media-track';
    bgContainer.appendChild(mediaTrack);

    heroItems.forEach((item, index) => {
      const posterUrl = sanitizeMediaUrl(item.poster_url || item.hero_poster_url || item.image_url || item.hero_image_url, '');
      const videoUrl = sanitizeMediaUrl(item.video_url || item.hero_video_url, '');
      const imageUrl = sanitizeMediaUrl(item.image_url || item.hero_image_url || posterUrl, '');

      if (videoUrl && !prefersReducedMotion && !saveData) {
        const video = document.createElement('video');
        video.className = `hero-bg-media hero-video-media hero-bg-video ${index === 0 ? 'is-active' : ''}`;
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
        mediaTrack.appendChild(video);
      } else if (imageUrl) {
        const img = document.createElement('img');
        img.className = `hero-bg-media ${index === 0 ? 'is-active' : ''}`;
        img.src = imageUrl;
        img.alt = item.title || 'AlphaZee featured piece';
        img.loading = index === 0 ? 'eager' : 'lazy';
        img.dataset.slideIndex = String(index);
        mediaTrack.appendChild(img);
      } else {
        const fallbackBg = document.createElement('div');
        fallbackBg.className = `hero-bg-media ${index === 0 ? 'is-active' : ''}`;
        fallbackBg.style.background = '#eeece6';
        fallbackBg.dataset.slideIndex = String(index);
        mediaTrack.appendChild(fallbackBg);
      }
    });

    const overlay = document.createElement('div');
    overlay.className = 'hero-overlay';

    const motif = document.createElement('div');
    motif.className = 'hero-motif';
    motif.setAttribute('aria-hidden', 'true');
    motif.textContent = 'AZ';

    // 2. Continuous Horizontal Marquee of Pure Featured Picture Cards (Zero text, click to view product)
    const pictureCards = [];
    heroItems.forEach(item => {
      const img = sanitizeMediaUrl(item.image_url || item.hero_image_url || item.poster_url || item.hero_poster_url, '');
      if (img) {
        pictureCards.push({
          id: item.collection_id ? null : item.id,
          slug: item.slug || item.target_product_slug || item.target_collection_slug,
          title: item.title,
          image_url: img,
        });
      }
    });

    catalogProducts.forEach(prod => {
      const img = sanitizeMediaUrl(prod.primary_image_url || prod.image_url, '');
      if (img && !pictureCards.some(c => c.slug === prod.slug || (c.id && c.id === prod.id))) {
        pictureCards.push({
          id: prod.id,
          slug: prod.slug,
          title: prod.title,
          image_url: img,
        });
      }
    });

    if (pictureCards.length === 0) {
      heroItems.forEach(item => {
        pictureCards.push({
          id: item.collection_id ? null : item.id,
          slug: item.slug,
          title: item.title,
          image_url: sanitizeMediaUrl(item.poster_url || item.image_url || '', ''),
        });
      });
    }

    const marqueeContainer = document.createElement('div');
    marqueeContainer.className = 'hero-marquee-container';
    marqueeContainer.setAttribute('aria-label', 'Featured Products Horizontal Showcase');

    const marqueeTrack = document.createElement('div');
    marqueeTrack.className = `hero-marquee-track ${isUserPaused ? 'is-paused' : ''}`;

    const repeatedList = pictureCards.filter((card, index, all) =>
      index === all.findIndex(other => other.image_url === card.image_url)).slice(0, 6);

    repeatedList.forEach((card, cIndex) => {
      if (!card.image_url) return;
      const cardEl = document.createElement('div');
      cardEl.className = 'hero-picture-card';
      cardEl.setAttribute('role', 'button');
      cardEl.setAttribute('tabindex', '0');
      cardEl.setAttribute('aria-label', card.title ? `View ${card.title}` : 'Featured piece');
      cardEl.dataset.slug = card.slug || '';
      cardEl.dataset.id = card.id || '';

      const img = document.createElement('img');
      img.className = 'hero-picture-img';
      img.src = card.image_url;
      img.alt = card.title || 'AlphaZee Featured Piece';
      img.loading = cIndex < 6 ? 'eager' : 'lazy';

      cardEl.appendChild(img);

      const handleCardClick = () => {
        if (onProductClick && (card.slug || card.id)) {
          onProductClick(card.slug || card.id);
        } else {
          const featured = document.querySelector('#featured');
          if (featured) featured.scrollIntoView({ behavior: 'smooth' });
        }
      };

      cardEl.addEventListener('click', handleCardClick);
      cardEl.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handleCardClick();
        }
      });

      marqueeTrack.appendChild(cardEl);
    });

    marqueeContainer.appendChild(marqueeTrack);

    // 3. Accessible Slide Content Container (Maintains full screen-reader and test accessibility)
    const container = document.createElement('div');
    container.className = 'container hero-content-wrapper';

    const track = document.createElement('div');
    track.className = 'hero-slides-track';

    heroItems.forEach((item, index) => {
      const slide = document.createElement('div');
      slide.className = `hero-slide ${index === 0 ? 'is-active' : ''}`;
      slide.dataset.index = String(index);
      slide.setAttribute('role', 'group');
      slide.setAttribute('aria-hidden', String(index !== 0));
      slide.inert = index !== 0;
      slide.setAttribute('aria-roledescription', 'slide');
      slide.setAttribute('aria-label', `${index + 1} of ${heroItems.length}: ${item.title || 'Featured'}`);

      const safeTitle = escapeHtml(item.title || 'Selected by AlphaZee');
      const safeBenefit = escapeHtml(item.benefit || item.hero_benefit || 'Clothing and accessories for your next look.');
      const priceDisplay = (item.min_price !== undefined || item.min_price_minor !== undefined)
        ? formatDisplayPrice(item.min_price ?? item.min_price_minor)
        : null;
      const priceText = priceDisplay && priceDisplay !== 'Price unavailable' ? `From ${priceDisplay}` : '';

      slide.innerHTML = `
        <div class="hero-text-content">
          <span class="hero-eyebrow">Selected by AlphaZee</span>
          <${index === 0 ? 'h1' : 'h2'} class="hero-title">${safeTitle}</${index === 0 ? 'h1' : 'h2'}>
          <p class="hero-desc">${safeBenefit}</p>
          ${priceText ? `<div class="hero-price-tag">${priceText}</div>` : ''}
          <div class="hero-cta-group">
            <button class="btn btn-hero hero-cta-btn" data-slug="${escapeHtml(item.slug || '')}" data-id="${escapeHtml(item.id || '')}">
              ${item.slug || item.id ? 'View the piece' : 'Explore Pieces'}
            </button>
            <a href="#collections" class="btn btn-secondary hero-secondary-btn">
              Browse collections
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

    // 4. Navigation & Discreet Accessible Playback Controls Bar
    const controls = document.createElement('div');
    controls.className = 'hero-controls';
    controls.innerHTML = `
      ${!isSingle ? `<button class="hero-ctrl-btn" id="hero-prev" aria-label="Previous Slide">${directionIcon(false)}</button>` : ''}
      <button class="hero-ctrl-btn" id="hero-play-pause" aria-label="${isUserPaused ? 'Resume hero playback' : 'Pause hero playback'}" title="${isUserPaused ? 'Resume' : 'Pause'}">
        ${playbackIcon(isUserPaused)}
      </button>
      <span class="hero-slide-indicator" id="hero-indicator">1 / ${heroItems.length}</span>
      ${!isSingle ? `<button class="hero-ctrl-btn" id="hero-next" aria-label="Next Slide">${directionIcon(true)}</button>` : ''}
    `;

    controls.querySelector('#hero-prev')?.addEventListener('click', () => goToSlide(currentSlide - 1));
    controls.querySelector('#hero-next')?.addEventListener('click', () => goToSlide(currentSlide + 1));
    controls.querySelector('#hero-play-pause')?.addEventListener('click', togglePlayPause);

    if (typeof section.replaceChildren === 'function') {
      section.replaceChildren(bgContainer, overlay, motif, marqueeContainer, container, controls);
    } else {
      section.innerHTML = '';
      section.appendChild(bgContainer);
      section.appendChild(overlay);
      section.appendChild(motif);
      section.appendChild(marqueeContainer);
      section.appendChild(container);
      section.appendChild(controls);
    }

    setupObserver();
    scheduleImageSlide();
  }

  function handleAutoplayReject() {
    isUserPaused = true;
    updatePlayPauseButton();
  }

  function updatePlayPauseButton() {
    const btn = section.querySelector('#hero-play-pause');
    if (!btn) return;
    btn.innerHTML = playbackIcon(isUserPaused);
    btn.setAttribute('aria-label', isUserPaused ? 'Resume hero playback' : 'Pause hero playback');
    btn.title = isUserPaused ? 'Resume' : 'Pause';

    const track = section.querySelector('.hero-marquee-track');
    if (track) {
      track.classList.toggle('is-paused', isUserPaused);
    }
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
      }, 5000);
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

    // 1. Horizontal slide animation for media track
    const mediaTrack = section.querySelector('.hero-media-track');
    if (mediaTrack && mediaTrack.style) {
      mediaTrack.style.transform = `translateX(-${currentSlide * 100}%)`;
    }

    // 2. Horizontal slide animation for editorial text track
    const slidesTrack = section.querySelector('.hero-slides-track');
    if (slidesTrack && slidesTrack.style) {
      slidesTrack.style.transform = `translateX(-${currentSlide * 100}%)`;
    }

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
      slide.setAttribute('aria-hidden', String(i !== currentSlide));
      slide.inert = i !== currentSlide;
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
    alive = true;
    const request = ++generation;
    try {
      let items = [];
      let extraProds = [];
      try {
        const slidesRes = await fetchHeroSlides();
        const slides = Array.isArray(slidesRes) ? slidesRes : (slidesRes?.slides || []);
        if (slides.length > 0) {
          items = slides.map(s => ({
            id: s.target_product_id || null,
            collection_id: s.target_collection_id || null,
            slug: s.target_product_slug || s.product?.slug || null,
            title: s.title || s.product?.title || 'Selected by AlphaZee',
            benefit: s.benefit || s.product?.hero_benefit || 'Clothing and accessories for your next look.',
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

      try {
        const prodsRes = await fetchProducts({ pageSize: 12 });
        extraProds = prodsRes?.products || [];
      } catch {
        // Ignore in unit test or offline mode
      }

      if (!alive || request !== generation) return;
      clearImageTimer();
      section.querySelectorAll('video').forEach(video => video.pause?.());
      currentSlide = 0;
      heroItems = items;
      catalogProducts = extraProds;
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

