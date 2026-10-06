import { heroProducts } from '../data/products.js';

export function createHero(onProductClick) {
  const section = document.createElement('section');
  section.className = 'hero-section';
  section.setAttribute('aria-label', 'Featured Products Showcase');

  let currentSlide = 0;
  const totalSlides = heroProducts.length;
  let autoAdvanceInterval = null;
  let isPlaying = true;
  let prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let saveData = navigator.connection && navigator.connection.saveData;

  // Background media container
  const bgContainer = document.createElement('div');
  bgContainer.className = 'hero-bg-container';

  heroProducts.forEach((item, index) => {
    // Media layer
    const video = document.createElement('video');
    video.className = `hero-bg-media ${index === 0 ? 'is-active' : ''}`;
    video.poster = item.poster;
    video.muted = true;
    video.loop = true;
    video.playsInline = true;
    video.setAttribute('aria-hidden', 'true');
    video.setAttribute('tabindex', '-1');

    // Only set src for first slide initially or if reduced motion is disabled
    if (!prefersReducedMotion && !saveData) {
      if (index === 0) {
        video.src = item.video;
        video.play().catch(() => {
          // Keep poster on play failure
        });
      }
    }

    video.dataset.slideIndex = index;
    bgContainer.appendChild(video);
  });

  const overlay = document.createElement('div');
  overlay.className = 'hero-overlay';

  const motif = document.createElement('div');
  motif.className = 'hero-motif';
  motif.setAttribute('aria-hidden', 'true');
  motif.textContent = 'AZ';

  // Slides Track & Container
  const container = document.createElement('div');
  container.className = 'container hero-content-wrapper';

  const track = document.createElement('div');
  track.className = 'hero-slides-track';

  heroProducts.forEach((item, index) => {
    const slide = document.createElement('div');
    slide.className = `hero-slide ${index === 0 ? 'is-active' : ''}`;
    slide.setAttribute('role', 'group');
    slide.setAttribute('aria-roledescription', 'slide');
    slide.setAttribute('aria-label', `${index + 1} of ${totalSlides}: ${item.title}`);

    slide.innerHTML = `
      <div class="hero-grid">
        <div class="hero-image-col">
          <div class="hero-product-img-wrapper">
            <img 
              src="${item.image}" 
              alt="${item.title}" 
              class="hero-product-img" 
              loading="${index === 0 ? 'eager' : 'lazy'}"
              width="440"
              height="440"
            />
          </div>
        </div>
        <div class="hero-info-col">
          <span class="badge hero-badge-tag">${item.stockStatus}</span>
          <h1 class="hero-title">${item.title}</h1>
          <p class="hero-benefit">${item.benefit}</p>
          <div class="hero-meta-row">
            <span class="hero-price">${item.formattedPrice}</span>
            <span class="hero-price-note">Tax included • Free exchange</span>
          </div>
          <div class="hero-actions">
            <button class="btn btn-hero btn-shop-hero" data-product-id="${item.productId}">
              Shop this product
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="5" y1="12" x2="19" y2="12"></line>
                <polyline points="12 5 19 12 12 19"></polyline>
              </svg>
            </button>
          </div>
        </div>
      </div>
    `;

    slide.querySelector('.btn-shop-hero').addEventListener('click', () => {
      if (onProductClick) {
        onProductClick(item.productId);
      }
    });

    track.appendChild(slide);
  });

  // Controls bar
  const controlsBar = document.createElement('div');
  controlsBar.className = 'hero-controls-bar';

  if (totalSlides > 1) {
    controlsBar.innerHTML = `
      <div class="hero-indicators" role="tablist" aria-label="Hero slide selection">
        ${heroProducts.map((_, i) => `
          <button 
            class="hero-indicator-dot ${i === 0 ? 'is-active' : ''}" 
            role="tab" 
            aria-selected="${i === 0}" 
            aria-label="Go to slide ${i + 1}"
            data-index="${i}">
          </button>
        `).join('')}
      </div>

      <div class="hero-nav-buttons">
        <button class="hero-ctrl-btn hero-motion-toggle" id="hero-motion-toggle" aria-label="Pause slide transitions and video">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
            <rect x="6" y="4" width="4" height="16"></rect>
            <rect x="14" y="4" width="4" height="16"></rect>
          </svg>
          <span class="motion-text">Pause</span>
        </button>

        <button class="hero-ctrl-btn" id="hero-btn-prev" aria-label="Previous featured product">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="15 18 9 12 15 6"></polyline>
          </svg>
        </button>

        <button class="hero-ctrl-btn" id="hero-btn-next" aria-label="Next featured product">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
        </button>
      </div>
    `;
  }

  container.appendChild(track);
  if (totalSlides > 1) {
    container.appendChild(controlsBar);
  }

  section.appendChild(bgContainer);
  section.appendChild(overlay);
  section.appendChild(motif);
  section.appendChild(container);

  // Transition Logic
  function goToSlide(index) {
    currentSlide = (index + totalSlides) % totalSlides;

    // Slide track
    track.style.transform = `translateX(-${currentSlide * 100}%)`;

    // Active slide class
    const slides = track.querySelectorAll('.hero-slide');
    slides.forEach((sl, i) => {
      sl.classList.toggle('is-active', i === currentSlide);
    });

    // Indicators
    const dots = controlsBar.querySelectorAll('.hero-indicator-dot');
    dots.forEach((dot, i) => {
      const active = i === currentSlide;
      dot.classList.toggle('is-active', active);
      dot.setAttribute('aria-selected', active);
    });

    // Background video
    const videos = bgContainer.querySelectorAll('.hero-bg-media');
    videos.forEach((vid, i) => {
      if (i === currentSlide) {
        vid.classList.add('is-active');
        if (!prefersReducedMotion && !saveData && isPlaying) {
          if (!vid.src) {
            vid.src = heroProducts[i].video;
          }
          vid.play().catch(() => {});
        }
      } else {
        vid.classList.remove('is-active');
        vid.pause();
      }
    });
  }

  function startAutoAdvance() {
    if (prefersReducedMotion || !isPlaying || totalSlides <= 1) return;
    stopAutoAdvance();
    autoAdvanceInterval = setInterval(() => {
      goToSlide(currentSlide + 1);
    }, 8000);
  }

  function stopAutoAdvance() {
    if (autoAdvanceInterval) {
      clearInterval(autoAdvanceInterval);
      autoAdvanceInterval = null;
    }
  }

  // Event handlers
  if (totalSlides > 1) {
    controlsBar.querySelector('#hero-btn-prev')?.addEventListener('click', () => {
      goToSlide(currentSlide - 1);
      startAutoAdvance();
    });

    controlsBar.querySelector('#hero-btn-next')?.addEventListener('click', () => {
      goToSlide(currentSlide + 1);
      startAutoAdvance();
    });

    const dots = controlsBar.querySelectorAll('.hero-indicator-dot');
    dots.forEach((dot) => {
      dot.addEventListener('click', () => {
        const idx = parseInt(dot.dataset.index, 10);
        goToSlide(idx);
        startAutoAdvance();
      });
    });

    const motionBtn = controlsBar.querySelector('#hero-motion-toggle');
    if (motionBtn) {
      motionBtn.addEventListener('click', () => {
        isPlaying = !isPlaying;
        const textSpan = motionBtn.querySelector('.motion-text');
        if (isPlaying) {
          textSpan.textContent = 'Pause';
          motionBtn.querySelector('svg').innerHTML = `
            <rect x="6" y="4" width="4" height="16"></rect>
            <rect x="14" y="4" width="4" height="16"></rect>
          `;
          startAutoAdvance();
          const activeVid = bgContainer.querySelector(`.hero-bg-media[data-slide-index="${currentSlide}"]`);
          if (activeVid && !prefersReducedMotion && !saveData) activeVid.play().catch(() => {});
        } else {
          textSpan.textContent = 'Play';
          motionBtn.querySelector('svg').innerHTML = `
            <polygon points="5 3 19 12 5 21 5 3"></polygon>
          `;
          stopAutoAdvance();
          bgContainer.querySelectorAll('.hero-bg-media').forEach(v => v.pause());
        }
      });
    }

    // Touch Swipe handling (horizontal only, without blocking vertical scroll)
    let touchStartX = 0;
    let touchStartY = 0;
    let touchEndX = 0;
    let touchEndY = 0;

    track.addEventListener('touchstart', (e) => {
      touchStartX = e.changedTouches[0].screenX;
      touchStartY = e.changedTouches[0].screenY;
    }, { passive: true });

    track.addEventListener('touchend', (e) => {
      touchEndX = e.changedTouches[0].screenX;
      touchEndY = e.changedTouches[0].screenY;
      const diffX = touchStartX - touchEndX;
      const diffY = touchStartY - touchEndY;

      // Only horizontal swipe if diffX is significantly larger than vertical diffY
      if (Math.abs(diffX) > 40 && Math.abs(diffX) > Math.abs(diffY)) {
        if (diffX > 0) {
          goToSlide(currentSlide + 1);
        } else {
          goToSlide(currentSlide - 1);
        }
        startAutoAdvance();
      }
    }, { passive: true });

    // Pause on hover or focus
    section.addEventListener('mouseenter', stopAutoAdvance);
    section.addEventListener('mouseleave', () => {
      if (isPlaying) startAutoAdvance();
    });
    section.addEventListener('focusin', stopAutoAdvance);
    section.addEventListener('focusout', () => {
      if (isPlaying) startAutoAdvance();
    });
  }

  // IntersectionObserver to pause when off-screen
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) {
        stopAutoAdvance();
        bgContainer.querySelectorAll('.hero-bg-media').forEach(v => v.pause());
      } else if (isPlaying) {
        startAutoAdvance();
        const activeVid = bgContainer.querySelector(`.hero-bg-media[data-slide-index="${currentSlide}"]`);
        if (activeVid && !prefersReducedMotion && !saveData) activeVid.play().catch(() => {});
      }
    });
  }, { threshold: 0.2 });

  observer.observe(section);

  if (!prefersReducedMotion && isPlaying) {
    startAutoAdvance();
  }

  return section;
}
