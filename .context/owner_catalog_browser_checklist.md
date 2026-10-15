# Owner catalog milestone browser acceptance

Created during M0 (2026-10-14). Updated through M8 (2026-10-15): dashboard,
catalog, storefront, owner operations and lab customer checkout passed in isolated headless Chrome.
See `m8_browser_verification.json`, `m8_runtime_verification.json` and `m8_checkout_lab_runbook.md`.
M8 copies selected SAMPLE catalog/media from the separate M3 acceptance source into its own checkout-lab database/volume. Never use the private development backup restore as a browser fixture.

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
| COD dispatch/delivery/settlement/report | Stock deducted once; cash/held COD reconciles | M7 owner transitions passed; M8 customer-created COD order dispatch, delivery, full settlement and report passed; final stock balances verified across restart |
| Simulated bank handoff/proof/verification | Supplier first; four-hour window; screenshot not cleared funds | M8 real customer bank checkout, supplier acceptance, simulated handoff, tracking proof form and explicit simulated funds checkbox passed; proof stayed pending until verification |
| Expiry review + cancellation | Explicit review; eligible release once | M7 read-only order opening, explicit expiry flag/review/release and pre-dispatch cancellation passed |
| Refund/return/RTO inspection | Sellable only restocks; paid refund is separate evidence | M7 receipt, inspection, completed refund liability, separate paid refund/history and original RTO passed; stock invariants API-tested |
| Size exchange/replacement | Separate reservation/shipment; original snapshots preserved | M7 approval, receipt/inspection, replacement dispatch/transit/delivery and separate charge settlement passed; original snapshot invariants API-tested |
| Archive purchased product | Public sale hidden; history/return/report survives | M4 sample archive/public 404 passed; purchased-history browser journey remains pending |
| Logout/expiry/unauthorized mutation | Server rejects; UI returns to login | M1 Chrome logout/expiry and post-logout owner GET rejection passed; API tests cover protected mutations |
| Simultaneous normal/test sessions | Cookies/storage independent; normal checkout remains 503 | M8 valid non-lab SAMPLE source and lab sessions coexist on one cookie host; distinct owner/order/checkout names, cross-DB token rejection and lab logout preserving the non-lab cookie passed. Real development owner credentials were not used; normal checkout remains closed |
| Offline, keyboard, desktop/mobile | Recoverable errors; no stuck overlays/clipped essential controls | M4 keyboard/gallery/error checks passed; M7 desktop Reports screenshot inspected and mobile Orders no page overflow passed; checkout lab layouts pending |

M0–M8 are complete. M9 remains pending. M8 recorded 98 Chrome checks with no unexpected JavaScript errors, and runtime snapshots preserve imported media/posters, orders and final stock across restart. Broader mobile checkout and purchased-product archive/history acceptance remain for M9. Final manual commands
and detailed steps will be supplied from the implemented runtime in M9. If browser
automation is unavailable then, record the reason and actual manual results;
unit tests alone cannot mark this checklist passed.
