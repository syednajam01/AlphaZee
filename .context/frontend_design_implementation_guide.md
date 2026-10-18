# AlphaZee: storefront design and implementation brief

For Antigravity. Prepared 2026-10-19. Implement this brief in the existing project, phase by phase, using your browser after EVERY phase. This is a proposed design direction, not a claim that these screens already exist or have passed visual testing.

## 1. Context and scope

Read `.agent/AGENTS.md`, `.context/m9_owner_handoff.md` and `.context/production_readiness_summary.md` first. Use `.context/browser_acceptance_v2_review.md` for evidence limitations. Preserve API contracts, owner authentication, exact PKR totals, inventory/fulfillment rules and persistent data. Keep normal/public checkout closed; test orders only at `http://127.0.0.1:13001`. Normal development is `http://localhost:13000`. No deployment, database resets or sample data in development.

Goal: a distinctive, calm Pakistani apparel store where buyers understand the product, choose the right variant and complete an order confidently. Redesign the customer experience; keep owner operations functional. Do not invent reviews, discounts, scarcity, guarantees, delivery promises or bank/payment capabilities. Unavailable content needs an honest empty state. No decorative controls without working behavior.

### Framework flexibility — owner update, 2026-10-19

You may use React (including with existing Vite), another suitable frontend framework, or styling/component libraries, and customize Docker packaging accordingly. You are not restricted to plain JavaScript/raw CSS. Choose tools for maintainability, accessible interactions and the visual brief; framework adoption alone does not improve design. Theme library components to AlphaZee rather than accepting generic defaults.

Before migrating, inspect work already completed and record the choice, benefit and migration scope in the progress file. Preserve that work; migrate incrementally and reuse existing API/cart logic. Keep backend contracts and environment boundaries intact. Update dependencies/lockfile, build scripts, relevant tests, Dockerfiles, Compose configuration and serving/proxy rules where needed. Check official framework documentation during implementation.

Verify development, production-image and isolated-lab builds/startup, deep-link refresh, assets/media, same-origin API/session/CSRF behavior, admin access and cart persistence. Then run the phase's browser gate. Record actual commands/results and remaining gaps; container changes do not authorize deployment or opening public checkout.

## 2. Visual system: warm editorial commerce

Preserve the AlphaZee logo. Use photography, strong type hierarchy and precise alignment; avoid excessive pills, gradients, glass effects, floating cards and animation.

| Foundation | Required starting specification |
| --- | --- |
| Color | Page ivory `#F7F7F2`; surfaces white; text `#171717`; secondary text `#595959`; primary green `#145C44`, hover `#0E4231`; pale green `#E8F2EE`; dividers `#DEDED7`. Error `#B42318`, success `#145C44`. Measure contrast for actual combinations. |
| Typography | Manrope for UI/body, Newsreader for editorial hero/section headings only. Use licensed WOFF2 assets, preferably self-hosted, `font-display: swap`, system/Georgia fallbacks. Maximum two families; UI weights 400/500/600/700, editorial 500. Fonts failing must not block shopping. |
| Type scale | Body/input 16px, line-height 1.5; secondary 14px; metadata 12px only for nonessential content; product title 28–40px; section 24–36px; hero 36–64px with fluid `clamp()`. Numeric prices use tabular figures. Avoid all-caps paragraphs. |
| Spacing/layout | Tokens 4/8/12/16/24/32/48/64/96px. Container max 1280px; gutters 16px mobile, 24px tablet, 40px desktop. Sections 40–56px mobile, 64–96px desktop. No arbitrary enormous empty regions. |
| Controls | Primary solid green/white, secondary outline, tertiary text. Button/input height 48px; compact icon target at least 44×44px as this project's usability target. Radius 8px controls, 12px dialogs; media mostly square-edged. Visible hover, focus, active, loading, disabled and error states. |
| Motion | 150–220ms opacity/transform transitions; restrained drawers. Honor reduced motion. No scroll hijacking, bouncing purchase buttons or automatic hero carousel. |

Centralize tokens/components; remove conflicting inline styles in touched screens. Scope storefront styling so it does not break admin. Maintain semantic HTML, labels, meaningful link text and visible focus. Normal text contrast target 4.5:1; measure rather than assume. See [W3C contrast guidance](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html).

## 3. Responsive pages and product identity

- **Header/home:** compact logo/navigation/cart; visible Shop and Track order; accessible mobile menu. One editorial hero with one clear shopping CTA and real managed imagery, followed by collections and products. Keep the first shopping content reachable without excessive scrolling. Footer includes actual support/policy information; flag missing business copy instead of inventing it.
- **Catalog:** two columns on typical phones, three on tablets, four on wide screens; gracefully use one if content requires it at narrow widths/zoom. Consistent image ratio, title/price alignment and availability labels. Filter/sort controls must use supported data and apply across the full result set, not just loaded cards. Preserve filters and scroll position on return from a product.
- **Product page:** implement real `/products/:slug` routes. Product cards/title/image must be anchors supporting new tabs and sharing. Optional quick view is secondary. Direct paste, reload, Back/Forward and invalid/archived URLs must work. Reuse existing catalog APIs and stable product/variant IDs; handle changed slugs without corrupting carts. Optional `?variant=<id>` restores only a valid variant belonging to that product.
- **Desktop product layout:** roughly 58% gallery / 42% purchase details; sticky summary only while it fits. Show breadcrumb, title, PKR price, availability, color/size with clear selection, size guide, quantity and Add to cart. Below: description, material/care, sizing, delivery/returns and relevant products from actual catalog data.
- **Mobile product layout:** gallery first, then purchase essentials; full-width CTA. A bottom purchase bar may appear when the main CTA leaves view; reserve space, respect safe areas and never cover fields, keyboard or dialogs. It must reflect variant/price/stock accurately; no silent default size.
- Give each product a meaningful document title/description and canonical URL. Provide a useful unavailable-product screen. Verify deep links through the chosen development server AND production serving configuration (currently Caddy); distinguish client-side not-found UI from a genuine HTTP 404. Social previews/indexing may need server-rendered metadata: record that gap honestly.

