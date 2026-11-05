# Antigravity: viewport, contrast and storefront repairs

## Objective and context

Implement and browser-verify the fixes below, not just an audit or screenshots. The owner reports oversized product images/videos requiring scrolling to see one complete media item, invisible text caused by color mismatches, and an unfinished homepage/hero. Repair the existing frontend with a consistent, professional AlphaZee presentation. Preserve the working commerce flows.

Read in order: `.agent/AGENTS.md`; this guide; `.context/temporary_media_preview.md`; relevant sections of `.context/frontend_design_implementation_guide.md` and `.context/brand_voice_and_story_guide.md`. Earlier PASS reports do not establish current visual quality.

Use `http://localhost:13000` and `/products/temporary-media-preview-20261105`. The owner authorized these temporary personal photos/video in development. They test portrait-media handling, not final commercial art direction. Preserve their originals and restore manifest. The preview is intentionally unavailable with a placeholder zero price; do not invent stock or enable purchases to test it. Real order testing belongs only in the separate lab at `http://127.0.0.1:13001`.

## Code map and starting observations

- `frontend/src/components/ProductPage.js`, `ProductGallery.js`, `Hero.js`, `Header.js`, `FeaturedProducts.js`, `ProductModal.js`.
- `frontend/src/styles/product-page.css`, `hero.css`, `header.css`, `grid.css`, `variables.css`, `reset.css`, `components.css`, `main.css`; `utils/productMedia.js`, `overlay.js`, `capabilities.js`.
- Product stage currently uses `aspect-ratio: 3 / 4` plus `min-height: 340px`. Images have a specific `max-height: none`, while `main.css` adds another gallery rule with `max-height: 60vh`. Inspect the computed cascade; changing image height alone may leave a huge parent.
- Hero styles contain blurred stills and a dark overlay. Inspect whether these obscure the actual assets. Check undefined/custom theme variables, inherited button text colors, specificity and import order. These are source observations, not browser-confirmed causes.

Keep the existing framework. React/libraries are permitted if a concrete need justifies them, but this repair does not require a framework/Next.js migration. Prefer scoped shared styles over accumulating overrides or `!important` patches.

## Work phase by phase

### F0 — Reproduce and prioritize

Before edits, open home and product in the real browser at **1366×768, 1440×900, 390×844 and 360×640**, plus mobile landscape. Record screenshot, viewport, scroll position and computed offending styles. List P0 usability failures and P1 polish issues. Check page overflow, header/announcement height, selected media bounds, controls, text/background colors and Console/Network errors. Save evidence under `.local/frontend-repairs/<run>/`.

### F1 — Product media must fit the screen

At normal zoom and scroll position zero, show the **entire selected image/video**, including navigation and video controls, inside a sensible viewport-sized gallery. This means one active slide fits; it does not mean displaying every uploaded file simultaneously.

- Budget height from the actual viewport minus header, breadcrumb, spacing and gallery navigation. Use responsive viewport units (`svh`/`dvh` with fallback) and bounded sizing; remove minimums/aspect rules that defeat the budget. Handle wrapping announcements and mobile browser bars.
- Give the stage an explicit bounded height; fill it with `object-fit: contain` media. Portrait, landscape and square assets must retain proportions. Accept intentional surrounding space. Do not crop product details, stretch media, downscale source files or hide overflow as a substitute for correct layout.
- Starting visual targets: desktop stage roughly 450–560px on a 768px-high laptop; mobile roughly 300–450px depending on available height. These are tuning ranges, not rigid minimums. Measure stage **and controls** against the usable viewport.
- Keep a balanced desktop media/purchase two-column layout. Mobile puts media before purchase details. Description, care, sizing and related items remain naturally scrollable below; do not disable page scrolling or trap the details in a nested scroll pane.
- Add compact image/poster thumbnails with a clear selected state and video indicator. Support the expected 8–9 photos plus one video without growing a tall thumbnail stack; use an accessible bounded strip/rail. Preserve arrows, swipe, keyboard, counters and enlargement.
- Gallery video starts on explicit interaction with visible controls; pause on slide/route/variant changes or hidden tabs. No autoplay sound. Lightbox supports Escape, focus restoration and usable zoom.

**Gate:** switch through every image and the video at all four baseline sizes. Verify complete media/control bounds without page-scrolling to uncover their bottom. For very short landscape screens and 200% zoom, allow natural scrolling/reflow rather than shrinking text/controls into unusability.

### F2 — Remove invisible text and unify controls

Audit title, price, options, quantity, stock messages, thumbnails, breadcrumbs, links, badges, form labels, placeholders, buttons and overlay controls. Check default, hover, selected, focus, disabled, loading and error states.

Use explicit semantic foreground/background pairs: dark text on light surfaces; inverse text only on genuinely dark surfaces. Avoid inherited white text on white buttons. Preserve Manrope/Newsreader and existing green/neutral tokens; make hierarchy, spacing and sizes consistent. Target contrast at least **4.5:1** for normal text, **3:1** for large text and meaningful control boundaries. Inspect computed styles and check rendered screenshots; opacity alone does not establish a disabled state. Maintain visible keyboard focus and approximately 44px touch targets.

**Gate:** all option labels and actions remain readable and identifiable with mouse, keyboard and touch. Check cart, checkout, admin and vendor surfaces for shared-style regressions.

### F3 — Homepage/hero and browsing polish

Make the hero a deliberate horizontal editorial section with legible headline, short honest copy and one primary shopping action. Balance height so shopping content is discoverable, especially on phones. Prevent text, navigation and media controls from overlapping.

Retain admin-managed sequencing: muted inline hero video, advance after playback, loop playlist, pause/resume, manual navigation, image timing and poster/error fallback. Respect reduced motion/data-saving preferences. Keep foreground media clear; use restrained/local contrast overlays rather than making every photo blurry or excessively dark. For portrait video in a horizontal area, use a considered media/text split or subtle background treatment instead of losing the subject to aggressive cropping. Do not promise that portrait temporary assets can fill a wide frame without compromise.

Check header/mobile menu, collection navigation, product grid/card ratios, hover front/back image, touch navigation, footer, loading/empty/error states and route Back/Forward. Avoid invented reviews, scarcity, discounts or delivery promises.

**Gate:** watch a complete hero cycle; exercise pause/manual controls, hover enter/leave and touch navigation. Inspect home at desktop/mobile, bright/dark slide backgrounds and reduced motion.

### F4 — Regression and handoff

After **each phase**: open the changed screen, inspect screenshots yourself, operate the controls, inspect Console/Network, fix failures and repeat affected checks before advancing. DOM existence, screenshot count or API success alone is not visual acceptance.

Final matrix adds 768×1024, 1920×1080, real desktop **200% browser zoom**, keyboard-only navigation, slow/failed media, narrow screens and mobile rotation. No horizontal page overflow, obscured CTA, sticky-bar overlap or layout jump. Test a long title and 9-photo/1-video **lab** fixture. Device emulation is not a physical-device pass; record unavailable checks honestly.

Run `npm.cmd test` and `npm.cmd run build` in `frontend`; do not weaken existing behavior tests. Refresh/rebuild the lab when testing changed source there. Smoke-check production deep-link serving if packaging changes. Preserve checkout isolation, accounts, prices, stock, media associations and existing backend contracts.

Write `.context/frontend_browser_repair_report.md`: phase status, changed files, before/after viewport measurements, screenshots, contrast checks, exact interactions/results, tests/builds, failures and remaining issues. Distinguish implemented, browser-verified and not tested. Update frontend progress with a link. Do not claim completion while the reported oversized media or invisible labels remain.
