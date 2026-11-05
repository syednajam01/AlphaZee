# Antigravity: complete the three-portal experience

## Mission and execution order

Act as a senior product designer, frontend engineer and browser QA engineer. Inspect, implement, measure and verify the existing application in this order: **customer storefront → admin portal → vendor portal**. “Main website” includes the full shopping journey, not only the homepage. Finish each portal's acceptance gate before starting substantial redesign of the next. Preserve recent working improvements; avoid decorative changes without a usability purpose.

Read first: `.agent/AGENTS.md`, this guide, `.context/frontend_browser_repair_report.md`, and the latest entries in `.context/frontend_redesign_progress.md`. Consult `.context/brand_voice_and_story_guide.md` for copy and `.context/temporary_media_preview.md` for current assets. Read finance/media specifications only when working on those controls. Do not load every historical document at once.

The November 6 report records gallery sizing, contrast, thumbnail, hero and hover improvements. Treat its claims as prior evidence, then inspect the current build. A screenshot count, CSS transform, `decoding="async"`, or animation FPS sample does not establish complete usability or performance.

## Boundaries and code map

- Normal storefront: `http://localhost:13000`; `/admin` and `/vendor`. Checkout remains closed. Existing owner credentials must not be reset.
- Lab: `http://127.0.0.1:13001`; separate owner/vendor/customer browser profiles. Use this for test purchases, stock changes, payouts, returns and destructive interaction tests. Preserve SAMPLE notices. No real transfers.
- Development contains the explicitly authorized `/products/temporary-media-preview-20261105`. Preserve it and its restore manifest. Its zero price/unavailable state is intentional. Do not infer real product quality, prices or stock from these personal photos. Additional fixtures belong in the lab.
- Keep the existing Vite/JavaScript implementation unless a specific requirement justifies an architectural change. Do not migrate to React/Next.js merely to improve appearance. Preserve same-origin API, session/CSRF controls, checkout gate, accounting definitions and media associations. Never hide leaked data with CSS as a privacy fix.
- Shared foundations: `frontend/src/styles/{variables,reset,layout,main,components}.css`; `utils/{api,dom,overlay,cart,capabilities}.js`; `main.js`, `app.js`.
- Storefront: `components/{Header,MobileNavDrawer,Hero,Collections,FeaturedProducts,ProductPage,ProductGallery,ProductModal,CartDrawer,CheckoutView,OrderTrackingModal,ReassuranceFooter}.js`; corresponding CSS.
- Admin: `AdminDashboard.js`, `AdminConsole.js`, `components/admin/`, `styles/admin.css`. Vendor: `VendorPortal.js`, `styles/vendor_portal.css`. Existing tests: `frontend/tests/`.

## P0 — Establish a baseline and shared design rules

Inventory every current route, section, dialog and primary action. Record purpose, default/empty/loading/error states and defects. Rank **P0** broken or unsafe flows, **P1** significant friction/readability, **P2** polish. Preserve unrelated working-tree changes and document missing business decisions separately.

Capture before screenshots at 1366×768 and 390×844. Define a small, consistent system using existing Manrope/Newsreader, green/neutral palette, spacing, buttons, fields, badges and icons. Storefront should feel editorial; admin should be dense but readable; vendor should be simple and mobile-first. Shared identity does not require identical layouts.

Make foreground/background pairs explicit across default, hover, selected, disabled, error and focus states. Target 4.5:1 normal-text contrast, 3:1 large text and meaningful control boundaries. Use visible keyboard focus, labeled inputs, approximately 44px touch targets, readable body text and clear action hierarchy. Scope portal styles to prevent theme leakage; remove conflicting overrides deliberately. Motion should communicate feedback, respect reduced motion and never be necessary to understand a control.

**Gate:** baseline issue list, screenshots, route/action inventory, and shared component decisions saved in the progress file. Open real affected pages after any shared-style change.

## P1 — Storefront discovery and product decisions

