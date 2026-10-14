# Owner catalog milestone browser acceptance

Created during M0 (2026-10-14). Updated after M1: direct dashboard/session/navigation
checks passed in isolated headless Chrome; catalog and commerce journeys remain
pending. See `m1_dashboard_runbook.md`. Use only an isolated browser
database/media environment established in M8, never the private backup restore.

For each row record date, environment, viewport, result, screenshot/trace path
and observed Console/Network errors. Redact passwords, access codes, CSRF tokens,
payment evidence and personal information. Screenshots must use SAMPLE assets.

| Check | Expected outcome | State |
| --- | --- | --- |
| Direct `/admin` + valid/invalid login | Correct login/dashboard, no private flash, usable errors | M1 Chrome valid login passed; invalid login covered by API/Node tests |
| Sections, deep link, refresh/back/forward | Correct section and restored owner session | M1 passed; later authoring sections remain placeholders |
| Collection + incomplete draft | Saved without SQL; draft absent publicly | Pending |
| Variants/PKR/duplicate validation | Exact fractional price; clear duplicate/missing field errors | Pending |
| Image/video upload, gallery, poster | Valid files preview/play; progress/errors truthful | Pending |
| Unsupported/oversize/failed upload | Rejected; no broken references or false success | Pending |
| Supplier/cost/stock + publish | Existing audit services; readiness reasons then public listing | Pending |
| Storefront/gallery/variant/cart | Real saved data and media; stock gating correct | Pending |
| Edit/reload + container restart/rebuild | Description/price/primary image and files persist | Pending |
| COD checkout/lost response | One order/hold; private code issued and replay safe | Pending |
| Owner hold links + supplier acceptance | Individual holds sum correctly; order opens | Pending |
| COD dispatch/delivery/settlement/report | Stock deducted once; cash/held COD reconciles | Pending |
| Simulated bank handoff/proof/verification | Supplier first; four-hour window; screenshot not cleared funds | Pending |
| Expiry review + cancellation | Explicit review; eligible release once | Pending |
| Refund/return/RTO inspection | Sellable only restocks; paid refund is separate evidence | Pending |
| Size exchange/replacement | Separate reservation/shipment; original snapshots preserved | Pending |
| Archive purchased product | Public sale hidden; history/return/report survives | Pending |
| Logout/expiry/unauthorized mutation | Server rejects; UI returns to login | M1 Chrome logout/expiry and post-logout owner GET rejection passed; API tests cover protected mutations |
| Simultaneous normal/test sessions | Cookies/storage independent; normal checkout remains 503 | Pending |
| Offline, keyboard, desktop/mobile | Recoverable errors; no stuck overlays/clipped essential controls | M1 desktop/mobile screenshots inspected; keyboard/offline guards Node-tested; full catalog/commerce layouts pending |

M1 implements `/admin`; uploads and the checkout lab remain pending. Final manual commands
and detailed steps will be supplied from the implemented runtime in M9. If browser
automation is unavailable then, record the reason and actual manual results;
unit tests alone cannot mark this checklist passed.
