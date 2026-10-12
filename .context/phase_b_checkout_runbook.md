# Phase B: checkout attempts and stock concurrency

Implemented 2026-10-13. Public checkout remains disabled. The working checkout path is available only in the isolated test configuration (`APP_ENV=test`, a loopback `_test` database, and `TEST_CHECKOUT_ENABLED=true`). No browser was used for verification.

## Checkout contract

1. `GET /api/v1/orders/checkout-session` issues a random HttpOnly, SameSite=Strict browser cookie; it is Secure with the `__Host-` prefix in production. The endpoint requires the checkout gate to be enabled and responds with `Cache-Control: no-store`.
2. `POST /api/v1/orders` requires that cookie, a trusted `Origin`, and a unique 16–64 character `Idempotency-Key` header. A body key, if present, must match the header. A request without a session returns 428; malformed or missing keys are rejected.
3. The server normalizes and hashes the complete order request, then serializes attempts with the same key using a PostgreSQL transaction lock. The order row stores the key, request fingerprint and checkout cookie hash. The unique order-key index is the final database safeguard. A retry with the same key, cookie and normalized request returns the existing order. A changed request or different cookie receives 409 without order data. Historical unbound keys cannot be replayed.
4. The frontend generates a cryptographically random key and saves the exact pending payload and key in tab session storage. It obtains the cookie before sending the order. A lost response keeps that attempt; reopening checkout retries it. Successful responses clear the pending attempt. A changed form cannot silently overwrite an unresolved attempt. The cart clears after an existing attempt is confirmed only if its items still match that attempt.
5. Coupon usage, order header, lines and reservations commit together. Coupon rows are locked before checking usage limits. Inventory balance rows are locked in a stable order before multi-item reservations, and availability is checked under those locks. Physical stock adjustments take the same balance lock and cannot lower stock below active holds; fulfillment excludes the reservation it is closing.

The migration `b79e3a2f0d61` adds two nullable columns to `orders` so historical rows remain valid. Verification upgraded, downgraded and re-upgraded a disposable database and preserved an existing SAMPLE order. The development migration was additive; see `phase_b_development_before.json` and `phase_b_development_after.json` for table counts.

## Verification

Run backend tests sequentially from `backend` with `.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider`. Run frontend tests and build from `frontend` with `npm.cmd test` and `npm.cmd run build`. Real PostgreSQL tests cover simultaneous duplicate keys, last-unit buyers, reversed item order, coupon usage once, changed and foreign replays, second-line rollback and stock-adjustment protection. Frontend tests cover lost-response retries and persistence across a module reload. The migration check is `backend/scripts/verify_phase_b_migration.py`.

This phase does not change the payment deadline, supplier confirmation or fulfillment lifecycle. Those remain assigned to later phases of `frontend_integration_and_repair_plan.md`.
