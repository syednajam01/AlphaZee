# Frontend control inventory — Phase L1

Updated 2026-10-13 through Phase L2. Verification is **terminal only**, as explicitly requested by the owner. No browser was launched and no browser result is claimed for any row.

Evidence labels: **DOM** = actual component construction/events exercised against the repository's Node DOM fixture, with mocked fetch; **unit** = existing unit/API-client tests; **HTTP** = live terminal requests to Vite/FastAPI; **source** = inspected implementation only. These do not establish visual layout, pointer hit-testing, touch behavior or complete persisted commerce journeys.

## Storefront shell and browsing

| Location / selector | Intended action and wiring | Endpoint | Current classification / evidence | Persistence expectation |
| --- | --- | --- | --- | --- |
| Header/footer logo `.brand-logo-link` | Native `#` home/top link | None | Implemented; source | None |
| Header Shop/Collections/About/FAQ links | Native anchors to existing sections | None | Implemented; source | None |
| Header `#btn-browse-catalog` | Scroll to `#featured`; renamed from misleading search action | None | Repaired; DOM | None |
| Header `#btn-cart` | Open cart drawer | Catalog reconciliation on open | Repaired overlay behavior; DOM | Cart items retained |
| Header `#btn-mobile-menu` | Open mobile menu and update expanded state | None | Repaired; DOM | None |
| Mobile `#mobile-nav-close-btn`, backdrop | Close menu, restore focus/scroll | None | Repaired; shared overlay + DOM | None |
| Mobile section links / logo | Close drawer and navigate to section/top | None | Implemented; source, shared close path tested | None |
| Header `#nav-track-order`, mobile/footer `a[href="#track"]` | All open the same tracking dialog | Lookup only on submit | Repaired; all three DOM-tested | Form state in current page |
| Footer All Products | Native `#featured` anchor; removed missing `#shop` target | None | Repaired; DOM checks missing old link | None |
| Footer Collections/New Arrivals/FAQ/Delivery/Inquiries | Native links to existing sections | None | Implemented; source | None |
| Footer Privacy/Terms | Display unavailable text without dead anchors | None | Intentionally disabled; DOM/source | None; requires approved content |
| Mobile/footer support buttons | Explain contact is unavailable; no placeholder WhatsApp destination | None | Intentionally disabled; DOM/source | None; requires real contact |
| FAQ `.faq-question` | Expand selected answer, collapse others, update aria-expanded | None | Implemented; DOM | Current page only |
| Hero fallback Explore Collection | Native `#featured` anchor | None | Implemented; offline fallback mounted in DOM | None |
| Hero `.hero-cta-btn` | Open corresponding product | GET `/products/{slug}` if needed | Implemented; existing hero/unit tests + source | None |
| Hero `#hero-prev`, `#hero-next` | Cycle slides | None | Implemented; existing hero tests; sample multi-slide browser flow not run | None |
| Hero View All link | Native `#featured` anchor | None | Implemented; source | None |
| Collections `.collection-card` | Set catalog collection filter and scroll | GET `/products?collection_id=...` | Implemented; DOM recovery/filter test | Current page only |
| Collections `.btn-retry` | Reload collections after failure | GET `/collections` | Implemented; DOM offline-to-online recovery | None |
| Catalog `[data-filter]` tabs | Change collection and reload page one | GET `/products` | Implemented; pagination/filter unit tests | Current page only |
| Catalog `#btn-load-more` | Load next page, discard stale results | GET `/products?page=...` | Implemented; pagination unit tests | Current page only |
| Catalog `.btn-retry` | Retry failed product request | GET `/products` | Implemented; DOM recovery | None |
| Catalog `.product-card-btn` | Open product details | GET `/products/{slug}` if card lacks variants | Implemented; DOM | None |

## Product, cart and checkout

