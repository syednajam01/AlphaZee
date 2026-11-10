# Vendor stock matrix

Implemented the approved `problems/p3_vendor_portal_matrix_redesign.md` brief for `/vendor`.

## What changed

- Stock is grouped by stable product ID and color, with sizes in compact desktop tables and touch-friendly mobile rows. Identically named products remain separate.
- Each size shows SKU, the vendor's agreed wholesale unit cost, physical stock, customer holds and authoritative available stock. Retail prices, margins and customer information remain excluded.
- Vendors enter **new physical totals**, rather than quantities sold. Inline steppers, individual Save and **Save all sizes for [color]** are available. Detailed count notes, shortage reporting and history remain accessible.
- A group save sends only changed, valid counts through the existing version-checked API. Saves are sequential and independent, not an atomic transaction. Successful sizes stay saved; failed sizes retain edits for retry. Conflicts require reviewing the latest recorded count.
- Counts below holds require confirmation. The backend records a shortage for review without reducing recorded stock below protected holds. The interface distinguishes a reported shortage from a saved stock count.
- Unsaved counts survive search, pagination and refresh within the open portal. They clear on browser reload, logout or session expiry. Discarding all edits requires confirmation. Each group saves only sizes shown on the current page; pagination may split groups.
- Visible tabs refresh every 30 seconds and on focus. Successful stock writes send a data-free notification to other local tabs. This is polling/shared-database synchronization, not WebSocket push. Dialog notes and focused edits survive background requests.
- Session expiry stops the remaining batch. Stale responses cannot restore private stock after logout or portal destruction. Empty pages caused by changing inventory offer a return to page one.

## Code

`VendorPortal.js` coordinates sessions, refresh, dialogs and saving. `VendorStockMatrix.js` renders the matrix; `utils/vendorMatrix.js` owns grouping, validation and draft state. Existing backend contracts and database schema are unchanged. Existing React navbar and admin Collections changes are preserved; a full vendor framework migration was unnecessary.

## Verification

Terminal verification uses disposable PostgreSQL databases and browser-only SAMPLE API fixtures, never production stock or real customer orders.

- Backend: **342 passed**; isolated migration upgrade/downgrade/re-upgrade and vendor-finance migration verification passed.
- Frontend: **157 passed** in the Node 22 Linux development image, including delayed-search/dialog and background-refresh regressions; production build passed.
- Operations: **29 passed**; isolated database/media restore, workflow policy, actionlint and production Compose packaging passed.
- Production-image browser checks passed for the storefront, mobile admin and React navbar. The vendor matrix passed Chromium and WebKit at 390/768/1440px, including cost privacy, duplicate product names, validation, partial retry, version conflicts, shortage confirmation, preserved holds, notes/history, drafts, pagination recovery and session cleanup.

CI and release workflows now run `ops/vendor_matrix_smoke.cjs` alongside existing storefront, admin-mobile and navbar smoke tests. Fixture state stays entirely inside the browser test.

Design retains the established stockroom palette and existing unslop attribution: Damir Sokolovsky, CC BY 4.0; see the vendor stylesheet credit.
