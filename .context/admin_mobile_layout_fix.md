# Admin mobile layout and scrolling fix — 2026-11-08

The owner's `image.png` was found and inspected. It shows the mobile navigation occupying the entire viewport, duplicated logos, and content pushed out of view. Reproduced locally using browser-only SAMPLE owner/catalog responses; no real login or data changes.

Cause: `.admin-page > .modal-content` forced `flex-direction: row !important`, while the mobile column rule lacked matching priority. The sidebar stretched to full screen height, its flex navigation expanded vertically, and the content had insufficient room. Desktop viewport heights also failed to account for a lab banner, and flex scroll children lacked explicit minimum-height constraints.

Changed `frontend/src/styles/admin.css`:

- Mobile shell correctly stacks vertically. Navigation is a compact horizontal row with 44px targets and one visible logo; sign-out remains reachable.
- Main content takes the remaining height. Explicit `min-height: 0` permits its own scrolling, with safe-area bottom padding.
- Desktop sizing stays within the shell; viewport calculations subtract the optional lab banner and use dynamic viewport units with a `vh` fallback.

Added `ops/admin_mobile_smoke.cjs` to CI packaging and pre-publication image checks. It tests 360×640, 390×844, 760×700, 768×1024 and 1440×900; verifies layout, logo count, overflow, touch/wheel scrolling, bottom reachability, final horizontal navigation item, a 480px-high viewport and a simulated lab banner. Explicit CDP touch-start/move/end events work in the test browser; its synthetic scroll-gesture shortcut did not scroll, so it is not used as evidence.

Verification: 140 frontend tests passed; production Vite build passed; browser checks passed at all five widths. Baseline mobile sidebar heights were 640/844/700px; fixed mobile sidebar height is 178px, nav height 68px. Sample product content scrolls inside the remaining area. Desktop layout remains horizontal. Local screenshots: `.local/admin-mobile/before/` and `after/`. Third-party fonts are blocked in this geometry regression to avoid network-dependent results; product/account responses are synthetic. This is Chrome emulation, not a physical iPhone/Safari acceptance test.

This fixes repository source. It does not change the already-running Azure containers: deploy the corrected build through the configured release process, then recheck alphazee.tech/admin on the affected phone.
