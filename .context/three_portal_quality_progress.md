# Three-Portal Experience Quality Progress

**Owner**: Syed Najam  
**Updated**: 2026-11-06  
**Execution Order**: Customer Storefront → Admin Portal → Vendor Portal  
**Current Phase**: Phase P0 Complete & Signed Off → Phase P1 Active (Storefront Discovery & Product Decisions)

---

## 1. Route, Section, Dialog & Action Baseline Inventory

| Portal | Route / Context | Primary Sections & Dialogs | Primary Actions | Loading / Empty / Error State Handling |
| :--- | :--- | :--- | :--- | :--- |
| **Storefront** | `/` (Home) | Announcement bar, Sticky Header, Hero carousel, Collections bar, Featured Products grid, Reassurance & Delivery, FAQ accordion, Footer | Browse pieces, switch hero slides/videos, filter collections, sort catalog, quick-view, view details | Skeletons for grid (`.catalog-skeleton-card`), retry on connection failure (`.catalog-status-box.is-error`), fallback for hero |
| **Storefront** | `/products/:slug` (Product Details) | Breadcrumbs, Media Gallery (images + video, thumbnails, zoom lightbox), Product info & pricing, Color/Size options, Quantity stepper, Add to Bag, Details accordions, Related pieces, Sticky mobile bar | Select variant, enlarge image, play video, change qty, add to bag, navigate breadcrumbs/related | Skeleton loader during fetch, dedicated 404/unavailable recovery screen (`.product-unavailable-view`) with catalog return CTA |
| **Storefront** | Overlay: Cart Drawer | `#cart-drawer`, `#cart-backdrop` | Adjust qty, remove line item, proceed to checkout (`#btn-checkout`), return to shop | Empty bag illustration and message, total price with PKR formatting, item counter badge |
| **Storefront** | Overlay: Mobile Nav | `#mobile-nav-drawer`, `#mobile-nav-backdrop` | Navigate to sections, open Track Order, view assistance notice | Focus trapped, close on backdrop/escape/link click, ARIA expanded state |
| **Storefront** | Overlay: Order Tracking | `#order-tracking-modal`, `#order-tracking-backdrop` | Lookup order by Order # and private Access Code, view 4-step status | Inline error on invalid lookup, spinner during fetch, full order status card |
| **Storefront (Lab)**| `http://127.0.0.1:13001` (Checkout) | `#checkout-modal` (Lab only) | Enter shipping address, select COD vs Bank Transfer, place test order | Client-side validation, error summary, lab banner (`SAMPLE CHECKOUT LAB`), post-purchase order summary with access code |
| **Admin** | `/admin` (Owner Console) | Sidebar navigation, Header with owner status, 12 Tabs: Overview, Products, Collections, Media, Inventory, Suppliers, Orders, Returns, Coupons, Expenses, Reports, Settings | Fulfill orders, adjust stock, review supplier acceptance, process returns, record COD remittance, configure settings | Session check (`Checking owner session...`), sign-in form (`#admin-auth-form`), inline alerts for auth failure |
| **Vendor** | `/vendor` (Stock Portal) | Stock-only mobile container, Top stats bar, Search bar, SKU stock table/cards, Count adjustment modal, Shortage report modal, History modal | Search assigned SKU, submit absolute physical count, report shortage, view stock audit log | Session check, dedicated vendor login (`#vp-login-form`), error alerts, zero-stock notice |

---

## 2. Baseline Defect Ranking (P0 / P1 / P2)

### P0 — Broken or Unsafe Flows (Must Fix Immediately)
- **None currently breaking**: Checkout lab isolation is strictly enforced (503 on development 13000; lab active on 13001). Development owner `syed123` preserved. No credentials or private tokens exposed.

### P1 — Friction, Usability, Accessibility (Active Focus)
1. **Header Active Navigation Indicator**: Desktop navigation lacks active section highlighting (`.nav-link.active`, `aria-current="page"`) to inform user of current position as they scroll between sections (`#featured`, `#collections`, `#reassurance`, `#faq`) or view product pages.
2. **Hero Call to Action Hierarchy**: The hero currently features multiple buttons ("View Product Details" and "Browse Catalog") with competing prominence; needs a single prominent primary shopping CTA paired with a clear route to collections.
3. **Cross-Route Link Delegation**: Ensure seamless transitions when clicking anchor links (`#collections`, `#featured`, `#track`) from `/products/:slug` back to the home page sections without jarring reloads.
4. **Touch Target Sizing**: Verify minimum 44×44px hit areas on mobile viewports for all interactive controls (cart button, mobile toggle, thumbnails, quantity buttons, filter pills).
5. **Focus Rings & Keyboard Accessibility**: Consistent 3:1 contrast focus rings (`:focus-visible`) across all buttons, inputs, pills, and dialog triggers for complete keyboard navigability.
6. **Dialog Focus Management**: Ensure focus is captured, trapped, and returned upon closing across `MobileNavDrawer`, `CartDrawer`, and `OrderTrackingModal`.