| Location / selector | Intended action and wiring | Endpoint | Current classification / evidence | Persistence expectation |
| --- | --- | --- | --- | --- |
| Product `[data-size]`, `[data-color]` | Select actual variant; reject unavailable combinations | None | Implemented; size DOM test, variant unit tests | Choice in current dialog |
| Product `#btn-modal-add-to-cart` | Add selected variant and open cart | Local cart; GET product on reconciliation | Implemented; DOM, unit | Local storage; existing persistence unit tests |
| Product image | Static product image, no gallery action promised | Image URL | Implemented display; source | None |
| Product `#modal-close-btn`, error close, backdrop | Dismiss product and invalidate outstanding fetch | None | Repaired overlay lifecycle; DOM/unit | Cart preserved |
| Cart `.btn-qty-inc`, `.btn-qty-dec` | Update quantity and totals | Local cart | Implemented; DOM | Local storage |
| Cart `.btn-remove-item` | Remove line and update badge/totals | Local cart | Implemented; DOM | Local storage |
| Cart `#cart-close-btn`, `#cart-drawer-backdrop` | Dismiss, restore focus/scroll | None | Repaired; DOM | Cart preserved |
| Cart `#btn-checkout` | Open checkout only if server permits it and cart is valid | GET `/storefront/capabilities` | Intentionally disabled publicly; DOM + live HTTP | Cart preserved |
| Checkout `#checkout-close-btn`, backdrop | Dismiss checkout | None | Shared repaired overlay; constructed/closed state DOM-tested | Cart preserved |
| Checkout inputs / payment radios | Validate customer details; offer bank transfer only when capability permits | GET `/storefront/capabilities` | Phase C bank option gated by validated API methods; public entry disabled | Current page only |
| Checkout `#btn-apply-coupon` | Validate coupon and recalculate display | POST `/coupons/validate` | Existing handler; API-client unit; full DOM submission pending | Order snapshot only on later submit |
| Checkout `#checkout-form`, `#btn-place-order` | Submit or recover an order | GET `/orders/checkout-session`, POST `/orders` | Phase B idempotency and lost-response recovery implemented and tested in isolated PostgreSQL/Node; publicly gated with live HTTP 503 | Pending key/payload in tab storage; order and holds in test database |
| Confirmation `#btn-finish-checkout` | Close completed checkout; a later visit restores a fresh form | None | Handler and form reset implemented; source/Node tests, browser journey pending | Order remains on server |
| Confirmation receipt form | Submit payment-proof URL/reference only after instructions | POST `/orders/{number}/receipt` | Phase C hides proof form until successful handoff; backend rejects earlier uploads | Receipt on server |
| All live dialogs: Escape/Tab/close | Hide/inert closed roots, trap focus, restore opener and scroll, allow one active dialog | None | Repaired; dedicated overlay DOM tests | None |

## Tracking and owner console