1. **Header/navigation:** recognizable brand, clear shopping and order tracking, useful cart count, accessible mobile menu, active navigation and working Back/Forward. Sticky bars must not obscure content or focus targets. Avoid unnecessary header height.
2. **Home/hero:** one clear primary shopping action, concise brand copy and a visible route to collections. Balance media, text and whitespace. Preserve muted hero playback, playlist advancement/loop, pause/manual controls, poster fallback and reduced-motion behavior. Check portrait and landscape media without stretching or obscuring the subject. Keep text readable over every slide; do not manufacture trust badges, urgency, reviews or guarantees.
3. **Collections/catalog:** understandable labels, consistent cards, real PKR prices, availability and full-result pagination/filter behavior. Search/sort controls must work against supported data; remove misleading controls or document a required API change. Preserve navigation context when returning from a product. Verify hover front/back on fine pointers and immediate navigation on touch. Handle absent second images and missing media.
4. **Product page:** preserve viewport-fitting selected media and complete playback controls. Test portrait/landscape/square images and 9 photos plus one video. Compact thumbnail navigation, meaningful image alt text, keyboard/swipe/enlarge, correct pause behavior and stable layout are required. Details remain naturally scrollable; short screens and zoom must reflow rather than clip.
5. **Purchase essentials:** title, price, exact variant, size guide, stock, quantity and action must be understandable. No silent size selection; incompatible options explain why unavailable. Show real description/material/care/sizing and delivery/returns information, distinguishing missing facts. Mobile purchase bars must reflect the current variant and avoid overlapping keyboard, dialogs or page content.

**Gate:** customer can navigate home → collection → product, compare media, select a valid variant, and recover from unavailable/missing products using mouse, touch and keyboard. Confirm direct product URLs, refresh, invalid URLs and Back/Forward. Preserve existing gallery fit measurements at normal zoom.

## P2 — Storefront transaction, trust and recovery

- **Cart:** exact chosen variant/photo/price, understandable quantity/remove controls, empty state, totals, changed-price/unavailable reconciliation and clear next action. No misleading delivery promises or unexpected loss of cart state.
- **Checkout, in lab:** persistent field labels, suitable keyboard/autocomplete, inline errors plus accessible summary, preserved valid input, clear quote/confirmation totals, pending feedback, retry recovery and duplicate-submit protection. Both COD and bank journeys must remain accurate. Supplier confirmation precedes bank instruction handoff; payment evidence is not automatic verification.
- **After purchase:** clear order reference, next steps, private tracking/access flow, delivery/payment distinction, return/exchange eligibility and refund status. Do not expose access codes in URLs, screenshots or analytics.
- **Trust/support:** working policy/support links and owner-approved details. Missing commercial content is a recorded launch blocker, not permission to invent claims. Ensure footer and long policy content work on small screens.
- **Resilience:** delayed/failed API, missing media, session expiry, browser refresh, offline retry, invalid input and repeated clicks. Focus must enter/leave dialogs correctly, including cart-to-checkout transitions. Announce status/errors without stealing focus or relying solely on color.
- **Discoverability:** one meaningful main heading, coherent page titles/canonical URLs, crawlable product links and honest metadata. Check existing sitemap/robots/structured data before changing them. Document SPA/server-rendering limitations; private admin/vendor pages must not be advertised for indexing.

**Gate:** complete both lab payment journeys and tracking/return UI paths. Verify real outcomes, not merely button clicks. All customer P0/P1 issues within this scope must be fixed or explicitly blocked before admin redesign.

## P3 — Measure storefront performance

Profile a **production build served locally** as well as the development experience. Record browser/version, viewport, CPU/network throttling, cache state, build identifier and fixture. Run three comparable cold-load measurements for home/product and a representative interaction trace; report median plus spread. Compare before/after under identical conditions.

Project targets: LCP ≤2.5s, CLS ≤0.1, and representative interaction latency ≤200ms under the documented profile. These are targets, not guaranteed results. Report Lighthouse/TBT, resource weight, requests, long tasks and interaction traces separately; lab scores do not establish real-user INP or field Core Web Vitals. Record the actual LCP element and largest resources.

Prioritize visible lead media; avoid lazy-loading the LCP image. Reserve media dimensions, lazy-load below-fold content, load gallery videos on demand and prevent hidden videos from downloading/playing unnecessarily. Limit concurrent hero video loading while allowing its intended autoplay. Preserve original uploads; any responsive derivatives must be separate, reversible assets with quality checked. Do not re-encode originals silently.

Inspect duplicate requests, whole-page re-renders, listener cleanup, font fallback, layout thrashing, oversized dependencies and unbounded lists. Confirm storefront bundles exclude private dashboard code. Apply `will-change` only where measured benefit warrants it; blanket layers/shadows/blur can worsen memory and scrolling. Cache immutable public media appropriately, never private API/session responses.

**Gate:** measured improvement or a documented satisfactory baseline, no functionality regression, honest remaining bottlenecks. A localhost connection or a smooth hover is not a complete performance pass.

## P4 — Admin portal: reliable daily operations