### P2 — Visual Polish & Refinement
1. **Typography & Font Fallbacks**: Ensure consistent pairing of Manrope (clean UI sans) and Newsreader (editorial serif accent) across all banners, cards, and modal headers.
2. **Sticky Header Transition Smoothness**: Ensure rAF-throttled sticky header background and shadow apply without micro-stuttering or obscuring anchored section titles.
3. **Editorial Accordion Clarity**: Clearly demarcate verified product facts from unverified details (e.g., material composition, care guidelines) without visual noise.

---

## 3. Shared Design Tokens & System Rules

To maintain cross-portal coherence while respecting differing information densities:

```css
:root {
  /* Typography */
  --font-family: 'Manrope', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --font-family-serif: 'Newsreader', Georgia, Cambria, serif;
  
  /* Color Palette */
  --color-bg: #FAFAFA;
  --color-surface: #FFFFFF;
  --color-surface-raised: #FFFFFF;
  --color-text: #111827;
  --color-text-muted: #6B7280;
  --color-text-subtle: #9CA3AF;
  
  /* Brand Accent (Forest / Pine Green) */
  --color-accent: #1B4332;
  --color-accent-hover: #143326;
  --color-accent-subtle: #E8F5E9;
  
  /* Borders & Dividers */
  --color-border: #E5E7EB;
  --color-border-subtle: #F3F4F6;
  
  /* Status Colors */
  --color-success: #059669;
  --color-warning: #D97706;
  --color-error: #DC2626;
  --color-error-bg: #FEF2F2;
  
  /* Focus Rings */
  --focus-ring: 2px solid #1B4332;
  --focus-ring-offset: 2px;
  
  /* Minimum Touch Target */
  --min-touch-target: 44px;
}
```

### Shared UI Principles
- **Touch Targets**: All buttons, links, inputs, and pills must provide at least 44×44px hit bounds on touch devices.
- **Contrast**: Normal text must meet ≥4.5:1 contrast against its background; large headings and non-text control boundaries must meet ≥3:1.
- **Focus Rings**: All interactive controls must exhibit an unambiguous, high-contrast `:focus-visible` ring; mouse clicks must not show ugly focus rings.
- **No Decorative Overload**: Every visual element must serve clarity, orientation, or feedback.

---

## 4. Phase Verification Gates

| Phase | Description | Status | Evidence / Artifacts |
| :--- | :--- | :--- | :--- |
| **P0** | Baseline Inventory, Defect Ranking & Shared Design Tokens | **SIGNED OFF** | 14 baseline screenshots in `.local/three-portal-quality/run_p0_baseline/` and brain artifacts |
| **P1** | Storefront Discovery & Product Decisions | **SIGNED OFF** | 12 screenshots in `.local/three-portal-quality/run_p1_discovery/` and brain artifacts; 137 unit tests passed; Vite build passed |
| **P2** | Storefront Transaction, Trust & Recovery | **SIGNED OFF** | 11 screenshots in `.local/three-portal-quality/run_p2_transactions/` and brain artifacts; COD purchase, bank transfer, private access code generation, order tracking lookup, cart quantity increment & removal verified 100% |
| **P3** | Storefront Performance Profiling | **SIGNED OFF** | Production build median LCP: 956ms (Home), 976ms (Product); CLS: 0.0047 (Home), 0.0010 (Product), 0.0000 (Mobile Product); Interaction Latency: 15.1ms (Cart Drawer), 8.0ms (Gallery Next); Code-split chunks verified; 6 screenshots + performance_measurements.json in `.local/three-portal-quality/run_p3_performance/` |
| **P4** | Admin Portal Daily Operations | **SIGNED OFF** | 14 screenshots in `.local/three-portal-quality/run_p4_admin/` and brain artifacts; 12 operational tabs verified on Desktop & Mobile (Overview, Orders, Products, Collections, Media, Inventory, Suppliers, Returns, Financial Reports, Settings); Keyboard focus verified |
| **P5** | Vendor Stock Portal Synchronization | **SIGNED OFF** | 9 mobile screenshots in `.local/three-portal-quality/run_p5_vendor/` and brain artifacts; Multi-vendor catalog isolation (Vendor 1 vs Vendor 2), SKU search, exact physical count update (3 -> 2), audit history modal, shortage reporting modal, and clean sign-out verified 100% |
| **P6** | Cross-Portal Matrix & Final Report | **SIGNED OFF** | 16 screenshots in `.local/three-portal-quality/run_p6_matrix/` and brain artifacts; Full viewport matrix (360x640, 390x844, 844x390, 768x1024, 1366x768, 1440x900) with zero horizontal overflow; 200% desktop zoom reflow; keyboard focus rings; reduced motion compliance; all 137 unit tests passed; Vite build clean in 3.71s |

