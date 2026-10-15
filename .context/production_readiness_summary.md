# AlphaZee: shop and production readiness

Reviewed 2026-10-15 against current backend, database models, deployment files and recorded M9 evidence. This is a readiness assessment; no deployment or checkout settings were changed.

## Direct answer

**The core backend is substantially implemented, but the app is not yet ready to accept real public orders.** You can begin configuring an Azure development/staging environment now, then verify it there. Completing M0–M9 means the local milestone passed; it does not mean production launch is complete.

Your intended model fits an **owner-operated store using vendors for supply and earning a retail margin**. You manage products, suppliers, orders and payments. Vendors do not currently have a finished self-service marketplace portal.

## What is implemented

| Area | Working scope |
| --- | --- |
| Owner access | Persistent accounts, hashed passwords, expiring/revocable sessions, protected admin APIs, Origin/CSRF checks and login throttling. |
| Catalog | Products, variants, collections, draft/publish/archive, prices, descriptions, images/videos/posters and durable media storage. Purchased history survives archival. |
| Vendors and inventory | Supplier registration, active supplier/variant mappings, wholesale costs, audited stock adjustments, physical/reserved/available quantities and supplier confirmation. |
| Cart and orders | Stable-ID cart recovery, authoritative prices, coupons, transactional stock holds, duplicate-submit recovery and immutable purchase/cost/address snapshots. |
| Fulfillment | Manual courier/tracking entry, dispatch/delivery, pre-dispatch cancellation and return-to-origin receipt/inspection. Stock changes follow fulfillment events. |
| After-sales | Private tracking/access codes, customer returns, size exchanges, replacement shipments, inspected restocking, refund liabilities and separately recorded refund payments. |
| Reporting | Delivered sales, recorded bank receipts, courier-held COD, partial/final COD settlements, refunds, supplier costs, courier expenses, estimated contribution and marketing attribution. |
| Infrastructure | Docker development/production packaging, migrations, health checks, persistent database/media volumes, HTTPS proxy configuration and documented backup/restore procedures. |

## Your two payment methods

- **COD:** order → supplier confirmation → dispatch → delivery → record courier receipts/deductions. Delivery and money reaching your bank are separate events.
- **Bank transfer:** order → supplier confirmation → explicitly send/record bank instructions → customer transfers → you check actual received funds and verify payment → dispatch. The backend blocks bank-order dispatch until payment is verified. Instructions start a four-hour deadline; overdue funds require manual review before cancellation releases stock.
- Bank configuration must be valid. Proof currently accepts a reference/image URL; there is no dedicated private receipt-file upload service. Agree a practical proof/support channel, or add secure private uploads if required.

**A card gateway or automatic bank integration is unnecessary for this chosen payment model.** Actual transfers and refunds remain manual; the application records your decisions/evidence.

## What remains before public launch

1. **Production checkout release — code work.** Checkout currently works only in the isolated test lab. Production order creation returns 503. Add an explicit production release mechanism with regression coverage; setting the existing test flag cannot enable production safely.
2. **Vendor payments — business-critical gap.** Wholesale cost snapshots exist, but no supplier payable/payout ledger records amounts owed, payments, balances or vendor statements. Build this if the app must manage vendor money, or adopt a clearly maintained external ledger initially. Estimated contribution excludes general overhead/tax and is not final profit; reported business cash also does not subtract supplier payouts.
3. **Shipping and commercial rules — decide, then implement as needed.** Customer order creation currently leaves shipping at the service default of zero. Choose intentional free delivery or implement server-calculated fees/coverage. Confirm who ships mixed-vendor orders and bears return/exchange costs; current original dispatch creates one shipment for the order, not independent vendor parcels. Finalize return windows, eligibility and refund rules. Tax/invoice accounting is not a completed subsystem.
4. **Real store setup.** Enter actual catalog, supplier costs/stock, bank details and support contacts. Publish privacy, terms, delivery and return information: current privacy/terms links are unset. Check customer-facing promises against your actual operations.
5. **Cloud operations and acceptance.** Configure secrets, persistent storage, HTTPS/domain, restricted database access, off-host matched DB/media backups, a tested restore, logs/alerts and an upgrade/rollback procedure. Verify payments, access control, migrations and restart persistence on Azure. Public-traffic/load and production proxy/rate-limit behavior still need assessment; local tests do not establish capacity or a complete security audit.

## Azure development/staging

The existing Compose layout makes a **Linux VM running Docker Compose a reasonable initial staging option**; this is an architectural recommendation, not a tested Azure deployment. Keep staging separate from real customer data and restrict access. Use production-style HTTPS configuration; checkout remains closed until a separate release change. Keep the checkout lab local.

Store PostgreSQL and media volumes on persistent storage, with backups outside the host. Azure managed data disks provide persistent VM storage; temporary disks are unsuitable for this data. See [Microsoft's disk guidance](https://learn.microsoft.com/en-us/azure/virtual-machines/linux/tutorial-manage-disks).

Azure managed PostgreSQL or a managed container platform requires adapting the deployment: the current production preflight specifically requires `db:5432`, and media uses a filesystem volume. Azure provisioning and CI/CD are not supplied in this repository. Follow the existing [Docker runbook](docker_deployment_runbook.md) as the packaging baseline.

## What can wait, and recommended order

Vendor self-service, automated courier booking/tracking, email/SMS/WhatsApp notifications, customer accounts, reviews and advanced marketplace commission/split-payment features are future additions. They are not prerequisites for an owner-operated store if you handle those operations manually.

**Next:** settle vendor accounting/shipping/fulfillment rules → close required backend gaps and implement the production checkout gate → verify Azure staging → improve frontend UX and public store information → rehearse both payment/return flows → approve public launch. Frontend redesign can proceed alongside staging; it does not require rebuilding the completed backend.

Evidence: [M9 report](m9_implementation_report.md) records 260 backend tests, 108 frontend tests and 228 browser checks, plus builds/migration/persistence checks. Those are prior recorded results, not newly rerun tests or proof of production readiness. This review inspected current code/configuration; no browser session or application test suite was run for this documentation-only task.
