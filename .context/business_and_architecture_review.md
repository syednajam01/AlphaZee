# AlphaZee: business review and architecture decision plan

Reviewed 2026-10-19. Two analytical roles, followed by a joint decision record; this is one evidence-based review, not a meeting with external specialists. Recommendations only: no application, database, checkout gate or deployment was changed.

## Decision for the owner

**Keep the existing commerce foundation. Prioritize truthful product information, reliable buying flows and operational readiness before more redesign or paid acquisition.** The redesign is substantial, but “U0–U5 completed” does not establish readiness for real orders. Next.js remains an option for public-page rendering; it has not been implemented in this checkout.

Evidence: inspected the supplied [redesign register](frontend_redesign_progress.md), relevant frontend/backend/container code, U3/U5 JSON and U4/U5 browser scripts, and three supplied screenshots below. Fresh checks: `npm.cmd test` → **123 passed, 0 failed**; `npm.cmd run build` → **passed, Vite 7.3.7, 35 modules**. No fresh browser session, backend suite, database inspection, Docker rebuild, production acceptance or real-customer research was performed. Historical reports are supporting evidence, not fresh certification. Product Design review guidance informed the journey assessment.

## Role 1 — senior business specialist

### Business model and strengths

AlphaZee is currently an owner-operated apparel retailer sourcing through suppliers. Its strongest assets are the existing catalog/inventory controls, exact order pricing, supplier confirmation, COD/bank workflows, private tracking, returns and cash reconciliation. These support a practical small-store operating model. A vendor marketplace, automated payments and a new backend are unnecessary for an initial controlled launch.

The business objective should be **orders customers keep, that generate positive contribution and whose money is actually reconciled**. Attractive screens help customers decide, but orders placed, orders delivered and cash received are different outcomes. No traffic, conversion, supplier performance or customer retention evidence was provided, so there is no basis for forecasting sales or promising that the redesign will convert.

### Recommendations in business order

| Priority | Recommendation | Why it matters / decision needed |
| --- | --- | --- |
| Before real traffic | Choose one clear customer segment and initial assortment; use real garment photos, verified measurements, materials and care instructions. | The current “heavyweight streetwear” positioning must match the actual inventory. The owner must confirm it; an agent cannot invent the offer. |
| Before orders | Agree delivery coverage/charges, dispatch timing, return eligibility/window, exchange costs and a working support channel. | Contradictory or unsupported promises create abandoned orders, complaints and expensive returns. Make the same policy visible before checkout and in support responses. |
| Before orders | Confirm supplier availability and who packs/ships a mixed-supplier basket. | The present original-shipment workflow should not be assumed to support independent supplier parcels. Start with an operation it can represent. |
| Before ads | Calculate contribution and available cash by product and delivery outcome. | Free shipping, supplier cost, courier deductions, failed deliveries, returns and ad spend can consume the retail margin. No spending target can be responsibly chosen without these inputs. |
| Before ads | Connect campaign visits to checkout attempts, accepted orders, deliveries and collected cash. | Existing order UTM attribution cannot explain all pre-order drop-off. Cheap clicks and many COD orders are insufficient evidence of profitable acquisition. |
| Pilot | Rehearse fulfillment/support, then run a small owner-budgeted acquisition experiment. | Compare actual outcomes with the assumptions; cap spend and daily order volume to what the owner can fulfill. |

Use a cohort worksheet: retained merchandise revenue after discounts/refunds + shipping charged − cost of goods consumed/lost − outbound and return courier costs − packaging/payment fees − other variable costs = contribution before advertising. Subtract campaign spend for contribution after advertising. Account for resellable returns without double-counting inventory cost. Track supplier payments and courier receivables separately for cash flow. This is an operating estimate, not the app's final accounting profit.

For a limited pilot, a maintained external supplier-payments ledger is acceptable: supplier, order reference, amount owed, due date, payment reference and remaining balance. Reconcile it daily. Build an internal payable ledger when volume or reconciliation errors justify it; never interpret wholesale-cost snapshots as proof a supplier has been paid.

Suggested research: observe five representative shoppers choosing a garment/size and explaining delivery/payment terms without coaching. This can reveal confusion; it is not statistical conversion proof. An IDE can test interactions but cannot establish customer demand or whether a real shopper trusts the offer.

## Role 2 — senior software engineer / architect

### Findings grounded in the implementation

