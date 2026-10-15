# Owner catalog milestone browser acceptance

Created during M0 (2026-10-14). Final M9 update (2026-10-15): dashboard,
catalog, storefront, owner operations, mobile checkout and purchased-history acceptance passed in isolated headless Chrome.
See `m9_browser_verification.json` (145 checks), `m9_catalog_browser_verification.json` (83 checks), `m9_runtime_verification.json` and `m9_owner_handoff.md`.
Tests copy selected SAMPLE catalog/media from the separate M3 acceptance source into the independent checkout lab. Never use the private development backup restore as a browser fixture.

For each row record date, environment, viewport, result, screenshot/trace path
and observed Console/Network errors. Redact passwords, access codes, CSRF tokens,
payment evidence and personal information. Screenshots must use SAMPLE assets.

| Check | Expected outcome | State |
| --- | --- | --- |
| Direct `/admin` + valid/invalid login | Correct login/dashboard, no private flash, usable errors | M1 Chrome valid login passed; invalid login covered by API/Node tests |
| Sections, deep link, refresh/back/forward | Correct section and restored owner session | M1 passed; M4 authoring routes and refresh passed |
| Collection + incomplete draft | Saved without SQL; draft absent publicly | M4 Chrome creation passed; public draft rejection API-tested |
| Variants/PKR/duplicate validation | Exact fractional price; clear duplicate/missing field errors | M4 Chrome fractional price passed; duplicate/missing fields API/Node-tested |
| Image/video upload, gallery, poster | Valid files preview/play; progress/errors truthful | M4 Chrome multiple uploads, poster, primary/hero/gallery and actual video playback passed |
| Unsupported/oversize/failed upload | Rejected; no broken references or false success | M4 corrupt-image error/retry UI passed; format/byte/pixel/duration limits API/runtime-tested |
| Supplier/cost/stock + publish | Existing audit services; readiness reasons then public listing | M5 Chrome registration/exact cost/receipt, zero/multiple/legacy holds, filtered order link, supplier history and public eligibility passed; pagination/version/conflict/lifecycle regressions API/Node-tested |
| Storefront/gallery/variant/cart | Real saved data and media; stock gating correct | M6 Chrome managed cards/hero/cover, real gallery playback, variant media/stock, checkout images, owner-edit refresh, slug/price recovery and inactive/unpublished/archive gating passed; 83 checks total with zero unexpected errors |
| Edit/reload + container restart/rebuild | Description/price/primary image and files persist | M4 Chrome edit/refresh passed; M3 Docker byte checksums and associations survive restart/recreation/matched restore |
| Concurrent edit conflict | Preserve input; explicit reload/review | M4 Chrome stale-version rejection and recovery passed; atomic rollback API/Node-tested |
| COD checkout/lost response | One order/hold; private code issued and replay safe | M8 actual customer form, simulated lost response/retry, identical order/attempt key, exact 2-unit hold and private tracking passed |
| Owner hold links + supplier acceptance | Individual holds sum correctly; order opens | M5/M6 hold links passed; M7 direct private order, supplier acceptance and payment flow passed |
| COD dispatch/delivery/settlement/report | Stock deducted once; cash/held COD reconciles | M9 real customer COD checkout, exact hold, delivery, partial PKR 100 receipt and final remaining receipt passed; runtime stock/hold triples preserved across restart |
| Simulated bank handoff/proof/verification | Supplier first; four-hour window; screenshot not cleared funds | M8 real customer bank checkout, supplier acceptance, simulated handoff, tracking proof form and explicit simulated funds checkbox passed; proof stayed pending until verification |
| Expiry review + cancellation | Explicit review; eligible release once | M7 read-only order opening, explicit expiry flag/review/release and pre-dispatch cancellation passed |
| Refund/return/RTO inspection | Sellable only restocks; paid refund is separate evidence | M9 customer-requested refund/receipt/inspection/liability/payment passed; replacement RTO receipt stays quarantined until inspection, restocks once and then hides its completed action. Original RTO also passed in M7 |
| Size exchange/replacement | Separate reservation/shipment; original snapshots preserved | M9 customer exchange options/request, original receipt/inspection, replacement delivery and separate replacement RTO passed; original snapshots and final stock preserved |
| Archive purchased product | Public sale hidden; history/return/report survives | M9 dashboard archive, public slug/stable-ID 404 and card removal passed; exact original order/returns/financial-summary comparison unchanged; private customer tracking works after archive |
| Logout/expiry/unauthorized mutation | Server rejects; UI returns to login | M1 Chrome logout/expiry and post-logout owner GET rejection passed; API tests cover protected mutations |
| Simultaneous normal/test sessions | Cookies/storage independent; normal checkout remains 503 | M8 valid non-lab SAMPLE source and lab sessions coexist on one cookie host; distinct owner/order/checkout names, cross-DB token rejection and lab logout preserving the non-lab cookie passed. Real development owner credentials were not used; normal checkout remains closed |
| Offline, keyboard, desktop/mobile | Recoverable errors; no stuck overlays/clipped essential controls | M9 phone checkout scroll/submit target/focus, deliberate offline failure with retained input and successful retry, contained private-order table and stacked report cards passed. M6 authoring/gallery/playback checks reran on Vite 7. Desktop/mobile screenshots inspected |

M0–M9 are complete locally. Final M9 execution recorded 228 browser checks with no unexpected JavaScript or network failures. Four intentional 401/404 observations and one deliberate offline checkout-session failure are separately logged. Archived media/posters, five SAMPLE order states and exact stock/holds survive lab restart. Exact owner startup, first-product, import, payment and backup instructions are in `m9_owner_handoff.md`; repeat acceptance commands are in `m9_implementation_report.md`. Public deployment/ordering remain separate.
