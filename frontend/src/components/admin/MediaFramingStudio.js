import { escapeHtml as esc } from '../../utils/dom.js';

/**
 * Reusable Interactive Media Framing & Crop Studio Modal.
 * Supports both 16:9 Widescreen (Hero Banner) and 9:16 Vertical Portrait (Product/Collection Cards).
 */
export function openFramingStudio({
  mediaUrl,
  isVideo = false,
  title = 'Adjust Media Framing',
  aspectRatio = '16:9', // '16:9' or '9:16'
  initialFocalX = 50,
  initialFocalY = 50,
  initialZoom = 1.0,
  bannerData = null,
  cardData = null,
  onSave,
  onCancel,
}) {
  let focalX = Math.max(0, Math.min(100, Math.round(Number(initialFocalX) || 50)));
  let focalY = Math.max(0, Math.min(100, Math.round(Number(initialFocalY) || 50)));
  let zoom = Math.max(1.0, Math.min(2.5, Number(initialZoom) || 1.0));
  let viewportMode = 'desktop'; // 'desktop' or 'mobile'

  const isWidescreen = aspectRatio === '16:9';
  const overlay = document.createElement('div');
  overlay.id = 'media-framing-studio-modal';
  overlay.style.cssText = `
    position: fixed; inset: 0; z-index: 10000;
    background: rgba(8, 14, 11, 0.94);
    backdrop-filter: blur(8px);
    display: flex; align-items: center; justify-content: center;
    padding: 20px; box-sizing: border-box;
    overflow-y: auto; scrollbar-width: none;
  `;

  function renderModalMarkup() {
    overlay.innerHTML = `
      <div class="framing-modal-card" style="
        background: #121815; border: 1px solid #2A3831; border-radius: 12px;
        width: 100%; max-width: 1180px; max-height: 94vh; display: flex; flex-direction: column;
        box-shadow: 0 24px 60px rgba(0,0,0,0.7); overflow: hidden; color: #FFF;
      ">
        <!-- Header -->
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 16px 24px; border-bottom: 1px solid #23322B; background: #161E1A;">
          <div style="display: flex; align-items: center; gap: 12px;">
            <div style="width: 32px; height: 32px; border-radius: 8px; background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.3); display: flex; align-items: center; justify-content: center; color: #10B981;">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="22" y1="12" x2="18" y2="12"></line><line x1="6" y1="12" x2="2" y2="12"></line><line x1="12" y1="6" x2="12" y2="2"></line><line x1="12" y1="22" x2="12" y2="18"></line></svg>
            </div>
            <div>
              <h3 style="margin: 0; font-size: 1.0625rem; font-weight: 600; color: #FFFFFF;">${esc(title)}</h3>
              <p style="margin: 2px 0 0 0; font-size: 0.75rem; color: #9AA39E;">
                ${isWidescreen ? '16:9 Widescreen Framing Studio • Non-destructive repositioning' : '9:16 Vertical Card Framing Studio • Mobile & Desktop responsive focus'}
              </p>
            </div>
          </div>
          <div style="display: flex; align-items: center; gap: 12px;">
            <span style="font-size: 0.6875rem; font-weight: 600; letter-spacing: 0.05em; padding: 4px 8px; border-radius: 4px; background: #23322B; color: #38BDF8; border: 1px solid rgba(56, 189, 248, 0.25);">
              ${isWidescreen ? '16:9 BANNER' : '9:16 CARD'}
            </span>
            <button type="button" class="btn btn-secondary btn-icon-only" id="framing-modal-close" title="Close editor" aria-label="Close editor" style="width: 32px; height: 32px;">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
            </button>
          </div>
        </div>

        <!-- Body Grid -->
        <div style="flex: 1; overflow-y: auto; scrollbar-width: none; padding: 20px 24px; display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 24px;">
          <!-- Left: Interactive Canvas & Adjustment Controls -->
          <div style="display: flex; flex-direction: column; gap: 16px;">
            <div style="display: flex; align-items: center; justify-content: space-between;">
              <span style="font-size: 0.8125rem; font-weight: 600; color: #E5E6DE;">Interactive Focal Canvas</span>
              <span id="framing-reticle-pill" style="font-size: 0.75rem; font-family: monospace; color: #F59E0B; background: rgba(245, 158, 11, 0.1); padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(245, 158, 11, 0.3);">
                ${focalX}% X, ${focalY}% Y | ${zoom.toFixed(2)}x
              </span>
            </div>

            <!-- Canvas Container -->
            <div id="framing-canvas" style="
              position: relative; width: 100%; aspect-ratio: ${isWidescreen ? '16 / 9' : '9 / 16'};
              max-height: ${isWidescreen ? '320px' : '380px'};
              background: #000; border-radius: 8px; overflow: hidden; cursor: crosshair;
              box-shadow: inset 0 0 0 1px #2A3831; user-select: none;
            ">
              <!-- Media element inside canvas -->
              ${isVideo ? `
                <video src="${esc(mediaUrl)}" muted playsinline autoplay loop style="
                  width: 100%; height: 100%; object-fit: cover;
                  object-position: ${focalX}% ${focalY}%;
                  transform: scale(${zoom});
                  pointer-events: none; transition: object-position 0.05s ease, transform 0.05s ease;
                " id="canvas-media-el"></video>
              ` : `
                <img src="${esc(mediaUrl)}" alt="Framing Preview" style="
                  width: 100%; height: 100%; object-fit: cover;
                  object-position: ${focalX}% ${focalY}%;
                  transform: scale(${zoom});
                  pointer-events: none; transition: object-position 0.05s ease, transform 0.05s ease;
                " id="canvas-media-el">
              `}

              <!-- Rule of thirds grid lines -->
              <div style="position: absolute; inset: 0; pointer-events: none;">
                <div style="position: absolute; left: 33.33%; top: 0; bottom: 0; width: 1px; background: rgba(255,255,255,0.22); border-right: 1px dashed rgba(0,0,0,0.5);"></div>
                <div style="position: absolute; left: 66.66%; top: 0; bottom: 0; width: 1px; background: rgba(255,255,255,0.22); border-right: 1px dashed rgba(0,0,0,0.5);"></div>
                <div style="position: absolute; top: 33.33%; left: 0; right: 0; height: 1px; background: rgba(255,255,255,0.22); border-bottom: 1px dashed rgba(0,0,0,0.5);"></div>
                <div style="position: absolute; top: 66.66%; left: 0; right: 0; height: 1px; background: rgba(255,255,255,0.22); border-bottom: 1px dashed rgba(0,0,0,0.5);"></div>
              </div>

              <!-- Draggable / Clickable Target Reticle -->
              <div id="canvas-reticle" style="
                position: absolute; left: ${focalX}%; top: ${focalY}%;
                width: 28px; height: 28px; border: 2px solid #F59E0B; border-radius: 50%;
                transform: translate(-50%, -50%); pointer-events: none;
                box-shadow: 0 0 10px rgba(0,0,0,0.9), inset 0 0 6px rgba(245, 158, 11, 0.4);
                display: flex; align-items: center; justify-content: center;
              ">
                <div style="width: 4px; height: 4px; border-radius: 50%; background: #F59E0B;"></div>
                <div style="position: absolute; width: 38px; height: 1px; background: rgba(245, 158, 11, 0.7);"></div>
                <div style="position: absolute; height: 38px; width: 1px; background: rgba(245, 158, 11, 0.7);"></div>
              </div>

              <div style="position: absolute; bottom: 8px; left: 8px; background: rgba(0,0,0,0.7); backdrop-filter: blur(4px); padding: 4px 8px; border-radius: 4px; font-size: 0.6875rem; color: #D1D5DB; pointer-events: none;">
                Click or drag anywhere to place focal point
              </div>
            </div>

            <!-- Fine-tuning Sliders -->
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; background: #161E1A; padding: 14px; border-radius: 8px; border: 1px solid #23322B;">
              <div>
                <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #9AA39E; margin-bottom: 4px;">
                  <span>Horizontal Focus (X)</span>
                  <strong id="val-focal-x" style="color: #FFF;">${focalX}%</strong>
                </div>
                <input type="range" id="slider-focal-x" min="0" max="100" value="${focalX}" style="width: 100%; accent-color: #10B981; cursor: pointer;">
              </div>
              <div>
                <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #9AA39E; margin-bottom: 4px;">
                  <span>Vertical Focus (Y)</span>
                  <strong id="val-focal-y" style="color: #FFF;">${focalY}%</strong>
                </div>
                <input type="range" id="slider-focal-y" min="0" max="100" value="${focalY}" style="width: 100%; accent-color: #10B981; cursor: pointer;">
              </div>
              <div style="grid-column: 1 / -1;">
                <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #9AA39E; margin-bottom: 4px;">
                  <span>Framing Zoom (Crop Scale)</span>
                  <strong id="val-zoom" style="color: #38BDF8;">${zoom.toFixed(2)}x</strong>
                </div>
                <input type="range" id="slider-zoom" min="1.0" max="2.0" step="0.05" value="${zoom}" style="width: 100%; accent-color: #38BDF8; cursor: pointer;">
              </div>
            </div>

            <!-- Quick Alignment Presets -->
            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
              <span style="font-size: 0.75rem; color: #9AA39E;">Presets:</span>
              <button type="button" class="btn btn-secondary btn-preset" data-fx="50" data-fy="20" data-zm="1.0" style="padding: 4px 10px; font-size: 0.75rem;">
                Top Focus (Face / Collar)
              </button>
              <button type="button" class="btn btn-secondary btn-preset" data-fx="50" data-fy="50" data-zm="1.0" style="padding: 4px 10px; font-size: 0.75rem;">
                Center Balance
              </button>
              <button type="button" class="btn btn-secondary btn-preset" data-fx="50" data-fy="80" data-zm="1.0" style="padding: 4px 10px; font-size: 0.75rem;">
                Bottom Focus (Hem / Shoes)
              </button>
              <button type="button" class="btn btn-secondary btn-preset" data-fx="50" data-fy="50" data-zm="1.0" style="padding: 4px 10px; font-size: 0.75rem; color: #FCA5A5;">
                Reset
              </button>
            </div>
          </div>

          <!-- Right: Live Storefront Simulation -->
          <div style="display: flex; flex-direction: column; gap: 16px; border-left: 1px solid #23322B; padding-left: 20px;">
            <div style="display: flex; align-items: center; justify-content: space-between;">
              <span style="font-size: 0.8125rem; font-weight: 600; color: #E5E6DE;">Live Storefront Simulation</span>
              ${isWidescreen ? `
                <div style="display: flex; background: #161E1A; padding: 2px; border-radius: 6px; border: 1px solid #23322B;">
                  <button type="button" id="btn-view-desktop" class="btn ${viewportMode === 'desktop' ? 'btn-primary' : 'btn-secondary'}" style="padding: 3px 10px; font-size: 0.6875rem;">
                    Desktop 16:9
                  </button>
                  <button type="button" id="btn-view-mobile" class="btn ${viewportMode === 'mobile' ? 'btn-primary' : 'btn-secondary'}" style="padding: 3px 10px; font-size: 0.6875rem;">
                    Mobile 390px
                  </button>
                </div>
              ` : `
                <span style="font-size: 0.6875rem; color: #9AA39E;">Storefront Product Card</span>
              `}
            </div>

            <!-- Simulation Box -->
            <div id="simulation-box-container" style="display: flex; align-items: center; justify-content: center; min-height: 340px; background: #0A0F0D; border-radius: 8px; border: 1px solid #23322B; padding: 16px; overflow: hidden;">
              ${isWidescreen ? `
                <!-- 16:9 Banner Storefront Preview -->
                <div id="sim-banner-wrapper" style="
                  position: relative; width: ${viewportMode === 'desktop' ? '100%' : '260px'};
                  aspect-ratio: ${viewportMode === 'desktop' ? '16 / 9' : '9 / 16'};
                  max-height: 320px; border-radius: 8px; overflow: hidden; background: #000;
                  box-shadow: 0 12px 28px rgba(0,0,0,0.5);
                ">
                  <!-- Simulated Banner Background -->
                  ${isVideo ? `
                    <video src="${esc(mediaUrl)}" muted playsinline autoplay loop style="
                      width: 100%; height: 100%; object-fit: cover;
                      object-position: ${focalX}% ${focalY}%;
                      transform: scale(${zoom});
                      pointer-events: none;
                    " id="sim-banner-media"></video>
                  ` : `
                    <img src="${esc(mediaUrl)}" alt="Live Preview" style="
                      width: 100%; height: 100%; object-fit: cover;
                      object-position: ${focalX}% ${focalY}%;
                      transform: scale(${zoom});
                      pointer-events: none;
                    " id="sim-banner-media">
                  `}

                  <!-- Storefront Gradient Scrim -->
                  <div style="
                    position: absolute; inset: 0; pointer-events: none;
                    background: ${viewportMode === 'desktop'
                      ? 'linear-gradient(90deg, rgba(8, 14, 11, 0.88) 0%, rgba(8, 14, 11, 0.65) 44%, rgba(8, 14, 11, 0.25) 75%, rgba(8, 14, 11, 0.12) 100%)'
                      : 'linear-gradient(180deg, rgba(8, 14, 11, 0.20) 0%, rgba(8, 14, 11, 0.55) 45%, rgba(8, 14, 11, 0.85) 100%)'};
                  "></div>

                  <!-- Storefront Typography Overlay -->
                  <div style="position: absolute; inset: 0; padding: ${viewportMode === 'desktop' ? '20px 24px' : '16px'}; display: flex; flex-direction: column; justify-content: ${viewportMode === 'desktop' ? 'center' : 'flex-end'}; z-index: 2; pointer-events: none;">
                    <span style="display: inline-block; font-size: 0.6875rem; font-weight: 600; color: #10B981; letter-spacing: 0.05em; margin-bottom: 6px;">
                      SELECTED BY ALPHAZEE
                    </span>
                    <h2 style="margin: 0 0 6px 0; font-size: ${viewportMode === 'desktop' ? '1.25rem' : '1rem'}; font-weight: 600; color: #FFFFFF;">
                      ${esc(bannerData?.title || 'Featured Drop')}
                    </h2>
                    <p style="margin: 0 0 12px 0; font-size: ${viewportMode === 'desktop' ? '0.8125rem' : '0.6875rem'}; color: #D1D5DB; line-height: 1.4;">
                      ${esc(bannerData?.benefit || 'Our 1st Exclusive Drop. Considered selection.')}
                    </p>
                    <div style="display: inline-block;">
                      <span style="display: inline-block; padding: 6px 14px; background: #145C44; color: #FFF; font-size: 0.75rem; font-weight: 500; border-radius: 4px;">
                        Shop the collection
                      </span>
                    </div>
                  </div>
                </div>
              ` : `
                <!-- 9:16 Product Card Storefront Preview -->
                <div id="sim-card-wrapper" style="
                  width: 220px; background: #FFFFFF; border-radius: 10px; border: 1px solid #E5E6DE;
                  box-shadow: 0 8px 24px rgba(0,0,0,0.3); overflow: hidden; display: flex; flex-direction: column;
                ">
                  <!-- Image area -->
                  <div style="position: relative; width: 100%; aspect-ratio: 3 / 4; background: #F0F0EB; overflow: hidden;">
                    <img src="${esc(mediaUrl)}" alt="Product card preview" style="
                      width: 100%; height: 100%; object-fit: cover;
                      object-position: ${focalX}% ${focalY}%;
                      transform: scale(${zoom});
                      pointer-events: none;
                    " id="sim-card-media">
                    <span style="position: absolute; top: 8px; left: 8px; background: #14231E; color: #FFF; font-size: 0.625rem; font-weight: 600; padding: 2px 6px; border-radius: 4px;">
                      ${esc(cardData?.badge || 'NEW')}
                    </span>
                  </div>

                  <!-- Info area -->
                  <div style="padding: 12px 14px; display: flex; flex-direction: column; gap: 4px; background: #FFF;">
                    <h4 style="margin: 0; font-size: 0.8125rem; font-weight: 600; color: #14231E; line-height: 1.3;">
                      ${esc(cardData?.title || 'Tailored Trench')}
                    </h4>
                    <span style="font-size: 0.8125rem; font-weight: 500; color: #14231E; font-variant-numeric: tabular-nums;">
                      ${esc(cardData?.priceFormatted || 'PKR 14,500')}
                    </span>
                    <button type="button" style="margin-top: 8px; padding: 5px; font-size: 0.6875rem; background: #F3F4F6; color: #14231E; border: 1px solid #E5E7EB; border-radius: 4px; cursor: default;">
                      Quick View
                    </button>
                  </div>
                </div>
              `}
            </div>

            <p style="font-size: 0.75rem; color: #9AA39E; margin: 0; line-height: 1.4;">
              ${isWidescreen
                ? '✓ Real-time storefront simulation updates as you adjust focal coordinates. The subject stays centered on all screens.'
                : '✓ The 9:16 card frame shows the exact appearance shoppers will see in the catalog grid.'}
            </p>
          </div>
        </div>

        <!-- Footer Actions -->
        <div style="display: flex; align-items: center; justify-content: flex-end; gap: 12px; padding: 16px 24px; border-top: 1px solid #23322B; background: #161E1A;">
          <button type="button" class="btn btn-secondary" id="framing-modal-cancel" style="padding: 8px 18px;">
            Cancel
          </button>
          <button type="button" class="btn btn-primary" id="framing-modal-apply" style="padding: 8px 22px; font-weight: 500; display: flex; align-items: center; gap: 8px;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>
            Apply & Save Framing
          </button>
        </div>
      </div>
    `;

    // Wire up events
    const canvas = overlay.querySelector('#framing-canvas');
    const reticle = overlay.querySelector('#canvas-reticle');
    const pill = overlay.querySelector('#framing-reticle-pill');
    const canvasMedia = overlay.querySelector('#canvas-media-el');
    const simMedia = overlay.querySelector(isWidescreen ? '#sim-banner-media' : '#sim-card-media');

    const sliderX = overlay.querySelector('#slider-focal-x');
    const sliderY = overlay.querySelector('#slider-focal-y');
    const sliderZoom = overlay.querySelector('#slider-zoom');
    const valX = overlay.querySelector('#val-focal-x');
    const valY = overlay.querySelector('#val-focal-y');
    const valZoom = overlay.querySelector('#val-zoom');

    function updateLiveView() {
      if (reticle) {
        reticle.style.left = `${focalX}%`;
        reticle.style.top = `${focalY}%`;
      }
      if (pill) {
        pill.textContent = `${focalX}% X, ${focalY}% Y | ${zoom.toFixed(2)}x`;
      }
      if (sliderX) sliderX.value = focalX;
      if (sliderY) sliderY.value = focalY;
      if (sliderZoom) sliderZoom.value = zoom;
      if (valX) valX.textContent = `${focalX}%`;
      if (valY) valY.textContent = `${focalY}%`;
      if (valZoom) valZoom.textContent = `${zoom.toFixed(2)}x`;

      const objPos = `${focalX}% ${focalY}%`;
      const scaleStr = `scale(${zoom})`;

      if (canvasMedia) {
        canvasMedia.style.objectPosition = objPos;
        canvasMedia.style.transform = scaleStr;
      }
      if (simMedia) {
        simMedia.style.objectPosition = objPos;
        simMedia.style.transform = scaleStr;
      }
    }

    // Canvas click & drag
    let isDragging = false;
    function handleCanvasCoords(e) {
      const rect = canvas.getBoundingClientRect();
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      const clientY = e.touches ? e.touches[0].clientY : e.clientY;
      const xPct = Math.round(((clientX - rect.left) / rect.width) * 100);
      const yPct = Math.round(((clientY - rect.top) / rect.height) * 100);
      focalX = Math.max(0, Math.min(100, xPct));
      focalY = Math.max(0, Math.min(100, yPct));
      updateLiveView();
    }

    canvas.addEventListener('mousedown', e => {
      isDragging = true;
      handleCanvasCoords(e);
    });
    window.addEventListener('mousemove', e => {
      if (isDragging) handleCanvasCoords(e);
    });
    window.addEventListener('mouseup', () => {
      isDragging = false;
    });

    // Touch support for mobile admin
    canvas.addEventListener('touchstart', e => {
      isDragging = true;
      handleCanvasCoords(e);
    }, { passive: true });
    window.addEventListener('touchmove', e => {
      if (isDragging) handleCanvasCoords(e);
    }, { passive: true });
    window.addEventListener('touchend', () => {
      isDragging = false;
    });

    // Sliders
    sliderX?.addEventListener('input', e => {
      focalX = Number(e.target.value);
      updateLiveView();
    });
    sliderY?.addEventListener('input', e => {
      focalY = Number(e.target.value);
      updateLiveView();
    });
    sliderZoom?.addEventListener('input', e => {
      zoom = Number(e.target.value);
      updateLiveView();
    });

    // Presets
    overlay.querySelectorAll('.btn-preset').forEach(btn => {
      btn.addEventListener('click', () => {
        focalX = Number(btn.dataset.fx);
        focalY = Number(btn.dataset.fy);
        zoom = Number(btn.dataset.zm || 1.0);
        updateLiveView();
      });
    });

    // Viewport Mode Switcher (Banner)
    overlay.querySelector('#btn-view-desktop')?.addEventListener('click', () => {
      viewportMode = 'desktop';
      renderModalMarkup();
    });
    overlay.querySelector('#btn-view-mobile')?.addEventListener('click', () => {
      viewportMode = 'mobile';
      renderModalMarkup();
    });

    // Close / Cancel / Apply
    const close = () => {
      overlay.remove();
      if (onCancel) onCancel();
    };

    overlay.querySelector('#framing-modal-close')?.addEventListener('click', close);
    overlay.querySelector('#framing-modal-cancel')?.addEventListener('click', close);
    overlay.querySelector('#framing-modal-apply')?.addEventListener('click', () => {
      overlay.remove();
      if (onSave) {
        onSave({ focalX, focalY, zoom });
      }
    });
  }

  renderModalMarkup();
  document.body.appendChild(overlay);

  // Close on Escape
  const escHandler = e => {
    if (e.key === 'Escape') {
      overlay.remove();
      window.removeEventListener('keydown', escHandler);
      if (onCancel) onCancel();
    }
  };
  window.addEventListener('keydown', escHandler);
}