| ID | Finding and evidence | Engineering recommendation |
| --- | --- | --- |
| E1 — confirmed | `frontend/src/components/ProductPage.js` reads `material_care` / `sizing_guide`, supplies a 240-GSM cotton fallback, and always renders one S–XL measurement table. Public `ProductDetailSchema` in `backend/app/schemas/catalog.py` exposes `material`, `care`, `sizing`. | Render the actual fields separately. Remove invented material/fit defaults and generic measurements. Show an honest unavailable state until owner-supplied data exists. Add a real table only with product-specific measurements. |
| E2 — confirmed content gap | The product page hardcodes a Karachi hub, 24–48-hour dispatch and seven-day exchange promise; checkout repeats the policy. `store-config.js` says shipping is calculated at checkout, while cart/checkout advertise free delivery. Privacy/terms links are null; support links point to page sections. | Owner supplies policy/contact decisions; centralize the approved copy. Validate working policy/contact destinations. Current zero shipping must be an intentional commercial choice, or replaced by server-calculated shipping. |
| E3 — confirmed interaction choice | `ProductPage.load()` selects the first available variant without a valid explicit variant URL. Tests currently expect this fallback. | For products requiring size selection, require a deliberate size choice before adding. A valid variant deep link may restore that choice. Update requirements/tests together; show clear selection guidance rather than a silent default. |
| E4 — code-review risks, browser reproduction pending | `ProductPage.load()` has no request generation/abort guard; related-product callbacks also mutate shared state. `app.js` detaches the product page on home navigation without calling its destroy method. Home navigation resets title but not product canonical/description. | Test slow A→B requests, delayed related results and product→home navigation. Guard stale callbacks, clean up gallery/video/listeners on route exit, and reset all route metadata. Do not claim these are browser-reproduced failures yet. |
| E5 — confirmed stack | `frontend/package.json` contains Vite and lucide, no React/Next.js. Docker builds `dist` and Caddy serves an SPA fallback. Product metadata is changed in browser JavaScript. | Label the Next.js record “evaluated, not migrated.” An unavailable-product screen does not establish an HTTP 404. Check deployed response status and initial HTML separately. |
| E6 — confirmed acceptance limits | U5 calls `Emulation.setPageScaleFactor`, then checks element presence/enabled state. Its matrix JSON records `titleVisible: false` at 360px and zero gallery/detail percentages at 1280px while passing. Admin checks assert title/password-field presence. U4 bank check stops at the pending-confirmation message. | Repair assertions and selectors; distinguish measurement errors from real layout bugs. Verify actual desktop zoom, authenticated admin actions and bank handoff/verification/dispatch. Empty-cart keyboard wrapping has evidence; it does not cover every overlay transition. |
| E7 — confirmed release gap | `backend/app/config.py:checkout_enabled` permits only the isolated test configuration. Customer-order DTO construction omits shipping, whose service default is zero. | Keep existing restrictions. A production release needs a separately designed default-off mechanism and acceptance, not relabeling production as test or weakening the lab guard. |
| E8 — inspected scope | UTM capture and marketing reporting exist; source search found no storefront Pixel/GA event instrumentation. Inspected finance models cover courier settlements/refund payments, not supplier payables. | Add only necessary funnel measurement; use a documented external payable ledger initially if chosen. These are distinct gaps, not reasons to rebuild the commerce backend. |

### Customer journey: review of supplied screenshots

These are Antigravity's supplied lab captures, inspected now; they are not fresh captures or production-catalog evidence. Fixture images are appropriate in the lab and cannot establish photographic quality for launch.

1. **Arrival — needs content acceptance.** Mobile home has a readable hierarchy, but the captured first screen is occupied by an empty-featured notice and a long text hero, with no garment visible. Use real managed imagery and let shoppers reach products sooner. Preserve the lab warning.

   ![Supplied mobile homepage](../.local/frontend-redesign/run_u5_matrix/u5_viewport_390_home.png)

2. **Product decision — functional structure, information gaps.** Price/options/CTA are visible, but the screenshot exposes generic material claims. The desktop details pane has a separate scrollbar (`product-page.css` sets sticky max-height/overflow). Test a single page scroll and shorter summary before retaining nested scrolling.

   ![Supplied desktop product page](../.local/frontend-redesign/run_u3_gallery/u3_desktop_product_details.png)

3. **Cart → checkout — usable summary, obstruction concern.** Quantity and exact subtotal are clear. The lab warning overlaps the cart header/close area in this capture. Reproduce and fix overlay offsets while retaining the warning. Check mobile occupied-cart → checkout focus and keyboard behavior.

   ![Supplied occupied cart](../.local/frontend-redesign/run_u4_checkout/u4_cart_drawer_with_item.png)

4. **Payment → fulfillment → after-sales — partially evidenced.** U4 records order placement and pending bank guidance. It does not freshly prove supplier acceptance, instruction handoff, received-funds verification, delivery, COD settlement or a completed return/refund. Reuse the existing M-phase workflows for a targeted regression after frontend changes.

### Next.js decision

**Defer migration until E1–E6 are resolved or reproduced; then make one bounded rendering decision.** If organic discovery is a near-term channel, Next.js with React is a reasonable option for public product/collection pages. If the immediate objective is a small paid-traffic pilot, current Vite can remain while launch blockers are closed. This sequencing changes with business priorities; neither framework guarantees orders.

