# AlphaZee Storefront Redesign: Progress & Verification Register

Tracking implementation of [.context/frontend_design_implementation_guide.md](file:///f:/AlphaZee/.context/frontend_design_implementation_guide.md) across phases U0–U5.

## Phase Register

| Phase | Description | Status | Evidence Location | Gaps / Notes |
|---|---|---|---|---|
| **U0** | Baseline capture, visual tokens (`variables.css`, `components.css`), shared controls & component reference | **Completed** | `.local/frontend-redesign/run_u0_baseline/` | Verified tokens, typography (Manrope/Newsreader), controls, 108 tests pass, build pass |
| **U1** | Direct `/products/:slug` routing, page shell, history/query handling, deep link fallbacks | **Completed** | `.local/frontend-redesign/run_u1_routing/` | All 6 browser checks passed, deep links, reload, 404, query variants, mobile bar verified |
| **U2** | Header/home layout, 3:4 catalog cards, image hover crossfades, filters & full-result set sort | **Completed** | `.local/frontend-redesign/run_u2_catalog/` | All 7 automated browser checks passed: sticky white header, Newsreader hero, 3:4 aspect ratio, 4/3/2 col responsive grid, immediate touch tap, full-dataset sorting, single-row category tabs |
| **U3** | Product detail page layout (58/42 desktop split, mobile stack & sticky purchase bar), gallery swipe/zoom/video | **Completed** | `.local/frontend-redesign/run_u3_gallery/` | All 7 automated browser checks passed: 58/42 split, prev/next controls, counter, lightbox zoom, keyboard arrows, live variant price/stock, mobile bar obstruction safety |
| **U4** | Cart drawer & Checkout view refinements, accessibility (dialog focus trap, Escape, Tab wrap), validation & honest state | In Progress | `.local/frontend-redesign/run_u4_checkout/` | Refining Cart Drawer, lab COD & bank journeys, focus management, and validation |
| **U5** | Breakpoint matrix (360/390/768/1280/1440), 200% browser zoom, reduced motion, slow network & admin console smoke check | Not Started | — | Final polish |

---

## Architecture & Migration Record (2026-10-19)

Per owner instruction and `.agent/AGENTS.md` framework flexibility, evaluated migrating the storefront to **Next.js with React** for SEO, AI agent discoverability, initial server-rendered HTML, canonical hygiene, and dynamic sitemaps.
- **Detailed Tradeoff Report**: [migration_tradeoffs.md](file:///C:/Users/SyedNajam%27s%20PC/.gemini/antigravity-ide/brain/ca17e23f-7699-47ff-83c4-deb583790c47/migration_tradeoffs.md)
- **Key Invariants Preserved**:
  1. FastAPI backend (`/api/v1`), PostgreSQL databases, and integer-paisas logic remain untouched.
  2. Authoritative checkout validation: SSR cached prices/availability never override backend checkout verification.
  3. Strict checkout isolation: Checkout stays open strictly in the isolated local lab (`127.0.0.1:13001`), closed in dev (`13000`) and production.
  4. Owner dashboard `/admin` remains fully functional with existing session, CSRF, and Origin protections.

---

## Phase Details

### Phase U0: Baseline Capture & Foundation Tokens
- **Scope**:
  - Captured existing desktop (1440px) and mobile (390px) screenshots for header, hero, catalog, and drawers across dev (13000) and lab (13001).
  - Centralized editorial commerce tokens in `frontend/src/styles/variables.css` matching design brief:
    - Page ivory `#F7F7F2`, surface `#FFFFFF`, text `#171717`, secondary `#595959`
    - Primary green `#145C44` (hover `#0E4231`), pale green `#E8F2EE`, borders `#DEDED7`
    - Error `#B42318` (`#FEF3F2`), success `#145C44` (`#E8F2EE`)
    - Typography: Manrope UI/body + Newsreader headings, font-display swap, system/Georgia fallbacks
    - Spacing scale: 4, 8, 12, 16, 24, 32, 48, 64, 96px
    - Container max 1280px; gutters 16px mobile, 24px tablet, 40px desktop
    - Standard 48px controls, at least 44x44px touch targets, 8px control radius, 12px dialog radius, 4px media radius
    - Tabular numeric price styling (`.price-tabular`)
    - Motion tokens: 150ms/180ms/220ms, prefers-reduced-motion reset
  - Standardized form controls (`.form-input`, `.form-select`, `.form-textarea`, `.form-label`, `.form-error`)
- **Changed Files**:
  - `frontend/src/styles/variables.css`
  - `frontend/src/styles/components.css`
  - `frontend/index.html`
  - `.local/frontend-redesign/browser_util.py`
- **Checks Actually Run**:
  - Unit/regression tests: `npm.cmd test` (108 passed, 0 failures).
  - Production build: `npm.cmd run build` (successful, 34 modules transformed in 6.97s).
  - CDP headless browser execution on `http://localhost:13000` and `http://127.0.0.1:13001` via `RedesignBrowser`.
- **Evidence Screenshots**:
  - Baseline before: `.local/frontend-redesign/run_u0_baseline/u0_desktop_home_before.png`
  - Baseline before mobile: `.local/frontend-redesign/run_u0_baseline/u0_mobile_home_before.png`
  - Baseline before cart: `.local/frontend-redesign/run_u0_baseline/u0_desktop_cart_drawer_before.png`
  - Lab before catalog: `.local/frontend-redesign/run_u0_baseline/u0_lab_desktop_catalog_before.png`
  - Tokens verified desktop: `.local/frontend-redesign/run_u0_baseline/u0_desktop_home_after_tokens.png`
  - Tokens verified mobile cart: `.local/frontend-redesign/run_u0_baseline/u0_mobile_cart_after_tokens.png`
  - JSON evidence: `.local/frontend-redesign/run_u0_baseline/u0_verification.json`
- **Defects & Fixes**:
  - Eliminated harsh button shadow glow; updated button styles to clean solid green.
  - Adjusted badge styling from pill to clean 4px radius.

### Phase U1: Product Routing & Page Shell
- **Scope**:
  - Implemented client-side SPA routing in `frontend/src/app.js` with direct `/products/:slug` pattern, query parameter variant support (`?variant=<id>`), `popstate` Back/Forward listener, and delegated internal link navigation.
  - Created editorial product page layout in `frontend/src/components/ProductPage.js` and `frontend/src/styles/product-page.css`:
    - Desktop 58% gallery / 42% sticky details split; mobile stacked column.
    - Semantic breadcrumbs (`Home / [Collection] / [Product]`).
    - Color and size option chips with radio roles and selection states.
    - 48px Quantity stepper (+ / -).
    - Authentic sizing guide table, material & garment care block, nationwide delivery details.
    - Mobile sticky purchase bar (`#mobile-purchase-bar`) with intersection observer.
    - Honest 404/archived product unavailable screen (`Piece Unavailable`) with action button to return to available collection.
    - Document title and canonical URL dynamically updated on load.
  - Updated `FeaturedProducts.js` to render genuine `<a>` anchors on product images and titles pointing to `/products/:slug`.
  - Added unit test suite `frontend/tests/product-routing.test.js` covering initial render, 404 handling, variant query selection, fallback on invalid variant, and cart addition.
- **Changed Files**:
  - `frontend/src/styles/product-page.css`
  - `frontend/src/styles/main.css`
  - `frontend/src/components/ProductPage.js`
  - `frontend/src/components/FeaturedProducts.js`
  - `frontend/src/app.js`
  - `frontend/tests/product-routing.test.js`
  - `scratch/verify_u1_gate.py`
  - `.local/frontend-redesign/browser_util.py`
- **Checks Actually Run**:
  - Frontend unit tests: `npm.cmd test` (113 passed, 0 failures).
  - Production build: `npm.cmd run build` (successful, 35 modules in 2.6s).
  - Browser CDP automated gate on `http://127.0.0.1:13001`:
    1. Direct URL navigation to `http://127.0.0.1:13001/products/sample-m8-0d535c70` -> PASS (Title: "SAMPLE M8 0d535c70 — AlphaZee", Price: "PKR 123.45", CTA: present).
    2. Deep link page reload -> PASS.
    3. Invalid variant query fallback (`?variant=invalid_99999`) -> PASS.
    4. Invalid slug unavailable screen (`/products/nonexistent-archived-piece-1234`) -> PASS (Displays "Piece Unavailable" and return button).
    5. Back / Forward SPA history -> PASS (Home -> Product -> Back to Home -> Forward to Product).
    6. Mobile product shell (390x844) -> PASS (Title visible, sticky purchase bar present).
- **Evidence Screenshots**:
  - Direct URL: `.local/frontend-redesign/run_u1_routing/u1_direct_url_product.png`
  - Reload: `.local/frontend-redesign/run_u1_routing/u1_reload_product.png`
  - Invalid variant fallback: `.local/frontend-redesign/run_u1_routing/u1_invalid_variant_fallback.png`
  - Invalid slug / 404: `.local/frontend-redesign/run_u1_routing/u1_invalid_slug_unavailable.png`
  - History forward: `.local/frontend-redesign/run_u1_routing/u1_history_forward_product.png`
  - Mobile product page: `.local/frontend-redesign/run_u1_routing/u1_mobile_product_page.png`
  - JSON evidence: `.local/frontend-redesign/run_u1_routing/u1_verification.json`
- **Defects & Fixes**:
  - Visual inspection revealed transparent header text overlapping product breadcrumbs on deep links without scroll. Planned fix in U2: header surface background and proper content top padding.
  - Initial click handler on product card media links called `e.preventDefault()` for modal; fixed to allow direct pushState navigation to `/products/:slug` while keeping `.product-card-btn` for quick view.
- **Next Step**:
  - Proceed to Phase U2: Header, Editorial Hero, and Responsive 3:4 Catalog Grid with full-dataset filtering, sorting, and image hover crossfade.

### Phase U2: Header, Editorial Hero & Responsive 3:4 Catalog Grid
- **Scope**:
  - **Header & Logo Contrast**: Updated `header.css` and `logo.css` to `position: sticky; top: 0;`, solid white surface (`#FFFFFF`), high-contrast dark text (`#171717`), and un-inverted logo filter (`filter: none`). Eliminates contrast clash and breadcrumb overlap on deep links.
  - **Editorial Hero**: Updated `Hero.js` and `hero.css` with Newsreader serif headings, calm layout, and eliminated auto-rotation per brief ("no automatic hero carousel"). Streamlined height (55–65vh) ensuring catalog items are immediately reachable.
  - **3:4 Aspect Ratio Catalog Frames**: Enforced exact 3:4 aspect ratio (`ratio: 0.75`, e.g. 280x373px) with `object-fit: contain` and clean borders, preventing layout shifts and distortion.
  - **Responsive Catalog Grid**: 4 columns on desktop (>=1024px), 3 columns on tablet (>=640px), 2 columns on mobile (<=640px), 1 column on extra narrow (<350px).
  - **Immediate Touch Navigation**: Direct pushState navigation on image/title click without requiring hover activation.
  - **Single-Row Horizontal Category Tabs**: Updated `grid.css` with `flex-wrap: nowrap; overflow-x: auto;` so 28 collection pills stay on a sleek single scrollable row instead of wrapping into 28 vertical rows.
  - **Full-Dataset Sorting & Filter Memory**: Added `#catalog-sort` (Featured, Price: Low to High, Price: High to Low, Name: A to Z) applying across the full product catalog, with `sessionStorage` filter/sort preservation.
  - **Image Hover Swap & Neutral Fallback**: 180ms hover transition for fine pointers (`@media (hover: hover) and (pointer: fine)`), with neutral fallback when no secondary image exists.
- **Changed Files**:
  - `frontend/src/styles/header.css`
  - `frontend/src/styles/logo.css`
  - `frontend/src/styles/hero.css`
  - `frontend/src/styles/grid.css`
  - `frontend/src/components/Hero.js`
  - `frontend/src/components/FeaturedProducts.js`
  - `scratch/verify_u2_gate.py`
- **Checks Actually Run**:
  - Frontend unit tests: `npm.cmd test` (113 passed, 0 failures).
  - Production build: `npm.cmd run build` (successful, 35 modules in 3.15s).
  - Web container build & restart: `docker compose -f compose.checkout-lab.yml up --build -d web`.
  - Browser CDP automated gate on `http://127.0.0.1:13001` (7/7 checks passed):
    1. Header contrast & Editorial Hero -> PASS.
    2. 3:4 aspect ratio crops on catalog cards -> PASS (exact 0.75 ratio).
    3. Responsive grid breakpoints (4 desktop / 3 tablet / 2 phone) -> PASS.
    4. Mobile touch navigation immediate tap -> PASS.
    5. Full-dataset sorting -> PASS.
    6. Category tabs & filter switching -> PASS.
    7. Secondary image hover swap & neutral fallback -> PASS.
- **Evidence Screenshots**:
  - Header & Editorial Hero: `.local/frontend-redesign/run_u2_catalog/u2_desktop_header_and_hero.png`
  - Catalog Grid (3:4 ratio): `.local/frontend-redesign/run_u2_catalog/u2_desktop_catalog_grid_3_4.png`
  - Tablet 3-column Grid: `.local/frontend-redesign/run_u2_catalog/u2_tablet_3col.png`
  - Mobile 2-column Grid: `.local/frontend-redesign/run_u2_catalog/u2_mobile_2col.png`
  - Sorted Price Ascending: `.local/frontend-redesign/run_u2_catalog/u2_sorted_price_asc.png`
  - Filtered Category: `.local/frontend-redesign/run_u2_catalog/u2_filtered_category.png`
  - JSON evidence: `.local/frontend-redesign/run_u2_catalog/u2_verification.json`
- **Next Step**:
  - Proceed to Phase U3: Full product gallery, details, variant selection, and purchase controls.

### Phase U3: Product Detail Page Layout, Gallery & Purchase Controls
- **Scope**:
  - **Desktop 58% Gallery / 42% Details Split**: Implemented responsive editorial product grid with sticky purchase summary on desktop (`position: sticky; top: calc(var(--header-height) + 24px)`), breadcrumbs (`Home / [Collection] / [Product]`), Newsreader/Manrope typography, tabular price, and stock badge.
  - **ProductGallery Upgrades**:
    - Floating round 44px navigation controls (`#gallery-prev-btn`, `#gallery-next-btn`) with subtle backdrop blur, hover states, and disabled handling for single-media pieces.
    - Slide counter badge (`.gallery-counter`) showing active index and total (`1 / N`).
    - Touch gesture swipe navigation (`touchstart`, `touchmove`, `touchend`) with 40px delta threshold and dominant horizontal intent preservation.
    - Keyboard arrow navigation (`ArrowRight`, `ArrowLeft`, `Home`, `End`) on stage carousel.
    - Lightbox image enlargement zoom modal (`#gallery-lightbox`) with dark blur backdrop, full-resolution unconstrained image, close button, focus trap, and Escape key dismiss.
    - Video lifecycle management: `playsinline`, `preload="none"`, `controls`, and automatic pause on slide change, modal/lightbox open, route change, and `visibilitychange` (tab hide).
    - Neutral fallback placeholder when product has no media.
  - **Live Variant Selection & Invariants**:
    - Interactive size and color chips with radio accessibility roles (`role="radiogroup"`, `role="radio"`, `aria-checked`).
    - Dynamic variant matching updating live price (`#product-detail-price`), stock badge ("In Stock" vs "Currently Unavailable"), and Add to Shopping Bag CTA state without page reloads.
    - Dynamic URL query parameter synchronization (`?variant=<id>`) via `history.replaceState`.
    - Variant-specific image selection upon option chip click.
    - 48px Quantity stepper (- / +) with numeric boundaries (1 to 99).
  - **Mobile Sticky Purchase Bar & Obstruction Safety**:
    - `#mobile-purchase-bar` slides into view only when the inline `#btn-add-to-cart` scrolls past the top of the viewport.
    - Reflects selected variant title, price, and active Add to Bag button.
    - Obstruction safety: automatically suppressed (`display: none !important`) whenever an overlay, cart drawer, or lightbox is open (`body.has-overlay`, `body.lightbox-open`), or when virtual keyboard inputs (`input`, `textarea`, `select`) receive focus (`.is-suppressed`).
  - **Authentic Editorial Accordions & Related Pieces**:
    - Material & Garment Care details (100% combed cotton 240 GSM, preshrunk, wash care).
    - Sizing Guide measurement table (Chest, Length, Shoulder across S, M, L, XL).
    - Nationwide Delivery & Returns (24–48h dispatch from Karachi hub, 3–5 days transit, COD and bank transfer, 7-day inspection policy).
    - Curated Related Pieces section rendering 3:4 aspect ratio cards.
- **Changed Files**:
  - `frontend/src/components/ProductGallery.js`
  - `frontend/src/components/ProductPage.js`
  - `frontend/src/utils/overlay.js`
  - `frontend/src/styles/product-page.css`
  - `frontend/tests/product-gallery-u3.test.js`
  - `scratch/verify_u3_gate.py`
  - `.local/frontend-redesign/browser_util.py`
- **Checks Actually Run**:
  - Frontend unit tests: `npm.cmd test` (118 passed, 0 failures; 5 new U3 tests for gallery controls, keyboard, zoom, touch, and video lifecycle).
  - Production build: `npm.cmd run build` (successful, 35 modules in 2.77s).
  - Web container build & restart: `docker compose -f compose.checkout-lab.yml up --build -d web`.
  - Browser CDP automated gate on `http://127.0.0.1:13001` (7/7 checks passed):
    1. Desktop 58/42 Layout & Content -> PASS (58% gallery / 42% details, breadcrumbs, accordions, size table).
    2. Gallery Controls & Counter -> PASS (prev/next buttons, slide counter pill `1 / 2` to `2 / 2`).
    3. Image Lightbox Zoom & Dismiss -> PASS (opens `#gallery-lightbox`, locks body scroll, dismisses on Escape).
    4. Keyboard Navigation on Stage -> PASS (stage focused, ArrowRight / ArrowLeft cycle slides).
    5. Variant Selection & Live State -> PASS (clicking 'L' updates price, stock badge, and syncs URL `?variant=52`).
    6. Mobile Sticky Bar & Obstruction Safety -> PASS (appears on scroll; suppressed on cart drawer open and input focus).
    7. Video Lifecycle Invariants -> PASS (video controls, pause on change, tab visibility pause).
- **Evidence Screenshots**:
  - Desktop Product Details: `.local/frontend-redesign/run_u3_gallery/u3_desktop_product_details.png`
  - Gallery Slide Navigation: `.local/frontend-redesign/run_u3_gallery/u3_gallery_slide_navigation.png`
  - Lightbox Zoom: `.local/frontend-redesign/run_u3_gallery/u3_gallery_lightbox_zoom.png`
  - Variant Selection & Live Price: `.local/frontend-redesign/run_u3_gallery/u3_variant_selection_live_price.png`
  - Mobile Sticky Purchase Bar: `.local/frontend-redesign/run_u3_gallery/u3_mobile_sticky_purchase_bar.png`
  - JSON evidence: `.local/frontend-redesign/run_u3_gallery/u3_verification.json`
- **Next Step**:
  - Proceed to Phase U4: Cart drawer & Checkout view refinements, lab COD & bank handoff presentation, and accessibility (dialog focus trap, Tab wrapping, Escape).




