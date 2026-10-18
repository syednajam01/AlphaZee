import { escapeHtml as esc, sanitizeMediaUrl, createSafeImageElement } from '../utils/dom.js';
import { mediaForVariant } from '../utils/productMedia.js';

export function mountProductGallery(host, product, variantId) {
  const media = mediaForVariant(product, variantId);
  const specific = media.findIndex(m => m.variant_id === variantId);
  let index = specific >= 0 ? specific : Math.max(0, media.findIndex(m => m.role === 'primary'));
  if (index < 0 || index >= media.length) index = 0;
  let alive = true;
  let lightboxElement = null;
  let lastFocusedTrigger = null;

  host.innerHTML = `
    <div class="product-gallery-stage" tabindex="0" role="region" aria-roledescription="carousel" aria-label="Product media gallery">
      <div class="product-gallery-media-wrapper"></div>
      
      <button type="button" class="gallery-nav-btn gallery-prev-btn" id="gallery-prev-btn" aria-label="Previous slide" ${media.length <= 1 ? 'style="display: none;" disabled' : ''}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="15 18 9 12 15 6"></polyline>
        </svg>
      </button>
      
      <button type="button" class="gallery-nav-btn gallery-next-btn" id="gallery-next-btn" aria-label="Next slide" ${media.length <= 1 ? 'style="display: none;" disabled' : ''}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="9 18 15 12 9 6"></polyline>
        </svg>
      </button>

      <button type="button" class="gallery-zoom-btn" id="gallery-zoom-btn" aria-label="Enlarge image" title="Enlarge image">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="11" cy="11" r="8"></circle>
          <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          <line x1="11" y1="8" x2="11" y2="14"></line>
          <line x1="8" y1="11" x2="14" y2="11"></line>
        </svg>
      </button>

      <div class="gallery-counter" id="gallery-counter" aria-live="polite" ${media.length <= 1 ? 'style="display: none;"' : ''}>
        <span class="gallery-current-num">${media.length > 0 ? index + 1 : 0}</span> / <span class="gallery-total-num">${media.length}</span>
      </div>
    </div>

    <div class="product-gallery-thumbs" role="group" aria-label="Product media">
      ${media.map((m, i) => `
        <button type="button" class="option-pill product-gallery-thumb" data-gallery-index="${i}" aria-label="${esc((m.kind === 'video' ? 'Play video: ' : 'View image: ') + (m.alt_text || product.title))}" aria-pressed="${i === index}">
          ${m.kind === 'video' ? 'Video' : 'Image'} ${i + 1}
        </button>
      `).join('')}
    </div>

    <p class="product-media-feedback" role="status" aria-live="polite"></p>
  `;

  const stage = host.querySelector('.product-gallery-stage');
  const mediaWrapper = host.querySelector('.product-gallery-media-wrapper');
  const feedback = host.querySelector('[role="status"]');
  const prevBtn = host.querySelector('#gallery-prev-btn');
  const nextBtn = host.querySelector('#gallery-next-btn');
  const zoomBtn = host.querySelector('#gallery-zoom-btn');
  const counterCurrent = host.querySelector('.gallery-current-num');

  function pause() {
    stage.querySelectorAll('video').forEach(v => v.pause?.());
  }

  function openLightbox(mediaIndex) {
    const item = media[mediaIndex];
    if (!item || item.kind === 'video' || typeof document === 'undefined') return;
    pause();

    lastFocusedTrigger = document.activeElement;
    closeLightbox();

    lightboxElement = document.createElement('div');
    lightboxElement.id = 'gallery-lightbox';
    lightboxElement.className = 'gallery-lightbox';
    lightboxElement.setAttribute('role', 'dialog');
    lightboxElement.setAttribute('aria-modal', 'true');
    lightboxElement.setAttribute('aria-label', `Enlarged view of ${item.alt_text || product.title}`);

    lightboxElement.innerHTML = `
      <div class="gallery-lightbox-backdrop" aria-hidden="true"></div>
      <div class="gallery-lightbox-content">
        <button type="button" class="gallery-lightbox-close" id="gallery-lightbox-close" aria-label="Close enlarged view">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
        <img class="gallery-lightbox-img" src="${sanitizeMediaUrl(item.url, '')}" alt="${esc(item.alt_text || product.title)}" />
        ${media.length > 1 ? `
          <div class="gallery-lightbox-counter">${mediaIndex + 1} of ${media.length}</div>
        ` : ''}
      </div>
    `;

    if (document.body?.appendChild) {
      document.body.appendChild(lightboxElement);
    }
    document.body?.classList?.add('lightbox-open');
    if (document.body?.style) document.body.style.overflow = 'hidden';

    const closeBtn = lightboxElement.querySelector('#gallery-lightbox-close');
    const backdrop = lightboxElement.querySelector('.gallery-lightbox-backdrop');

    closeBtn?.addEventListener('click', closeLightbox);
    backdrop?.addEventListener('click', closeLightbox);
    closeBtn?.focus?.();
  }

  function closeLightbox() {
    if (!lightboxElement) return;
    if (typeof lightboxElement.remove === 'function') {
      lightboxElement.remove();
    } else if (lightboxElement.parentElement?.removeChild) {
      lightboxElement.parentElement.removeChild(lightboxElement);
    } else if (lightboxElement.parentElement?.children) {
      const idx = lightboxElement.parentElement.children.indexOf(lightboxElement);
      if (idx !== -1) lightboxElement.parentElement.children.splice(idx, 1);
    }
    lightboxElement = null;
    if (typeof document !== 'undefined') {
      document.body?.classList?.remove('lightbox-open');
      if (document.body?.style) document.body.style.overflow = '';
    }
    if (lastFocusedTrigger && lastFocusedTrigger.isConnected !== false) {
      lastFocusedTrigger.focus?.();
    }
    lastFocusedTrigger = null;
  }

  function show(next) {
    pause();
    index = next;
    const item = media[index];
    mediaWrapper.innerHTML = '';
    feedback.textContent = '';

    host.querySelectorAll('[data-gallery-index]').forEach(button => {
      const isSelected = Number(button.dataset.galleryIndex) === index;
      button.setAttribute('aria-pressed', String(isSelected));
      if (isSelected) {
        button.classList.add('is-active');
      } else {
        button.classList.remove('is-active');
      }
    });

    if (counterCurrent) {
      counterCurrent.textContent = String(media.length > 0 ? index + 1 : 0);
    }

    if (!item) {
      mediaWrapper.innerHTML = '<div class="product-gallery-neutral-fallback"><span>No media available</span></div>';
      if (zoomBtn) zoomBtn.style.display = 'none';
      return;
    }

    if (item.kind === 'video') {
      if (zoomBtn) zoomBtn.style.display = 'none';
      const video = document.createElement('video');
      video.className = 'modal-img product-gallery-video';
      video.controls = true;
      video.playsInline = true;
      video.preload = 'none';
      const poster = sanitizeMediaUrl(item.poster_url, '');
      if (poster) video.poster = poster;
      video.setAttribute('aria-label', item.alt_text || product.title);
      const supported = ['video/mp4', 'video/webm'].includes(item.content_type) && poster;
      if (supported) {
        video.src = sanitizeMediaUrl(item.url, '');
      } else {
        feedback.textContent = 'This video is unavailable. Select another image or video.';
      }
      video.addEventListener('error', () => {
        if (alive) feedback.textContent = 'This browser could not play the video. Select another image or video.';
      });
      mediaWrapper.appendChild(video);
    } else {
      if (zoomBtn) zoomBtn.style.display = 'flex';
      const image = createSafeImageElement({
        src: item.url,
        alt: item.alt_text || product.title,
        className: 'modal-img',
        loading: index === 0 ? 'eager' : 'lazy',
        width: item.width,
        height: item.height
      });
      image.style.cursor = 'zoom-in';
      image.addEventListener('click', () => openLightbox(index));
      image.addEventListener('error', () => {
        if (alive) feedback.textContent = 'This image could not load. Select another image.';
      });
      mediaWrapper.appendChild(image);
    }
  }

  // Prev / Next button clicks
  prevBtn?.addEventListener('click', () => {
    if (media.length <= 1) return;
    const prev = index - 1 < 0 ? media.length - 1 : index - 1;
    show(prev);
  });

  nextBtn?.addEventListener('click', () => {
    if (media.length <= 1) return;
    const next = (index + 1) % media.length;
    show(next);
  });

  // Zoom button click
  zoomBtn?.addEventListener('click', () => {
    openLightbox(index);
  });

  // Keyboard navigation on gallery stage
  stage?.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft') {
      if (media.length <= 1) return;
      e.preventDefault();
      const prev = index - 1 < 0 ? media.length - 1 : index - 1;
      show(prev);
    } else if (e.key === 'ArrowRight') {
      if (media.length <= 1) return;
      e.preventDefault();
      const next = (index + 1) % media.length;
      show(next);
    } else if (e.key === 'Home') {
      if (media.length <= 1) return;
      e.preventDefault();
      show(0);
    } else if (e.key === 'End') {
      if (media.length <= 1) return;
      e.preventDefault();
      show(media.length - 1);
    } else if ((e.key === 'Enter' || e.key === ' ') && e.target === stage) {
      const item = media[index];
      if (item && item.kind !== 'video') {
        e.preventDefault();
        openLightbox(index);
      }
    }
  });

  // Global keydown for Escape when lightbox is active
  function handleDocumentKeyDown(e) {
    if (!alive) return;
    if (e.key === 'Escape' && lightboxElement) {
      e.preventDefault();
      closeLightbox();
    }
  }
  if (typeof document !== 'undefined') {
    document.addEventListener?.('keydown', handleDocumentKeyDown);
  }

  // Document visibility change listener (pauses active video on tab switch)
  function handleVisibilityChange() {
    if (typeof document !== 'undefined' && document.hidden) {
      pause();
    }
  }
  if (typeof document !== 'undefined') {
    document.addEventListener?.('visibilitychange', handleVisibilityChange);
  }

  // Touch gesture swipe detection
  let touchStartX = 0;
  let touchStartY = 0;
  let touchDeltaX = 0;
  let touchDeltaY = 0;

  stage?.addEventListener('touchstart', (e) => {
    if (!e.touches || e.touches.length === 0) return;
    touchStartX = e.touches[0].clientX;
    touchStartY = e.touches[0].clientY;
    touchDeltaX = 0;
    touchDeltaY = 0;
  }, { passive: true });

  stage?.addEventListener('touchmove', (e) => {
    if (!e.touches || e.touches.length === 0) return;
    touchDeltaX = e.touches[0].clientX - touchStartX;
    touchDeltaY = e.touches[0].clientY - touchStartY;
  }, { passive: true });

  stage?.addEventListener('touchend', () => {
    if (media.length <= 1) return;
    const absX = Math.abs(touchDeltaX);
    const absY = Math.abs(touchDeltaY);
    if (absX > 40 && absX > absY) {
      if (touchDeltaX < 0) {
        show((index + 1) % media.length);
      } else {
        show(index - 1 < 0 ? media.length - 1 : index - 1);
      }
    }
    touchDeltaX = 0;
    touchDeltaY = 0;
  }, { passive: true });

  // Thumbnail click handlers
  host.querySelectorAll('[data-gallery-index]').forEach(button => {
    button.addEventListener('click', () => show(Number(button.dataset.galleryIndex)));
  });

  // Initial show
  show(index);

  return {
    destroy() {
      alive = false;
      pause();
      closeLightbox();
      if (typeof document !== 'undefined') {
        document.removeEventListener?.('keydown', handleDocumentKeyDown);
        document.removeEventListener?.('visibilitychange', handleVisibilityChange);
      }
    }
  };
}
