# Live checkout enabled — 2026-11-08

Owner authorized enabling production checkout for friends to try. The owner also confirmed the saved temporary delivery rules: **All Pakistan, PKR 200 shipping, no free-shipping threshold**, pending discussion with couriers.

## Current live behavior

- Website: https://alphazee.tech
- `checkout_enabled=true`; `test_mode=false`.
- Payment method currently available: **Cash on Delivery**. Bank transfer was not enabled or given fabricated account details.
- Shipping: **PKR 200**, across **All Pakistan**. Admin-confirmed delivery rules are now active.
- Orders submitted by visitors are real production records and can reserve real stock. Sharing the site only with friends does not impose an invite-only restriction.

## What changed

The necessary application code was already deployed as `d39e86c`. No new image build, database migration, stock adjustment, account reset or source default change was needed.

1. The existing settings service confirmed shipping rules with version checking and an audit reason recording the owner's temporary rate approval. The maintenance actor is null/system; no owner's login was impersonated.
2. The VM's private `PRODUCTION_CHECKOUT_ENABLED` was changed to true. Only that environment setting changed; other private values and file ownership were preserved.
3. CI's private host configuration now expects checkout enabled, so the next deployment's health check accepts the intended state.
4. A new root-private runtime environment snapshot was created, then only the API container was recreated using the existing digest-pinned release files. The frontend reads checkout capabilities at runtime.
5. The release-state environment path/hash was updated to match the active configuration. Original private settings were retained for recovery under `/var/lib/alphazee-cicd/config-releases/checkout-enable-1794099256834712108/`; do not publish those files.
6. The obsolete default announcement saying public ordering was closed was replaced, through the audited settings service, with “Checkout is open • Cash on delivery available”. Custom branding and policies were preserved.

## Actual verification

- Production preflight passed with the new configuration before it was activated.
- Live capabilities report enabled checkout, normal production mode and COD.
- Live checkout session succeeded with a Secure, HttpOnly `__Host-alphazee_checkout` cookie. Cookie values were not logged.
- A real quote for one available item and Karachi/Sindh returned PKR 1,500 subtotal + PKR 200 delivery = PKR 1,700, with confirmed shipping rules.
- Headless Chrome used the real live site/API at 390×844: product variant → shopping bag → enabled checkout → COD → quote-review total. SAMPLE form values stayed in the browser; the quote request contained only item IDs, quantity and city/province. Actual order POSTs were explicitly blocked in the verification browser, and zero order attempts occurred.
- The separate final confirmation was never clicked. **No verification order or stock reservation was created.**

The initial browser check expected an automatic quote after entering a city/province. The implemented flow requests the quote on the first “Place Order” click, then asks for a separate confirmation. The corrected verification followed that actual flow successfully.

## What friends should do

Open the site or refresh an already-open tab, choose the product/size/color, add it to the bag, and proceed to checkout. Fill delivery details and use COD. The first “Place Order” click calculates the server-confirmed total; review the PKR 200 delivery fee, then click the separate “Confirm order” button only when intending to submit.

Monitor submitted orders in `/admin/orders`. Friend test orders are still production orders; use normal admin cancellation/fulfillment workflows rather than deleting database records manually.

## Changing courier rates tomorrow

Go to **Admin → Store Settings → Shipping & thresholds**. Update delivery coverage, shipping fee and any free-shipping threshold; keep the delivery confirmation checkbox correct, then save. The saved server rules apply to new quotes/orders without a code deployment. Existing orders retain their original snapshotted totals.

For disabling checkout later, change the production runtime switch and CI's expected state together, create/update the active private environment snapshot and recreate the API from the current release files. Editing only `.env.production` does not change the already-running container or its active snapshot. Never switch the live server into lab/test mode to test orders.

Simple explanation of the earlier deployment problems: [cicd_explained_simply.md](cicd_explained_simply.md).