| Location / selector | Intended action and wiring | Endpoint | Current classification / evidence | Persistence expectation / next phase |
| --- | --- | --- | --- | --- |
| Tracking `#tracking-search-form`, `#btn-search-order` | Access an order with its private code/session | GET `/orders/{number}` and code exchange | Phase G order-scoped access; backend security tests; browser journey unverified | Order-scoped session |
| Tracking `#tracking-close-btn`, backdrop | Dismiss tracking | None | Repaired; DOM | Current form inputs retained |
| Tracking courier link | Open supplied tracking URL | External courier | Existing conditional link; source only | None |
| Tracking `#btn-toggle-return-form` | Show/hide return request panel | None | Existing handler; source | Current page only |
| Tracking return type/line/reason/notes + submit | Request return or size exchange | POST `/returns/request` | Phase G access and replacement allocation backed by API tests; browser journey unverified | Return/replacement on server |
| Tracking payment-proof form | Show sent bank snapshot/deadline and submit proof after handoff | POST `/orders/{number}/receipt` | Gated by handoff and Phase G order-scoped session; backend tests | Receipt on server |
| Footer `a[href="#admin"]` | Open owner console and restore session | GET `/auth/session`, then active admin tab | Shell/session DOM tests; anonymous HTTP access 401 | PostgreSQL session survives API restart |
| Owner `#admin-auth-form` | Username/password sign-in | POST `/auth/login` | Implemented Phase A; inline errors and password clearing tested in DOM; real HTTP login passed | HttpOnly cookie; no shared key in storage |
| Owner `#btn-admin-logout` | Revoke session and return to login | POST `/auth/logout` with CSRF token | Implemented Phase A; successful/failed logout DOM tests; real HTTP revocation passed | Stolen/replayed cookie rejected after logout |
| Owner `#btn-toggle-admin-sidebar` | Collapse/expand sidebar | None | Existing handler; source | Current page only |
| Owner `.admin-tab-btn` | Switch overview/orders/inventory/coupons/returns/suppliers/analytics | GET matching `/admin/*` endpoint | Existing handlers; source | Read-only tab load; not exercised with real credentials |
| Owner `#btn-refresh-admin-tab` | Retry/reload active tab | GET matching endpoint | Existing handler; source | Reads latest server state |
| Owner `#admin-close-btn`, backdrop | Close console and any nested forms | None | Repaired; DOM | No server mutation |
| Order `.btn-verify-payment` | Verify received funds outside expired review | POST `/admin/orders/{id}/verify-payment` | Phase C lock/deadline guard and owner identity tested | Payment audit on server |
| Order `.btn-confirm-supplier` | Record supplier acceptance only with complete allocations | POST `/admin/orders/{id}/confirm-supplier` | Phase C allocation guard tested | Supplier audit on server |
| Order `.btn-prepare-instructions` | Preview bank account, then explicitly record successful customer handoff | GET `/admin/orders/{id}/payment-instructions-preview`; POST `/instructions-sent` | Phase C owner form and backend integration tested; no browser exercise | Handoff snapshot and UTC deadline on server |
| Order `#btn-review-expired-orders`, `.btn-resolve-payment` | Flag expired orders and decide after checking funds | POST `/admin/orders/review-expired`; POST `/orders/{id}/payment-review` | Phase C preserved holds and explicit release/verify tested | Review audit on server |
| Order `.btn-dispatch-order` | Open dispatch details form | None until submit | Implemented; owner DOM mutation test | Selected order retained in form |
| Dispatch `#admin-dispatch-form`, `#btn-submit-dispatch` | Book/dispatch shipment | POST `/admin/orders/{id}/dispatch` | Implemented with validation, one pending submit, failure retry and refreshed order; DOM test plus backend API lifecycle | Shipment/tracking on server |
| Dispatch `#btn-cancel-dispatch` | Dismiss nested form | None | Repaired; DOM | No mutation |
| Remittance form / `#btn-submit-remit` | Record courier settlement | POST `/admin/shipments/{id}/remittance` | Implemented in Phase F; DOM shell and backend reconciliation tests | Append-only settlement entries on server |
| Remittance `#btn-cancel-remit` | Dismiss nested form | None | Repaired; DOM | No mutation |
| Order `.btn-cancel-order` | Cancel eligible order | POST `/admin/orders/{id}/cancel` | Backend lifecycle tests and owner handler; browser journey unverified | Cancellation and released holds on server |
| Order `.btn-rto-order`, `.btn-rto-receive`, `.btn-rto-inspect` | Initiate/receive/inspect RTO | POST order RTO endpoints | Phase D/E quantity and stock tests; owner handlers; browser journey unverified | Inspection/stock records on server |
| Orders `#btn-review-expired-orders` | Explicitly flag expired bank payments for review | POST `/admin/orders/review-expired` | Phase C review API; no automatic mutation on tab read | Review state on server |
| Inventory tab | Display supplier/variant physical/held/available figures and adjust stock | GET `/admin/inventory/summary`; POST `/admin/inventory/adjust` | Implemented; optimistic version and held-stock guards; DOM and backend API tests | Stock event, balance and version on server |
| Coupons `#new-coupon-form`, `.btn-del-coupon` | Create/delete coupon | POST/DELETE `/admin/coupons` | Existing handlers and backend API tests; browser journey unverified | Server database write |
| Suppliers `#new-supplier-form` | Create supplier | POST `/admin/suppliers` | Existing handler and backend API tests; browser journey unverified | Server database write |
| Supplier-variant cost mapping | Assign supplier and wholesale cost to catalog variant | GET `/admin/catalog/variants`; POST `/admin/suppliers/{id}/variants` | Implemented; owner catalog includes unmapped variants; DOM and backend read tests | Supplier mapping/cost on server |
| Returns `.btn-approve-ret`, `.btn-reject-ret`, `.btn-complete-ret`, `.btn-record-refund` | Approve/reject/complete return, then record actual refund payment | POST `/admin/returns/{id}/...` | Phase D/G/F backend tests and owner handlers; browser journey unverified | Return, replacement and refund evidence on server |
| Delivery/status update | Set in-transit, out-for-delivery or delivered status | POST `/admin/shipments/{id}/status` | Implemented; delivery DOM and backend lifecycle tests | Shipment status and allocation on server |
| Analytics | Read operational sales/cash reconciliation and marketing reports | GET profit-loss and marketing endpoints | Phase F accounting fixtures; terminal-tested only; operational estimate, not a tax export | Current database snapshot |

`AdminPreview.js` is not imported by the running app and is not a second live console. Its controls are excluded from the live register.

## Remaining verification

- No browser Console, visual viewport, pointer hit-test, touch or layout evidence was collected, per the owner's instruction.
- DOM fixtures exercise event wiring and state, not browser rendering. The hidden-root fix is supported by explicit `hidden`/`inert` states plus CSS `display:none !important` for closed roots, but the owner's exact browser symptom has not been independently reproduced visually.
- Live catalog responses are empty. Product recovery tests use in-memory SAMPLE / TEST fixtures, not fabricated development catalog entries.
- During Phase V, PostgreSQL-backed API tests exercised owner and customer mutations in isolated `_test` databases. The development-stack HTTP smoke checks performed no successful owner mutations or customer order submissions; public checkout remained disabled. Browser persistence remains unverified.
