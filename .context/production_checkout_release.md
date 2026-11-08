# Production checkout release — 2026-11-06

**Live update, 2026-11-08:** checkout is now enabled at alphazee.tech in production mode, with COD and owner-confirmed temporary All Pakistan shipping of PKR 200. Runtime/CI expectations and the active environment snapshot were updated together. See `.context/live_checkout_activation.md` for verified behavior and current operating instructions. The initial implementation evidence below is historical.

The owner authorized implementing public checkout. The application now has a separate `PRODUCTION_CHECKOUT_ENABLED` switch. This supersedes older documentation saying a production release mechanism does not exist. No Azure deployment or live customer transaction has occurred.

## Deploy and enable

Use `compose.prod.yml`, a real HTTPS origin and strong production credentials from `.env.production.example`. Keep `APP_ENV=production`, `DEBUG=false`, `TEST_CHECKOUT_ENABLED=false`, `CHECKOUT_LAB=false`. Set **`PRODUCTION_CHECKOUT_ENABLED=true`** in the private host `.env.production` when the store is ready. Compose passes it to API and migrations. The example defaults to false so an unconfigured deployment cannot accidentally take orders.

On the Linux deployment host:

```sh
docker compose --env-file .env.production -f compose.prod.yml config --quiet
docker compose --env-file .env.production -f compose.prod.yml up --build --wait -d
```

Capabilities must report `checkout_enabled: true`, `test_mode: false`. Production browser checkout sessions use Secure, HttpOnly, SameSite cookies with the `__Host-` prefix. The frontend accepts explicit production capabilities and still closes checkout when capability loading fails. Quote, order and browser-session endpoints use the same release gate.

Test checkout retains its original isolated database/environment restrictions. The production flag cannot enable development or test environments. Production release refuses debug mode, lab/test flags, weak/placeholder DB credentials, `_test` databases and query overrides; existing HTTPS origin validation remains enforced. No schema migration is required.

## Close new orders

Set `PRODUCTION_CHECKOUT_ENABLED=false` and rerun the production Compose command. Recreating/restarting with the updated environment closes new checkout sessions, quotes and order creation with 503. Existing orders, stock holds, tracking and admin fulfillment remain intact. A flag change in a file alone does not update a running process. Requests already in progress may finish; do not interpret this as cancelling orders or refunding customers.

## Configure real commerce before customers

- Create a strong production owner interactively; do not reuse the short development account option.
- Publish actual catalog/media, confirmed inventory, supplier costs and agreements. Do not copy test orders or the personal-media preview into the public catalog.
- Explicitly activate delivery coverage/fees in admin. Production quote/order services reject unconfigured delivery rules instead of silently assuming free delivery.
- Configure valid bank details if offering manual transfers; otherwise the API offers COD only. Bank proof still requires manual funds verification. Card payments are not implemented by this release.
- Finalize real support details, published policies and return/refund operations.
- Verify HTTPS, proxy/throttling behavior, off-host database/media backups and a restore; then rehearse browser checkout, idempotent retry, sold-out/stale-total recovery and order tracking in Azure.

Your Azure for Students account remains a learning/staging resource subject to its offer terms. Confirm suitable commercial hosting before real sales. A switch enabling orders is not evidence of cloud uptime, production acceptance or completed business configuration.

## Terminal evidence

Executed: **64 backend tests passed** against a fresh disposable database (93.21s; one existing AnyIO deprecation), **138 frontend tests passed**, final Vite build passed. Backend evidence: `.local/production-checkout-tests.txt` and `.xml`. Coverage includes rejected release configurations, startup preflight true/false/typo values, production capabilities/Secure cookies, actual production-mode quote/order creation, exact shipping total, retry without duplicate holds, switch-off retaining the existing order, isolated lab restrictions, private access, bank lifecycle and cancellations. No customer/development stock was consumed. No migration was added.

The first intermediate run preceded the final capability/import fixes and failed two new checks; the final run above passed. Production API and final frontend image builds passed, as did production Compose `config --quiet`. This does not constitute an Azure deployment.

## Antigravity cloud/browser acceptance

1. Use the deployed production-style HTTPS origin with a controlled acceptance catalog, no real transfer. Confirm release false disables checkout in the UI and returns 503 for session/quote/order endpoints.
2. Enable the production flag and recreate containers. Confirm capabilities true with test mode false; header/cart/checkout must contain no SAMPLE or preview claim. Test bank unavailable until valid configuration.
3. Confirm a valid item/variant, configured delivery coverage and accurate quoted totals. Test out-of-area address, stale total, out-of-stock item, validation/retry and double-click/lost-response recovery. Verify exactly one order/stock hold, not only a confirmation screenshot.
4. Confirm secure customer cookies, private tracking/access recovery, wrong-Origin rejection and inability to read another order. Rehearse COD and configured manual-bank fulfillment; transfer proof alone cannot authorize dispatch.
5. Close checkout again: new attempts fail, existing order tracking/admin workflows still work. Restart/recreate and verify persistence. Do not delete the acceptance order/ledger history to fake cleanup.
6. Record actual browser results, deployed image/revision, failures and screenshots in `.context/production_checkout_browser_report.md`. Keep secrets/access codes/customer data out of evidence. A real-customer launch remains dependent on owner-approved catalog/policies, operational readiness and suitable cloud subscription.

Prior Azure guides' statements that checkout is lab-only are historical; use this document for current enable/disable instructions. Browser acceptance after deployment remains pending.
