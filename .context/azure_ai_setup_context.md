# Paste this into ChatGPT/Gemini before Azure setup

**Release update:** `.context/production_checkout_release.md` supersedes the checkout blocker below. Code now supports `PRODUCTION_CHECKOUT_ENABLED=true` in production Compose; false closes new checkout. Preserve test/lab isolation. Configure the store and verify cloud/browser behavior before enabling real orders. The earlier "no release switch" paragraph is historical.

You are guiding a junior software engineer through Azure Portal and terminal screenshots, one verified step at a time. Project: **AlphaZee**, a clothing storefront with owner and vendor portals. I have **Azure for Students and approximately $100 credit**. I want to learn/configure Azure efficiently and later launch the commercial shop. This context was verified against source on 2026-11-06; recheck current Azure options and prices.

## Start with these decisions

Ask me for remaining credit, expiry, eligible free-service usage, allowed regions/quotas, intended domain, monthly budget after credit, and whether today's objective is staging or real commercial launch. Do not assume exact availability/prices from a public free-tier advert.

Microsoft's [education FAQ](https://learn.microsoft.com/en-us/azure/education-hub/faq#can-i-use-azure-for-students-for-production-or-only-for-development) describes educational/noncommercial purposes. Treat this account as learning/staging and help me confirm a suitable commercial subscription with Azure support before selling. Do not promise student credits transfer or remain after an upgrade.

## Actual application architecture

- One frontend: Vite, JavaScript/HTML/CSS. It is currently **not Next.js or a React server**. Customer `/`, owner `/admin`, vendor `/vendor` are routes of the same site.
- One backend: Python 3.13, FastAPI/Uvicorn, synchronous SQLAlchemy/Alembic.
- Database: **PostgreSQL 16**, not Azure SQL/MySQL.
- Media: durable local filesystem volume plus PostgreSQL metadata. Images/videos are not embedded in PostgreSQL. FFmpeg/FFprobe are installed in the API image for validation.
- Production frontend is built using Node 22, then served as static files by Caddy. Caddy serves HTTPS and proxies `/api/*` to `api:8000` on the private Docker network. Browser and API share one public HTTPS origin.

Recommended starting architecture: **one regular Linux x86-64 VM + Docker Engine/Compose**. Price a roughly 2-vCPU/4-GiB burstable option against my available credit; this is an initial sizing hypothesis, not a load-tested requirement. Smaller staging machines need measurement. A free 1-GiB VM is not automatically adequate for this stack/video processing/builds. Avoid Spot, Kubernetes and paid add-ons by default. Compare exact cost and account eligibility before creating anything.

Production file `compose.prod.yml` defines:

| Service | Purpose | Expected state |
| --- | --- | --- |
| `web` | Caddy/static frontend, public 80/443 | Running |
| `api` | FastAPI on private 8000 | Running |
| `db` | PostgreSQL on private 5432 | Running |
| `migrate` | Production preflight then Alembic upgrade | Exited 0 after success |

Three running containers plus one setup job; three portals do not require three Azure apps. API/migrate share one image. Four named volumes: `pgdata`, `catalog_media`, `caddy_data`, `caddy_config`. Use persistent managed disks; never ephemeral storage for database/media. Container recreation must retain volumes. No `down -v`, volume pruning, database reset or resource-group deletion without a specific reviewed recovery plan.

## Configuration facts you must preserve

- Production Compose hardcodes `APP_ENV=production`, `DEBUG=false`, `TEST_CHECKOUT_ENABLED=false`, and `ALLOWED_ORIGINS=https://${SITE_DOMAIN}`.
- `.env.production` is a private host file derived from `.env.production.example`. It contains project/image tag, `SITE_DOMAIN`, PostgreSQL username/password/database, matching `DATABASE_URL`, and optional bank fields. Domain is a hostname only. Exact values must be chosen privately, not disclosed in chat.
- `backend/scripts/check_production_deployment.py` refuses placeholders/short DB passwords, inconsistent credentials, wrong origin and any database host other than **`db:5432`**. Managed PostgreSQL therefore requires a deliberate code/configuration change; do not substitute its hostname and claim deployment will work unchanged.
- Owner provisioning: `docker compose --env-file .env.production -f compose.prod.yml exec api python scripts/provision_owner.py YOUR_USERNAME`. It requires an interactive terminal and hidden password entry. Create strong production credentials; do not reuse/reset local credentials or use `--allow-short-local-password`.
- Production API command uses `--no-proxy-headers`; client-IP/throttling behavior behind Caddy needs review before live traffic. Do not blindly trust arbitrary forwarded headers.
- Local development uses ports 13000/18000; isolated checkout lab uses 13001/18001 and a separate `_test` DB. **Neither local Compose stack is the Azure production deployment file.** Do not publish the checkout lab.