For migration, retain FastAPI/PostgreSQL and the same-origin API. Prove one product route in a branch first: product content in initial HTML, correct metadata/status codes, hydration, cart continuity, API cookies/CSRF, assets and container restart. Start with explicit freshness behavior; cache public data only with tested invalidation. Never cache private order/session responses publicly. Retain working admin integration and a rollback route. Expand only after parity. Next.js self-hosting requires attention to proxying and cache behavior: [official deployment guidance](https://nextjs.org/docs/app/guides/self-hosting).

Regardless of framework, implement accurate Product data, canonical URLs, discoverable links and a sitemap of public pages. Structured data must agree with visible products: [Google ecommerce guidance](https://developers.google.com/search/docs/specialty/ecommerce/include-structured-data-relevant-to-ecommerce). Google says its AI search features use the same SEO foundations and need no special AI files; this is not a guarantee for Google or other AI services: [Google AI search guidance](https://developers.google.com/search/docs/appearance/ai-features).

## Joint meeting: decisions translated into phases

| Phase / owner | Agreed scope | Exit evidence |
| --- | --- | --- |
| B0 — owner + agent | Record customer/assortment, real product facts, coverage/fees, return rules, dispatch responsibility, support channel, supplier settlement and pilot budget. Agent lists unknowns instead of inventing answers. | Short approved commercial decision sheet; initial products have actual photos, material/care/sizing and supported variants. |
| B1 — frontend engineer | Fix E1/E2/E3; reproduce and fix E4; improve the three captured journey concerns. Keep the visual system. Independent correctness fixes can start while B0 decisions are pending. | Tests cover real API fields, missing data, deliberate size choice, rapid navigation and metadata cleanup; mobile/desktop screenshots of real approved content; existing regressions/build pass. |
| B2 — verification engineer | Repair E6 evidence and rerun affected flows on the current build. | True 200% desktop zoom with no lost controls/content; accurate measurements at all five widths; occupied-cart/checkout focus; actual admin login/edit; bank handoff through verified dispatch; COD and return/refund regression. Save commands, assertions, screenshots and NOT TESTED items. |
| B3 — architect, conditional | Decide Vite retention versus bounded Next.js migration; complete search essentials either way. | Written decision and current stack record; production-container deep links, correct response codes, metadata/structured data, fresh published prices/stock, no private-page indexing or shared private cache. |
| B4 — backend/operations + owner | Implement chosen shipping/release changes; configure real policies/support/payments; stage production packaging, backup/restore and rollback; establish supplier ledger. | HTTPS staging acceptance, restored DB+media check, restart persistence, permissions, no secret leakage, checkout close/reopen behavior and operational rehearsal. Public release still requires the owner's decision. |
| B5 — growth + owner | Add minimal measurement, then a capped pilot after B4. Use product-specific ad landing pages and consistent creative/price promises. | Deduplicated events, campaign/order matching and weekly delivery, settlement, return and contribution review. Expand only when data and operating capacity support it. |

B2 must verify resize behavior rather than equating page-scale emulation with desktop zoom; W3C's requirement concerns preserving content and functionality at enlarged text: [resize-text guidance](https://www.w3.org/WAI/WCAG22/Understanding/resize-text.html).

For B5, define events such as product view, add to cart, checkout start, accepted order and checkout failure. Emit accepted-order once per successful order, not per button click. Keep delivered/settled results separate from order creation, especially for COD. Exclude lab/staff traffic and private access codes, contact details and payment evidence. Select analytics/advertising integrations deliberately and document data handling before activation.

Review weekly: product-view→cart, cart→checkout, checkout→accepted-order rates with explicit denominators; delivery/retention rates by order cohort; campaign spend per retained customer; outstanding courier cash/supplier balances; and contribution after advertising. Set targets after establishing a baseline. Stop scaling if funds are unreconciled, stock promises fail, service capacity is exceeded or contribution is negative beyond the agreed experiment budget.

## Do now / defer / avoid

**Now:** B0 decisions plus B1 correctness work, then targeted B2 acceptance. Preserve the current backend and completed design work.

**Defer:** vendor portal, mobile app, loyalty program, AI shopping assistant, automated courier integrations, complex recommendations, multi-vendor split shipments and a major accounting subsystem unless actual operations demand them. Reconsider with observed demand or recurring manual errors.

**Avoid:** another full redesign to postpone launch decisions; fabricated reviews or product promises; a framework migration justified only by “better SEO”; changing tests merely to keep them green; scaling Meta ads before ordering, fulfillment and measurement are ready.

**Next instruction to Antigravity:** read this file and the canonical `.agent/AGENTS.md`; implement B1's independent correctness fixes with targeted tests, list the B0 inputs needed from the owner, and return evidence before starting a framework migration or production release. This document itself authorizes no new implementation or external spending.