## 4. Image, hover and video behavior

Catalog photographs use consistent 3:4 frames with intentional crop/focal point; product detail images preserve garment visibility using contain where appropriate. Reserve dimensions to prevent layout shifts. Never stretch images. Use real supplied product assets; synthetic fixtures stay in the lab. Missing-media states remain neutral.

On `(hover: hover) and (pointer: fine)`, a brief deliberate hover crossfades to the next valid still image in about 180ms; leaving restores the primary image. No second asset means no swap. Keyboard/touch users retain access to all views on the product page. On touch, tapping a card navigates immediately; never require a first tap to activate hover.

Product gallery supports thumbnails, swipe with visible controls/count, keyboard navigation and image enlargement. Preserve vertical page scrolling and browser pinch zoom. Videos show a poster and Play button, use `playsinline`, visible controls and load on demand. Play only after explicit interaction; pause on slide/variant/route change, modal close or hidden tab. One video at a time; never autoplay sound or grid videos. Handle loading/playback failure with retry/poster fallback. Lazy-load below-fold media; prioritize only the lead image and use responsive sources when actually available. Follow [video loading guidance](https://web.dev/learn/performance/video-performance).

## 5. Cart, checkout and HCI

Cart shows image, chosen options, exact price, editable quantity/remove and honest delivery/total information. Adding an item gives visible confirmation without stealing focus unexpectedly. Reconcile unavailable/changed products visibly. Preserve existing idempotent order/retry behavior.

Checkout: one-column mobile form; desktop form plus readable summary. Persistent labels, appropriate autocomplete/input types, inline actionable errors and error summary. Preserve valid input, prevent repeated submission and announce progress. Use “Checking availability…” while pending; do not flash “Checkout unavailable” for ordinary loading. Do not hardcode new shipping charges or promises.

Clearly explain COD versus bank transfer: supplier confirmation precedes bank instructions; owner verifies received funds before dispatch. Confirmation shows order reference, next steps and private access-code guidance; never place that code in URLs/analytics. Tracking/return forms use the same visual language.

Dialogs must support first/last Tab wrapping, reverse wrapping, Escape, sensible initial focus, visible focus restoration to a usable trigger and background inertness. Test cart-to-checkout transitions with real keyboard actions. Errors cannot rely on color alone. Respect zoom/reduced motion; describe unavailable states rather than hiding reasons.

## 6. Implementation phases and mandatory browser gates

| Phase | Implement | Open browser and verify before advancing |
| --- | --- | --- |
| U0 | Capture existing screens; create tokens/shared controls and a concise component reference. | Compare header, type, buttons/forms and product card at mobile/desktop. Record before screenshots. |
| U1 | Product routing and page shell, preserving catalog/cart state and admin routes. | Direct URL, refresh, new tab, Back/Forward, invalid slug, archived product, valid/invalid variant query; production build deep links. |
| U2 | Header/home/catalog and media interactions. | Hover enter/leave, touch navigation, consistent crops, absent second image, empty/error/retry, filters and pagination. |
| U3 | Full product gallery/details/variant selection and purchase controls. | Image/video/swipe/zoom, pause behavior, size/stock changes, keyboard navigation and mobile purchase bar without obstruction. |
| U4 | Cart, checkout, confirmation and tracking/return presentation. | Lab COD and bank journeys, invalid fields, stock changes, offline/retry, exact totals, duplicate-submit safety and focus restoration. |
| U5 | Visual polish and targeted regression. | 360/390/768/1280/1440px, actual 200% browser zoom, keyboard boundaries, slow network, reduced motion, media failure and owner-console smoke check. |

At EACH gate: inspect screenshots yourself, exercise controls, inspect Console/Network, fix introduced defects, repeat affected checks and save evidence. Run relevant frontend tests and build. Test meaningful routing/state changes; do not weaken tests to pass new selectors. Mark unavailable browsers/hardware NOT TESTED. Device pixel ratio or pinch emulation is not desktop browser zoom. No blanket accessibility or production certification.

## 7. Code map and handoff

Start with `frontend/src/styles/variables.css`, `main.css`, `components.css`, `grid.css`; `main.js`/`app.js`; `components/Header.js`, `FeaturedProducts.js`, `ProductModal.js`, `ProductGallery.js`, `CartDrawer.js`, `CheckoutView.js`, `OrderTrackingModal.js`; `utils/api.js`, `cart.js`, `overlay.js`, `capabilities.js`. Extract reusable product presentation for the new page; avoid duplicated business logic. Check `frontend/Caddyfile` and existing tests/runners for integration.

Keep `.context/frontend_redesign_progress.md` updated per phase: scope, changed files, checks actually run, screenshot paths under `.local/frontend-redesign/<run>/`, failures/fixes, known gaps and next phase. Preserve earlier acceptance evidence and secrets. Work through U0–U5 sequentially; a blocker pauses dependent work, not independent improvements. Final handoff must distinguish implemented, browser-verified and remaining work.
