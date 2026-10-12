# Frontend control inventory — Phase L1

Updated 2026-10-13. Verification is **terminal only**, as explicitly requested by the owner. No browser was launched and no browser result is claimed for any row.

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
| Checkout inputs / payment radios | Validate customer details; select payment | None until submit | Existing handlers; source/unit; public entry disabled | Current page only |
| Checkout `#btn-apply-coupon` | Validate coupon and recalculate display | POST `/coupons/validate` | Existing handler; API-client unit; full DOM submission pending | Order snapshot only on later submit |
| Checkout `#checkout-form`, `#btn-place-order` | Submit or recover an order | GET `/orders/checkout-session`, POST `/orders` | Phase B idempotency and lost-response recovery implemented and tested in isolated PostgreSQL/Node; publicly gated with live HTTP 503 | Pending key/payload in tab storage; order and holds in test database |
| Confirmation `#btn-finish-checkout` | Close completed checkout; a later visit restores a fresh form | None | Handler and form reset implemented; source/Node tests, browser journey pending | Order remains on server |
| Confirmation receipt form | Submit payment-proof URL/reference | POST `/orders/{number}/receipt` | Existing handler; unit/source; payment corrections Phase C | Receipt on server; not exercised here |
| All live dialogs: Escape/Tab/close | Hide/inert closed roots, trap focus, restore opener and scroll, allow one active dialog | None | Repaired; dedicated overlay DOM tests | None |

## Tracking and owner console

| Location / selector | Intended action and wiring | Endpoint | Current classification / evidence | Persistence expectation / next phase |
| --- | --- | --- | --- | --- |
| Tracking `#tracking-search-form`, `#btn-search-order` | Lookup entered order/phone | GET `/orders/{number}` | Existing handler; API-client unit/source | Secure access replacement in Phase G; real lookup not exercised |
| Tracking `#tracking-close-btn`, backdrop | Dismiss tracking | None | Repaired; DOM | Current form inputs retained |
| Tracking courier link | Open supplied tracking URL | External courier | Existing conditional link; source only | None |
| Tracking `#btn-toggle-return-form` | Show/hide return request panel | None | Existing handler; source | Current page only |
| Tracking return type/line/reason/notes + submit | Request return | POST `/returns/request` | Existing handler, incomplete secure ownership/exchange selection; unit/source | Phase G; no customer writes exercised |
| Tracking payment-proof form | Submit receipt URL/reference | POST `/orders/{number}/receipt` | Existing handler; unit/source | Phase C/G; no customer writes exercised |
| Footer `a[href="#admin"]` | Open owner console and restore session | GET `/auth/session`, then active admin tab | Shell/session DOM tests; anonymous HTTP access 401 | PostgreSQL session survives API restart |
| Owner `#admin-auth-form` | Username/password sign-in | POST `/auth/login` | Implemented Phase A; inline errors and password clearing tested in DOM; real HTTP login passed | HttpOnly cookie; no shared key in storage |
| Owner `#btn-admin-logout` | Revoke session and return to login | POST `/auth/logout` with CSRF token | Implemented Phase A; successful/failed logout DOM tests; real HTTP revocation passed | Stolen/replayed cookie rejected after logout |
| Owner `#btn-toggle-admin-sidebar` | Collapse/expand sidebar | None | Existing handler; source | Current page only |
| Owner `.admin-tab-btn` | Switch overview/orders/inventory/coupons/returns/suppliers/analytics | GET matching `/admin/*` endpoint | Existing handlers; source | Read-only tab load; not exercised with real credentials |
| Owner `#btn-refresh-admin-tab` | Retry/reload active tab | GET matching endpoint | Existing handler; source | Reads latest server state |
| Owner `#admin-close-btn`, backdrop | Close console and any nested forms | None | Repaired; DOM | No server mutation |
| Order `.btn-verify-payment` | Verify funds | POST `/admin/orders/{id}/verify-payment` | Existing handler; error recovery incomplete; source/unit | Phase C/L2 |
| Order `.btn-confirm-supplier` | Record supplier acceptance | POST `/admin/orders/{id}/confirm-supplier` | Existing handler; source/unit | Phase C/D |
| Order `.btn-dispatch-order` | Open dispatch details form | None until submit | Existing opener; source | Fulfillment integration Phase D/L2 |
| Dispatch `#admin-dispatch-form`, `#btn-submit-dispatch` | Book/dispatch shipment | API client exists, submit integration unfinished | Now explicitly disabled; native submit prevented | Phase D/L2; no false success |
| Dispatch `#btn-cancel-dispatch` | Dismiss nested form | None | Repaired; DOM | No mutation |
| Remittance form / `#btn-submit-remit` | Record courier settlement | API client exists, submit integration unfinished | Now explicitly disabled; no currently wired opener; native submit prevented | Phase F/L2 |
| Remittance `#btn-cancel-remit` | Dismiss nested form | None | Repaired; DOM | No mutation |
| Order `.btn-cancel-order` | Cancel eligible order | POST `/admin/orders/{id}/cancel` | Existing handler; source/unit | Phase D lifecycle verification required |
| Order `.btn-rto-order`, `.btn-rto-receive`, `.btn-rto-inspect` | Initiate/receive/inspect RTO | POST order RTO endpoints | Existing handlers; corrected quantity lifecycle unfinished | Phase D/E; not exercised against development |
| Orders `#btn-purge-expired-orders` | Existing automatic expiry cancellation | POST `/admin/orders/cancel-expired` | Existing handler conflicts with required review behavior | Replace in Phase C; not executed |
| Inventory tab | Display physical/held/available figures | GET `/admin/inventory/summary` | Read-only implemented; adjustment UI absent | Stock adjustment interface Phase L2 |
| Coupons `#new-coupon-form`, `.btn-del-coupon` | Create/delete coupon | POST/DELETE `/admin/coupons` | Existing handlers; unit/source | Database writes not exercised |
| Suppliers `#new-supplier-form` | Create supplier | POST `/admin/suppliers` | Existing handler; unit/source | Database writes not exercised |
| Supplier-variant cost mapping | Assign supplier to variant | API client exists | UI unfinished; no live visible mapping control | Phase L2 |
| Returns `.btn-approve-ret`, `.btn-reject-ret`, `.btn-complete-ret` | Approve/reject/complete return | POST `/admin/returns/{id}/...` | Existing handlers; corrected inspected quantities/refund/exchange flow unfinished | Phase D/E/G/L2 |
| Delivery/status update | Change allocated shipment status | API client exists | Missing complete owner interaction | Phase D/L2 |
| Analytics | Read reports | GET profit-loss and marketing endpoints | Display implemented; accounting corrections pending | Phase F; not certified financial reports |

`AdminPreview.js` is not imported by the running app and is not a second live console. Its controls are excluded from the live register.

## Remaining verification

- No browser Console, visual viewport, pointer hit-test, touch or layout evidence was collected, per the owner's instruction.
- DOM fixtures exercise event wiring and state, not browser rendering. The hidden-root fix is supported by explicit `hidden`/`inert` states plus CSS `display:none !important` for closed roots, but the owner's exact browser symptom has not been independently reproduced visually.
- Live catalog responses are empty. Product recovery tests use in-memory SAMPLE / TEST fixtures, not fabricated development catalog entries.
- No owner mutations or customer orders were submitted successfully during L1. Database persistence for those operations remains assigned to the later integration phases.
