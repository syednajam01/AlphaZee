import { escapeHtml as esc } from '../../utils/dom.js';

/**
 * Interactive Media Framing & Crop Studio Modal.
 * Supports:
 * 1) 16:9 Widescreen (Hero Banners): Full unclipped media with out-of-frame shading,
 *    and live storefront simulations for Desktop (16:9), Mobile Phone (16:9 in smartphone frame),
 *    and Side-by-Side comparison.
 * 2) 9:16 Vertical Portrait (Product & Collection Cards): Full unclipped media with 9:16
 *    viewfinder crop window, and live card simulations for Desktop and Mobile 2-column grids.
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
  let viewportMode = 'desktop'; // 'desktop' | 'mobile' | 'both'

  const isWidescreen = aspectRatio === '16:9';
  const targetRatio = isWidescreen ? 16 / 9 : 9 / 16;

  // Natural media aspect ratio (detected dynamically on media load)
  let mediaNaturalRatio = isWidescreen ? 16 / 9 : 9 / 16;
  let mediaLoaded = false;

  const overlay = document.createElement('div');
  overlay.id = 'media-framing-studio-modal';
  overlay.style.cssText = `
    position: fixed; inset: 0; z-index: 10000;
    background: rgba(6, 10, 8, 0.95);
    backdrop-filter: blur(12px);
    display: flex; align-items: center; justify-content: center;
    padding: 16px; box-sizing: border-box;
    overflow-y: auto; scrollbar-width: none;
  `;

  function renderModalMarkup() {
    overlay.innerHTML = `
      <div class="framing-modal-card" style="
        background: #111714; border: 1px solid #23322B; border-radius: 14px;
        width: 100%; max-width: 1240px; max-height: 96vh; display: flex; flex-direction: column;
        box-shadow: 0 32px 80px rgba(0,0,0,0.85); overflow: hidden; color: #FFF;
      ">
        <!-- Header -->
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 16px 24px; border-bottom: 1px solid #23322B; background: #151D19;">
          <div style="display: flex; align-items: center; gap: 12px;">
            <div style="width: 36px; height: 36px; border-radius: 9px; background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.3); display: flex; align-items: center; justify-content: center; color: #10B981;">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="22" y1="12" x2="18" y2="12"></line><line x1="6" y1="12" x2="2" y2="12"></line><line x1="12" y1="6" x2="12" y2="2"></line><line x1="12" y1="22" x2="12" y2="18"></line></svg>
            </div>
            <div>
              <div style="display: flex; align-items: center; gap: 8px;">
                <h3 style="margin: 0; font-size: 1.125rem; font-weight: 600; color: #FFFFFF;">${esc(title)}</h3>
                <span style="font-size: 0.6875rem; font-weight: 600; letter-spacing: 0.05em; padding: 3px 8px; border-radius: 4px; background: #1B2822; color: #38BDF8; border: 1px solid rgba(56, 189, 248, 0.25);">
                  ${isWidescreen ? '16:9 BANNER' : '9:16 CARD'}
                </span>
              </div>
              <p style="margin: 3px 0 0 0; font-size: 0.75rem; color: #9AA39E;">
                ${isWidescreen
                  ? 'See the full photo, adjust the 16:9 crop window, and inspect how much appears on Desktop vs Mobile.'
                  : 'Adjust vertical 9:16 card focus and inspect storefront card appearance.'}
              </p>
            </div>
          </div>
          <button type="button" class="btn btn-secondary btn-icon-only" id="framing-modal-close" title="Close editor" aria-label="Close editor" style="width: 34px; height: 34px;">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
          </button>
        </div>

        <!-- Body Grid -->
        <div style="flex: 1; overflow-y: auto; scrollbar-width: none; padding: 20px 24px; display: grid; grid-template-columns: minmax(360px, 1.1fr) minmax(360px, 1.2fr); gap: 24px;">
          
          <!-- LEFT COLUMN: Full Media Viewfinder with Out-of-Frame Shading -->
          <div style="display: flex; flex-direction: column; gap: 14px;">
            <div style="display: flex; align-items: center; justify-content: space-between;">
              <span style="font-size: 0.8125rem; font-weight: 600; color: #E5E6DE;">Full Media & Crop Viewfinder</span>
              <span id="framing-reticle-pill" style="font-size: 0.75rem; font-family: monospace; color: #F59E0B; background: rgba(245, 158, 11, 0.1); padding: 3px 8px; border-radius: 4px; border: 1px solid rgba(245, 158, 11, 0.3);">
                Focal: ${focalX}% X, ${focalY}% Y · ${zoom.toFixed(2)}x
              </span>
            </div>

            <!-- Canvas Viewfinder Wrapper -->
            <div id="viewfinder-outer-container" style="
              position: relative; width: 100%; height: 340px; background: #080C0A;
              border-radius: 10px; border: 1px solid #23322B; overflow: hidden;
              display: flex; align-items: center; justify-content: center; user-select: none;
            ">
              <!-- Natural Media Element -->
              <div id="media-viewport-box" style="position: relative; max-width: 100%; max-height: 100%; overflow: hidden; cursor: crosshair;">
                ${isVideo ? `
                  <video src="${esc(mediaUrl)}" id="viewfinder-media" muted playsinline autoplay loop style="
                    display: block; max-width: 100%; max-height: 340px; object-fit: contain; pointer-events: none;
                  "></video>
                ` : `
                  <img src="${esc(mediaUrl)}" id="viewfinder-media" alt="Original Media" style="
                    display: block; max-width: 100%; max-height: 340px; object-fit: contain; pointer-events: none;
                  ">
                `}

                <!-- Dark Shading Masks (Outside the Crop Window) -->
                <div id="mask-top" style="position: absolute; top: 0; left: 0; right: 0; background: rgba(0, 0, 0, 0.65); pointer-events: none; backdrop-filter: blur(1.5px);"></div>
                <div id="mask-bottom" style="position: absolute; bottom: 0; left: 0; right: 0; background: rgba(0, 0, 0, 0.65); pointer-events: none; backdrop-filter: blur(1.5px);"></div>
                <div id="mask-left" style="position: absolute; top: 0; bottom: 0; left: 0; background: rgba(0, 0, 0, 0.65); pointer-events: none; backdrop-filter: blur(1.5px);"></div>
                <div id="mask-right" style="position: absolute; top: 0; bottom: 0; right: 0; background: rgba(0, 0, 0, 0.65); pointer-events: none; backdrop-filter: blur(1.5px);"></div>

                <!-- Crop Window (Clear area inside the 16:9 banner or 9:16 card frame) -->
                <div id="crop-window-frame" style="
                  position: absolute; box-sizing: border-box;
                  border: 2px solid #38BDF8; box-shadow: 0 0 0 1px rgba(0,0,0,0.5), inset 0 0 16px rgba(56, 189, 248, 0.15);
                  pointer-events: none; transition: none;
                ">
                  <!-- Corner Crop Handles -->
                  <div style="position: absolute; top: -2px; left: -2px; width: 12px; height: 12px; border-top: 3px solid #FFF; border-left: 3px solid #FFF;"></div>
                  <div style="position: absolute; top: -2px; right: -2px; width: 12px; height: 12px; border-top: 3px solid #FFF; border-right: 3px solid #FFF;"></div>
                  <div style="position: absolute; bottom: -2px; left: -2px; width: 12px; height: 12px; border-bottom: 3px solid #FFF; border-left: 3px solid #FFF;"></div>
                  <div style="position: absolute; bottom: -2px; right: -2px; width: 12px; height: 12px; border-bottom: 3px solid #FFF; border-right: 3px solid #FFF;"></div>

                  <!-- Rule of Thirds Grid -->
                  <div style="position: absolute; left: 33.33%; top: 0; bottom: 0; width: 1px; background: rgba(255, 255, 255, 0.25);"></div>
                  <div style="position: absolute; left: 66.66%; top: 0; bottom: 0; width: 1px; background: rgba(255, 255, 255, 0.25);"></div>
                  <div style="position: absolute; top: 33.33%; left: 0; right: 0; height: 1px; background: rgba(255, 255, 255, 0.25);"></div>
                  <div style="position: absolute; top: 66.66%; left: 0; right: 0; height: 1px; background: rgba(255, 255, 255, 0.25);"></div>

                  <!-- Reticle Target (Focal Center) -->
                  <div id="canvas-reticle" style="
                    position: absolute; left: 50%; top: 50%; width: 26px; height: 26px;
                    border: 2px solid #F59E0B; border-radius: 50%; transform: translate(-50%, -50%);
                    box-shadow: 0 0 10px rgba(0,0,0,0.9), inset 0 0 6px rgba(245, 158, 11, 0.4);
                    display: flex; align-items: center; justify-content: center;
                  ">
                    <div style="width: 4px; height: 4px; border-radius: 50%; background: #F59E0B;"></div>
                    <div style="position: absolute; width: 34px; height: 1px; background: rgba(245, 158, 11, 0.8);"></div>
                    <div style="position: absolute; height: 34px; width: 1px; background: rgba(245, 158, 11, 0.8);"></div>
                  </div>

                  <!-- Crop Tag -->
                  <div style="position: absolute; top: 6px; left: 8px; background: rgba(14, 23, 19, 0.85); backdrop-filter: blur(4px); padding: 2px 6px; border-radius: 4px; font-size: 0.65rem; font-weight: 600; color: #38BDF8;">
                    ${isWidescreen ? 'IN-FRAME: 16:9 BANNER' : 'IN-FRAME: 9:16 CARD'}
                  </div>
                </div>
              </div>
            </div>

            <!-- Out-of-frame notice & instructions -->
            <div id="crop-stats-bar" style="display: flex; align-items: center; justify-content: space-between; font-size: 0.75rem; color: #9AA39E; background: #151D19; padding: 8px 12px; border-radius: 6px; border: 1px solid #23322B;">
              <span id="crop-status-text">Click or drag anywhere on the photo to shift the crop window.</span>
              <span style="color: #6EE7B7; font-weight: 500;">Shaded areas = cropped out</span>
            </div>

            <!-- Fine-Tuning Sliders -->
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; background: #151D19; padding: 14px; border-radius: 8px; border: 1px solid #23322B;">
              <div>
                <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #9AA39E; margin-bottom: 4px;">
                  <span>Horizontal Pan (X)</span>
                  <strong id="val-focal-x" style="color: #FFF;">${focalX}%</strong>
                </div>
                <input type="range" id="slider-focal-x" min="0" max="100" value="${focalX}" style="width: 100%; accent-color: #10B981; cursor: pointer;">
              </div>
              <div>
                <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #9AA39E; margin-bottom: 4px;">
                  <span>Vertical Pan (Y)</span>
                  <strong id="val-focal-y" style="color: #FFF;">${focalY}%</strong>
                </div>
                <input type="range" id="slider-focal-y" min="0" max="100" value="${focalY}" style="width: 100%; accent-color: #10B981; cursor: pointer;">
              </div>
              <div style="grid-column: 1 / -1;">
                <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #9AA39E; margin-bottom: 4px;">
                  <span>Crop Zoom Scale</span>
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

          <!-- RIGHT COLUMN: Storefront Simulation Across Desktop & Mobile -->
          <div style="display: flex; flex-direction: column; gap: 14px; border-left: 1px solid #23322B; padding-left: 20px;">
            <div style="display: flex; align-items: center; justify-content: space-between;">
              <span style="font-size: 0.8125rem; font-weight: 600; color: #E5E6DE;">Live Storefront Simulation</span>
              
              <!-- Viewport Selector: Desktop vs Mobile vs Side-by-Side -->
              <div style="display: flex; background: #151D19; padding: 2px; border-radius: 6px; border: 1px solid #23322B;">
                <button type="button" id="btn-view-desktop" class="btn ${viewportMode === 'desktop' ? 'btn-primary' : 'btn-secondary'}" style="padding: 4px 10px; font-size: 0.6875rem;">
                  Desktop 16:9
                </button>
                <button type="button" id="btn-view-mobile" class="btn ${viewportMode === 'mobile' ? 'btn-primary' : 'btn-secondary'}" style="padding: 4px 10px; font-size: 0.6875rem;">
                  Mobile (390px)
                </button>
                <button type="button" id="btn-view-both" class="btn ${viewportMode === 'both' ? 'btn-primary' : 'btn-secondary'}" style="padding: 4px 10px; font-size: 0.6875rem;">
                  Side-by-Side
                </button>
              </div>
            </div>

            <!-- Simulation Stage -->
            <div id="simulation-stage-box" style="
              display: flex; align-items: center; justify-content: center; min-height: 380px;
              background: #080C0A; border-radius: 10px; border: 1px solid #23322B; padding: 16px;
              overflow-x: auto; scrollbar-width: none;
            ">
              ${renderSimulationContent()}
            </div>

            <div style="font-size: 0.75rem; color: #9AA39E; line-height: 1.4;">
              ${isWidescreen
                ? '✓ <strong>Desktop & Mobile Parity:</strong> The banner runs edge-to-edge in 16:9 widescreen on both desktop and mobile. Check that overlay headings do not obscure important faces or graphics.'
                : '✓ <strong>Card Grid View:</strong> The 9:16 card frame shows the exact appearance shoppers will see in catalog grids.'}
            </div>
          </div>
        </div>

        <!-- Footer Actions -->
        <div style="display: flex; align-items: center; justify-content: flex-end; gap: 12px; padding: 14px 24px; border-top: 1px solid #23322B; background: #151D19;">
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

    wireStudioEvents();
  }

  function renderSimulationContent() {
    if (!isWidescreen) {
      // 9:16 Product Card Simulation
      return `
        <div style="display: flex; gap: 20px; align-items: flex-start; justify-content: center;">
          <div style="width: 220px; border-radius: 8px; overflow: hidden; background: #141A17; border: 1px solid #23322B; box-shadow: 0 10px 24px rgba(0,0,0,0.5);">
            <div style="position: relative; width: 100%; aspect-ratio: 9 / 16; overflow: hidden; background: #000;">
              ${isVideo ? `
                <video src="${esc(mediaUrl)}" class="sim-media-target" muted playsinline autoplay loop style="
                  width: 100%; height: 100%; object-fit: cover;
                  object-position: ${focalX}% ${focalY}%; transform: scale(${zoom});
                "></video>
              ` : `
                <img src="${esc(mediaUrl)}" class="sim-media-target" alt="Card Preview" style="
                  width: 100%; height: 100%; object-fit: cover;
                  object-position: ${focalX}% ${focalY}%; transform: scale(${zoom});
                ">
              `}
            </div>
            <div style="padding: 12px;">
              <span style="font-size: 0.65rem; color: #10B981; font-weight: 600; text-transform: uppercase;">The Collection</span>
              <h4 style="margin: 4px 0 2px 0; font-size: 0.875rem; color: #FFF; font-weight: 500;">${esc(cardData?.title || 'Silk Tunic')}</h4>
              <p style="margin: 0; font-size: 0.75rem; color: #9AA39E;">PKR 4,200</p>
            </div>
          </div>
        </div>
      `;
    }

    // 16:9 Banner Storefront Simulation
    const showDesktop = viewportMode === 'desktop' || viewportMode === 'both';
    const showMobile = viewportMode === 'mobile' || viewportMode === 'both';

    return `
      <div style="display: flex; gap: 24px; align-items: center; justify-content: center; width: 100%; flex-wrap: ${viewportMode === 'both' ? 'nowrap' : 'wrap'};">
        ${showDesktop ? `
          <!-- Desktop Mockup (16:9 Widescreen) -->
          <div style="flex: ${viewportMode === 'both' ? '1.4' : '1'}; max-width: ${viewportMode === 'both' ? '460px' : '580px'}; display: flex; flex-direction: column; gap: 6px;">
            <div style="display: flex; align-items: center; justify-content: space-between; font-size: 0.6875rem; color: #9AA39E;">
              <span>Desktop Display (16:9 Full Screen)</span>
              <span style="color: #38BDF8;">1920 × 1080</span>
            </div>
            <!-- Browser Mock Window -->
            <div style="border-radius: 8px; overflow: hidden; background: #0D1310; border: 1px solid #23322B; box-shadow: 0 16px 36px rgba(0,0,0,0.6);">
              <!-- Browser Header -->
              <div style="background: #18221D; padding: 6px 12px; display: flex; align-items: center; gap: 6px; border-bottom: 1px solid #23322B;">
                <div style="width: 8px; height: 8px; border-radius: 50%; background: #EF4444;"></div>
                <div style="width: 8px; height: 8px; border-radius: 50%; background: #F59E0B;"></div>
                <div style="width: 8px; height: 8px; border-radius: 50%; background: #10B981;"></div>
                <div style="margin-left: 8px; background: #0D1310; padding: 2px 10px; border-radius: 4px; font-size: 0.625rem; color: #9AA39E; font-family: monospace;">alphazee.tech</div>
              </div>
              <!-- Simulated Storefront Banner -->
              <div style="position: relative; width: 100%; aspect-ratio: 16 / 9; overflow: hidden; background: #000;">
                ${isVideo ? `
                  <video src="${esc(mediaUrl)}" class="sim-media-target" muted playsinline autoplay loop style="
                    width: 100%; height: 100%; object-fit: cover;
                    object-position: ${focalX}% ${focalY}%; transform: scale(${zoom});
                  "></video>
                ` : `
                  <img src="${esc(mediaUrl)}" class="sim-media-target" alt="Desktop Banner" style="
                    width: 100%; height: 100%; object-fit: cover;
                    object-position: ${focalX}% ${focalY}%; transform: scale(${zoom});
                  ">
                `}
                <!-- Storefront Scrim & Typography -->
                <div style="position: absolute; inset: 0; background: linear-gradient(90deg, rgba(8, 14, 11, 0.88) 0%, rgba(8, 14, 11, 0.60) 45%, rgba(8, 14, 11, 0.20) 75%, rgba(8, 14, 11, 0.10) 100%); pointer-events: none;"></div>
                <div style="position: absolute; inset: 0; padding: 18px 22px; display: flex; flex-direction: column; justify-content: center; z-index: 2; pointer-events: none;">
                  <span style="font-size: 0.625rem; font-weight: 600; color: #10B981; letter-spacing: 0.05em; margin-bottom: 4px;">SELECTED BY ALPHAZEE</span>
                  <h3 style="margin: 0 0 4px 0; font-size: 1.05rem; font-weight: 600; color: #FFF; line-height: 1.2;">${esc(bannerData?.title || 'Featured Drop')}</h3>
                  <p style="margin: 0 0 10px 0; font-size: 0.6875rem; color: #D1D5DB; line-height: 1.3;">${esc(bannerData?.headline || bannerData?.benefit || 'Our 1st Exclusive Drop. Considered selection.')}</p>
                  <div><span style="display: inline-block; padding: 4px 10px; background: #145C44; color: #FFF; font-size: 0.625rem; font-weight: 500; border-radius: 4px;">Shop collection</span></div>
                </div>
              </div>
            </div>
          </div>
        ` : ''}

        ${showMobile ? `
          <!-- Mobile Phone Mockup (True 16:9 Banner on 390px Viewport) -->
          <div style="flex: ${viewportMode === 'both' ? '0 0 250px' : '0 0 280px'}; display: flex; flex-direction: column; gap: 6px;">
            <div style="display: flex; align-items: center; justify-content: space-between; font-size: 0.6875rem; color: #9AA39E;">
              <span>Mobile Phone (390px Viewport)</span>
              <span style="color: #10B981;">16:9 True Widescreen</span>
            </div>
            <!-- Smartphone Shell -->
            <div style="
              width: 100%; border-radius: 24px; padding: 10px 8px 14px 8px;
              background: #0D1310; border: 2.5px solid #2A3831; box-shadow: 0 16px 36px rgba(0,0,0,0.6);
              display: flex; flex-direction: column; gap: 8px;
            ">
              <!-- Phone Dynamic Island / Speaker Notch -->
              <div style="display: flex; align-items: center; justify-content: center;">
                <div style="width: 50px; height: 10px; border-radius: 5px; background: #1C2621;"></div>
              </div>

              <!-- Phone Floating Navbar Island -->
              <div style="
                margin: 0 4px; padding: 4px 10px; border-radius: 999px; background: rgba(255, 254, 250, 0.9);
                display: flex; align-items: center; justify-content: space-between; box-shadow: 0 2px 6px rgba(0,0,0,0.15);
              ">
                <span style="font-size: 0.6875rem; font-weight: 700; color: #172033; font-family: serif;">AlphaZee</span>
                <div style="display: flex; gap: 6px; color: #172033;">
                  <div style="width: 10px; height: 10px; border-radius: 2px; border: 1px solid currentColor;"></div>
                  <div style="width: 10px; height: 10px; border-radius: 2px; border: 1px solid currentColor;"></div>
                </div>
              </div>

              <!-- True 16:9 Mobile Storefront Banner -->
              <div style="position: relative; width: 100%; aspect-ratio: 16 / 9; border-radius: 6px; overflow: hidden; background: #000;">
                ${isVideo ? `
                  <video src="${esc(mediaUrl)}" class="sim-media-target" muted playsinline autoplay loop style="
                    width: 100%; height: 100%; object-fit: cover;
                    object-position: ${focalX}% ${focalY}%; transform: scale(${zoom});
                  "></video>
                ` : `
                  <img src="${esc(mediaUrl)}" class="sim-media-target" alt="Mobile Banner" style="
                    width: 100%; height: 100%; object-fit: cover;
                    object-position: ${focalX}% ${focalY}%; transform: scale(${zoom});
                  ">
                `}
                <!-- Mobile Gradient Scrim & Mobile Typography -->
                <div style="position: absolute; inset: 0; background: linear-gradient(180deg, rgba(8, 14, 11, 0.20) 0%, rgba(8, 14, 11, 0.55) 45%, rgba(8, 14, 11, 0.85) 100%); pointer-events: none;"></div>
                <div style="position: absolute; inset: 0; padding: 10px 12px; display: flex; flex-direction: column; justify-content: flex-end; z-index: 2; pointer-events: none;">
                  <span style="font-size: 0.55rem; font-weight: 600; color: #10B981; letter-spacing: 0.05em; margin-bottom: 2px;">SELECTED BY ALPHAZEE</span>
                  <h4 style="margin: 0 0 2px 0; font-size: 0.75rem; font-weight: 600; color: #FFF; line-height: 1.1;">${esc(bannerData?.title || 'Featured Drop')}</h4>
                  <p style="margin: 0 0 6px 0; font-size: 0.55rem; color: #D1D5DB; line-height: 1.2;">${esc(bannerData?.headline || bannerData?.benefit || 'Considered selection.')}</p>
                </div>
              </div>

              <!-- Bottom Content Preview Hint -->
              <div style="padding: 4px 6px; display: flex; flex-direction: column; gap: 4px;">
                <div style="height: 6px; width: 45%; background: rgba(255,255,255,0.2); border-radius: 3px;"></div>
                <div style="height: 4px; width: 70%; background: rgba(255,255,255,0.1); border-radius: 2px;"></div>
              </div>
            </div>
          </div>
        ` : ''}
      </div>
    `;
  }

  function wireStudioEvents() {
    const mediaEl = overlay.querySelector('#viewfinder-media');
    const viewportBox = overlay.querySelector('#media-viewport-box');
    const cropWindow = overlay.querySelector('#crop-window-frame');
    const maskTop = overlay.querySelector('#mask-top');
    const maskBottom = overlay.querySelector('#mask-bottom');
    const maskLeft = overlay.querySelector('#mask-left');
    const maskRight = overlay.querySelector('#mask-right');
    const reticle = overlay.querySelector('#canvas-reticle');
    const reticlePill = overlay.querySelector('#framing-reticle-pill');
    const cropStatusText = overlay.querySelector('#crop-status-text');

    const sliderX = overlay.querySelector('#slider-focal-x');
    const sliderY = overlay.querySelector('#slider-focal-y');
    const sliderZoom = overlay.querySelector('#slider-zoom');
    const valX = overlay.querySelector('#val-focal-x');
    const valY = overlay.querySelector('#val-focal-y');
    const valZoom = overlay.querySelector('#val-zoom');

    function updateCropViewfinderGeometry() {
      if (!viewportBox || !cropWindow) return;

      const boxRect = viewportBox.getBoundingClientRect();
      const W = boxRect.width;
      const H = boxRect.height;
      if (!W || !H) return;

      const mediaRatio = W / H;
      let cropW, cropH;

      if (mediaRatio > targetRatio) {
        // Media is wider than target frame (height-constrained)
        cropH = H / zoom;
        cropW = cropH * targetRatio;
      } else {
        // Media is taller than target frame (width-constrained)
        cropW = W / zoom;
        cropH = cropW / targetRatio;
      }

      // Bound crop frame within viewport box
      cropW = Math.min(W, cropW);
      cropH = Math.min(H, cropH);

      const maxLeft = W - cropW;
      const maxTop = H - cropH;

      const left = maxLeft * (focalX / 100);
      const top = maxTop * (focalY / 100);

      // Position crop window frame
      cropWindow.style.width = `${Math.round(cropW)}px`;
      cropWindow.style.height = `${Math.round(cropH)}px`;
      cropWindow.style.left = `${Math.round(left)}px`;
      cropWindow.style.top = `${Math.round(top)}px`;

      // Update surrounding 4 dark masks
      if (maskTop) {
        maskTop.style.height = `${Math.max(0, Math.round(top))}px`;
      }
      if (maskBottom) {
        maskBottom.style.height = `${Math.max(0, Math.round(H - (top + cropH)))}px`;
      }
      if (maskLeft) {
        maskLeft.style.top = `${Math.round(top)}px`;
        maskLeft.style.height = `${Math.round(cropH)}px`;
        maskLeft.style.width = `${Math.max(0, Math.round(left))}px`;
      }
      if (maskRight) {
        maskRight.style.top = `${Math.round(top)}px`;
        maskRight.style.height = `${Math.round(cropH)}px`;
        maskRight.style.width = `${Math.max(0, Math.round(W - (left + cropW)))}px`;
      }

      // Update text pills and sliders
      if (reticlePill) {
        reticlePill.textContent = `Focal: ${focalX}% X, ${focalY}% Y · ${zoom.toFixed(2)}x`;
      }
      if (valX) valX.textContent = `${focalX}%`;
      if (valY) valY.textContent = `${focalY}%`;
      if (valZoom) valZoom.textContent = `${zoom.toFixed(2)}x`;

      if (sliderX && Number(sliderX.value) !== focalX) sliderX.value = focalX;
      if (sliderY && Number(sliderY.value) !== focalY) sliderY.value = focalY;
      if (sliderZoom && Number(sliderZoom.value) !== zoom) sliderZoom.value = zoom;

      // Calculate percentage of media visible in frame vs out-of-frame
      const visibleAreaPct = Math.round(((cropW * cropH) / (W * H)) * 100);
      const croppedOutPct = 100 - visibleAreaPct;
      if (cropStatusText) {
        cropStatusText.innerHTML = `<strong>${visibleAreaPct}%</strong> in frame · <span style="color: #F87171;">${croppedOutPct}%</span> cropped out in shaded areas.`;
      }

      // Synchronize Live Simulation targets
      overlay.querySelectorAll('.sim-media-target').forEach(sim => {
        sim.style.objectPosition = `${focalX}% ${focalY}%`;
        sim.style.transform = `scale(${zoom})`;
      });
    }

    // Media element natural dimension listener
    if (mediaEl) {
      const onMediaReady = () => {
        mediaLoaded = true;
        const nw = mediaEl.naturalWidth || mediaEl.videoWidth || 1920;
        const nh = mediaEl.naturalHeight || mediaEl.videoHeight || 1080;
        mediaNaturalRatio = nw / nh;
        updateCropViewfinderGeometry();
      };
      if (mediaEl.tagName === 'VIDEO') {
        if (mediaEl.readyState >= 1) onMediaReady();
        else mediaEl.addEventListener('loadedmetadata', onMediaReady);
      } else {
        if (mediaEl.complete) onMediaReady();
        else mediaEl.addEventListener('load', onMediaReady);
      }
    }

    // Canvas click & drag interaction
    let isDragging = false;
    function handlePointerCoords(e) {
      if (!viewportBox) return;
      const rect = viewportBox.getBoundingClientRect();
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      const clientY = e.touches ? e.touches[0].clientY : e.clientY;
      const xPct = Math.round(((clientX - rect.left) / rect.width) * 100);
      const yPct = Math.round(((clientY - rect.top) / rect.height) * 100);
      focalX = Math.max(0, Math.min(100, xPct));
      focalY = Math.max(0, Math.min(100, yPct));
      updateCropViewfinderGeometry();
    }

    viewportBox?.addEventListener('mousedown', e => {
      isDragging = true;
      handlePointerCoords(e);
    });
    window.addEventListener('mousemove', e => {
      if (isDragging) handlePointerCoords(e);
    });
    window.addEventListener('mouseup', () => {
      isDragging = false;
    });

    // Touch support for mobile admin
    viewportBox?.addEventListener('touchstart', e => {
      isDragging = true;
      handlePointerCoords(e);
    }, { passive: true });
    window.addEventListener('touchmove', e => {
      if (isDragging) handlePointerCoords(e);
    }, { passive: true });
    window.addEventListener('touchend', () => {
      isDragging = false;
    });

    // Sliders
    sliderX?.addEventListener('input', e => {
      focalX = Number(e.target.value);
      updateCropViewfinderGeometry();
    });
    sliderY?.addEventListener('input', e => {
      focalY = Number(e.target.value);
      updateCropViewfinderGeometry();
    });
    sliderZoom?.addEventListener('input', e => {
      zoom = Number(e.target.value);
      updateCropViewfinderGeometry();
    });

    // Presets
    overlay.querySelectorAll('.btn-preset').forEach(btn => {
      btn.addEventListener('click', () => {
        focalX = Number(btn.dataset.fx);
        focalY = Number(btn.dataset.fy);
        zoom = Number(btn.dataset.zm || 1.0);
        updateCropViewfinderGeometry();
      });
    });

    // Viewport Mode Switchers
    overlay.querySelector('#btn-view-desktop')?.addEventListener('click', () => {
      viewportMode = 'desktop';
      const stage = overlay.querySelector('#simulation-stage-box');
      if (stage) stage.innerHTML = renderSimulationContent();
      updateCropViewfinderGeometry();
      renderModalMarkup();
    });
    overlay.querySelector('#btn-view-mobile')?.addEventListener('click', () => {
      viewportMode = 'mobile';
      renderModalMarkup();
    });
    overlay.querySelector('#btn-view-both')?.addEventListener('click', () => {
      viewportMode = 'both';
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

    // Initial positioning
    setTimeout(updateCropViewfinderGeometry, 50);
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