Build around tasks: review orders → fulfill → reconcile money; manage products/media → stock/vendors; inspect reports → configure store. Keep navigation labels, page titles, breadcrumbs, search/filter and return-to-list behavior consistent. Preserve per-owner preferences; compact mode must remain readable.

- **Dashboard:** prioritize actions needing attention. Label time period, timezone, freshness and empty states. Distinguish revenue, cash, supplier payable, refunds, courier-held COD and contribution; never present estimated contribution as final profit.
- **Tables/detail:** aligned PKR values, readable status labels, stable pagination/sort/filter, matching exports, clear row selection and accessible mobile detail views. Use contained horizontal scrolling only for genuinely wide tables; keep key identity/actions accessible.
- **Catalog/media:** visible save/dirty state, draft/published status, actionable validation, upload progress/error/retry, primary/hover/poster assignments, gallery order, collection membership and preview. Keep source/vendor assignment and stock ownership consequences understandable.
- **Orders/finance:** separate order/payment/delivery/settlement states. Show allowed next actions and why others are blocked. Confirm consequential mutations with the exact order/vendor/amount; prevent repeated submissions. Supplier charges/payments, reversals, expenses, return inspection, refunds and RTO freight must remain auditable.
- **Inventory/vendors:** clearly separate physical, held and available quantities. Explain shortage and historical ownership review, stale edits and reassignment restrictions. Vendor login creation/reset/revocation must avoid exposing credentials in lists or logs.
- **Settings:** distinguish store-wide settings from personal preferences, draft policies from published ones, and configured delivery rules from defaults. Persist, reset and preview must do what their labels promise.

**Gate:** in lab, owner completes catalog/media setup, vendor assignment/login, stock update, fulfillment, return inspection and money reconciliation through real forms. Compare ledger/report values before/after presentation changes. Test interrupted saves, two-tab conflicts, session expiry and keyboard navigation. Profile dashboard/list loads; bound requests/data without hiding totals.

## P5 — Vendor portal: fast, clear stock updates

Keep scope to assigned stock. Show shop identity, product thumbnail/title/SKU/size/color, vendor count, committed holds, available online, and last confirmed update. Explain labels in plain language without exposing internal costs, retail prices, customer details or other vendors' information.

Make search and exact-SKU count entry usable one-handed on a small phone. Example: stored count 3, one sold in the shop → enter the new absolute physical count **2**, not a decrement of 1. Clearly define the quantity as vendor units allocated to AlphaZee; preserve separately owned returned stock. Validate nonnegative integers, show the proposed count and acknowledge only server-confirmed saves.

Handle stale versions by refreshing/reviewing, not silently overwriting. If reported stock is below holds, explain that the report was saved and owner review is needed; existing reservations remain protected and new sales stay blocked. Provide useful history/reason labels, zero-stock/no-match states, retry and logout. Never queue offline inventory changes silently. No vendor pricing/orders/payout portal expansion in this task.

**Gate:** two vendors in separate profiles: search → exact variant → count 3→2 → reload → history; repeat stale/conflicting counts, shortage reporting and revoked login. Verify response payloads as well as visible UI for isolation. Profile list/search/save under the same constrained mobile conditions.

## P6 — Cross-portal acceptance and handoff

At every phase: **inspect → implement → open browser → operate controls → inspect Console/Network and screenshots → fix → repeat**. Store evidence under `.local/three-portal-quality/<run>/`. Review screenshots personally. Record failures and retests; do not automatically label every capture PASS.

Final matrix: 360×640, 390×844, 768×1024, 1366×768, 1440×900, mobile landscape, real desktop 200% zoom, keyboard-only and reduced motion. Check supported browsers where available; mark physical Android/iPhone and screen-reader checks NOT TESTED if unavailable. Include long text, empty/large lists, 9-photo/1-video product, slow/error responses, dropdowns, dialogs and virtual keyboard obstruction. No horizontal page overflow, unreadable labels or hidden primary controls.

Run `npm.cmd test` and `npm.cmd run build`; add meaningful tests for changed state/interaction behavior. Use the guarded disposable backend runner if backend contracts change. Keep development/lab builds current and verify affected production packaging/deep links. Do not deploy publicly or open production checkout.

Maintain `.context/three_portal_quality_progress.md` with current phase, defects, decisions and next action. Finish with `.context/three_portal_quality_report.md`: route/action coverage; changed files; before/after screenshots and metrics; actual commands/results; implemented/browser-verified/not-tested distinctions; P0/P1/P2 leftovers; and owner-only commercial decisions. Link it from existing frontend progress without overwriting history. Completion requires working, verified journeys across all three portals, not visual polish alone.
