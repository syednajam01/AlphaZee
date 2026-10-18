# AlphaZee Storefront Redesign: Progress & Verification Register

Tracking implementation of [.context/frontend_design_implementation_guide.md](file:///f:/AlphaZee/.context/frontend_design_implementation_guide.md) across phases U0–U5.

## Phase Register

| Phase | Description | Status | Evidence Location | Gaps / Notes |
|---|---|---|---|---|
| **U0** | Baseline capture, visual tokens (`variables.css`, `components.css`), shared controls & component reference | **Completed** | `.local/frontend-redesign/run_u0_baseline/` | Verified tokens, typography (Manrope/Newsreader), controls, 108 tests pass, build pass |
| **U1** | Direct `/products/:slug` routing, page shell, history/query handling, deep link fallbacks | **Completed** | `.local/frontend-redesign/run_u1_routing/` | All 6 browser checks passed, deep links, reload, 404, query variants, mobile bar verified |
| **U2** | Header/home layout, 3:4 catalog cards, image hover crossfades, filters & full-result set sort | In Progress | `.local/frontend-redesign/run_u2_catalog/` | Evaluating Next.js migration tradeoffs per owner instruction |
| **U3** | Product detail page layout (58/42 desktop split, mobile stack & sticky purchase bar), gallery swipe/zoom/video | Not Started | — | Depends on U2 |
| **U4** | Cart drawer & Checkout view refinements, accessibility (dialog focus trap, Escape, Tab wrap), validation & honest state | Not Started | — | Depends on U3 |
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