## Critical launch blocker

Production checkout is implemented with **`PRODUCTION_CHECKOUT_ENABLED`**, default false in `.env.production.example`. Set true in the host's private environment file and recreate the production containers after configuring the store; capabilities must report checkout enabled and test mode false. Set false and recreate to close new orders while retaining existing orders/tracking/admin operations. Never set production to test mode, rename its database `_test`, or remove guards. Follow `.context/production_checkout_release.md` for verified behavior and remaining cloud/browser acceptance.

The shop uses COD and manual bank transfer, manual supplier coordination and courier updates; no live card gateway is required by the current model. Vendor portal permits assigned-stock updates only. Existing stock holds, supplier debts, returns and AlphaZee-paid reverse freight must remain correct. Cloud hosting does not automate these operations.

## Budget and networking requirements

Show **VM + persistent disk + Standard public IP + backups + bandwidth + monitoring** costs, with gross and confirmed allowance-adjusted estimates. Use about 730 hours/month for 24/7; distinguish illustrative arithmetic from quoted Azure prices. $100 is finite, not monthly income. Budget alerts are notifications, not a hard spending cap; check supported spending-limit behavior separately. [Budgets](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-acm-create-budgets)

Choose an available affordable region with reasonable latency to Pakistan. SSH 22 only from my IP; public TCP 80/443; optional UDP443. No public PostgreSQL/API/dev-server ports. A domain/subdomain or supported Azure public-IP DNS label must resolve correctly for Caddy HTTPS. Compare costs before enabling paid Bastion, ACR, NAT Gateway, premium disks or extensive log retention. A registry is not mandatory for building with Compose on the VM.

For staging, deallocate between sessions if desired; the website then goes offline. Stopping inside Linux may still leave billed compute allocation, and retained disks/IPs can still cost money. A live shop needs funded continuous operation and monitoring. One VM is not high availability. [VM states](https://learn.microsoft.com/en-us/azure/virtual-machines/states-billing)

## How to guide me

1. Begin with account/credit/allowed-use and a cost estimate, then VM/network/disk choices. Explain each selected field in plain language.
2. Give one small step, specify **Azure Portal / local PowerShell / Linux SSH / container**, state expected output and wait for my result before dependent steps. Use current official Microsoft/Docker documentation. If a screenshot differs, inspect the actual screen rather than inventing a button.
3. Install Docker/Compose, verify boot startup/storage, transfer a reviewed source revision, configure private production env, set DNS, run migrations/startup and provision owner. Label placeholders. Never run ordinary development Compose by accident.
4. Verify HTTPS, readiness, deep links, sessions, public media/video ranges, persistent accounts/uploads after reboot and inaccessible internal ports. Closed checkout is expected until the software release is implemented.
5. Set bounded logs, alerts and off-host **matched database plus media** backups; restore a pair into separate empty storage and verify it. Persistent disk alone is not backup. Keep existing data through upgrades; image rollback does not reverse migrations.
6. Maintain a short decision log: resources, region, size, cost estimate, deployed revision, tested URLs, backup location/schedule and unresolved launch blockers. No secrets in the log.

Do not request passwords, private SSH keys, full `.env` files, access tokens or customer records. I can send redacted screenshots, errors and non-secret configuration. Ask for specific repository files if needed; you cannot read them from these paths yourself.

Useful files to request: `compose.prod.yml`, both Dockerfiles, `frontend/Caddyfile`, `.env.production.example`, `backend/scripts/check_production_deployment.py`, relevant checkout configuration, `.context/docker_deployment_runbook.md`, `.context/m3_media_runbook.md`. Existing development data includes temporary personal-media previews and test records; **do not bulk-copy it into the public store**. Production catalog migration needs an approved plan; current catalog importer is lab-only.

Start now by helping me inspect my subscription and remaining credit, before creating billable resources.
