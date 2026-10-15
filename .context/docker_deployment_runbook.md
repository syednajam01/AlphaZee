# Container deployment

The repository has separate development and production Compose stacks. Both run PostgreSQL, migrations, the FastAPI service, and the frontend. Development runs Vite with mounted source at `http://localhost:3000`; production builds static assets and serves them through Caddy with HTTPS and an `/api/*` reverse proxy. The API and database are private to the production Compose network. No browser was used to verify this setup.

## Local development

Docker Desktop (or Docker Engine with Compose) must be running. From the repository root:

```powershell
docker compose up --build --wait -d
docker compose ps
docker compose logs --tail=100 migrate api web
```

The site is on `http://localhost:3000`, API on `http://localhost:8000`, and PostgreSQL on loopback port 5433. Source edits reload in the Vite and API containers. `migrate` runs `alembic upgrade head` after the database is healthy; the API waits for migration success, and the web service waits for API readiness. The existing `alphazee_pgdata` volume is reused, so this does not reset development data. If local Vite or Uvicorn processes already occupy ports 3000 or 8000, stop those processes before bringing up the Compose stack. The development database credentials retain the existing local `alphazee/changeme` values; never use this Compose file for staging or production.

For a side-by-side terminal check while local processes still use those ports, copy `.env.docker.local.example` to `.env.docker.local` and use `docker compose --env-file .env.docker.local up --build --wait -d`. That example maps the site to port 13000 and the API to 18000. The internal Vite/API ports remain 3000/8000, and allowed origins follow `WEB_PORT`.

Terminal smoke checks:

```powershell
curl.exe -fsS http://localhost:3000/api/v1/ready
curl.exe -fsS http://localhost:3000/api/v1/storefront/capabilities
docker compose exec api python -m alembic current
```

Public checkout remains disabled by the API. To create an owner login after migration, use the existing interactive command: `docker compose exec api python scripts/provision_owner.py YOUR_USERNAME`. Credentials are chosen interactively and must not be put in Compose files. `docker compose down` stops the stack and retains database volume data. Never use `down -v` on a database you intend to keep.

## Production on a Docker host

Copy the repository to the host, point the domain's DNS A/AAAA records at it, and make TCP 80/443 (and optionally UDP 443) reachable so Caddy can obtain and renew certificates. Fill `.env.production` from `.env.production.example` with a unique project name, real domain, strong unique PostgreSQL password, and matching URL-encoded `DATABASE_URL` using hostname `db` and port 5432. Keep `.env.production` private and outside version control. Set real bank fields only after confirming them; placeholders leave bank transfer disabled. `APP_ENV=production`, HTTPS-only allowed origin, debug off, and public checkout containment are fixed in the production Compose file.

Before each production deployment, back up PostgreSQL and retain a restorable copy. Migrations run automatically before the API starts and may change schema; rolling back an image does not reverse a migration. Review new migrations against a copy of production data first. A production preflight refuses the example domain, placeholder or short database passwords, non-HTTPS origin, debug mode, and test checkout mode before migrations run.

```sh
docker compose --env-file .env.production -f compose.prod.yml config --quiet
docker compose --env-file .env.production -f compose.prod.yml up --build -d
docker compose --env-file .env.production -f compose.prod.yml ps
docker compose --env-file .env.production -f compose.prod.yml logs --tail=100 migrate api web
```

Check `https://YOUR_DOMAIN/api/v1/ready`, `https://YOUR_DOMAIN/api/v1/storefront/capabilities`, and the static home page with `curl`. The production project has its own `pgdata`, `caddy_data`, and `caddy_config` volumes; it does not reuse the development database. Provision the owner interactively with `docker compose --env-file .env.production -f compose.prod.yml exec api python scripts/provision_owner.py YOUR_USERNAME` after the stack is healthy. Use `docker compose ... exec -T db pg_dump -U YOUR_DB_USER -d YOUR_DB_NAME -Fc` to create a PostgreSQL backup, directed to a protected file on the host. Store backups off-host as well.

The production frontend is static; redeploy after frontend edits. Production readiness depends on valid DNS/TLS, real deployment credentials, browser verification and a launch decision, so local development checks alone do not constitute a production launch. Secure order access, exchanges and financial settlements are implemented in the application; containerization does not open public checkout.


## Managed media and persistent owner accounts (M3/M4)

M8 adds `compose.checkout-lab.yml`: independent project/database/media, web on 127.0.0.1:13001, API 18001, PostgreSQL 5434. Its API/migrations share the DB namespace to satisfy the existing loopback test checkout gate. Only the lab opens checkout; it has a SAMPLE banner, simulated bank configuration and distinct owner/order/checkout cookies. Provision a separate owner interactively and use the explicit catalog-only export/import tool. See the [M8 runbook](m8_checkout_lab_runbook.md). Keep this Compose file separate from normal and production deployments.

M7 operational/report changes require no new environment settings or migration. Both development and production images build successfully. The acceptance-only `compose.operations-check.yml` must be combined with `compose.media-check.yml`; it adds synthetic bank settings solely for the isolated test database. See [M7 verification and operating steps](m7_operations_runbook.md). Normal checkout remains disabled.

The API now mounts its project’s named `catalog_media` volume at `/var/lib/alphazee/catalog-media`, with non-root ownership and FFmpeg/FFprobe in the image. Development and production use independent volumes. PostgreSQL preserves owner credentials; the requested `syed123` local account was verified after a database/API restart. Normal shutdown retains both volumes; `down -v` removes them. Back up database and media as one matched set with all API/import/cleanup writers stopped. See [the exact storage and matched restore procedure](m3_media_runbook.md) and [the authoring guide](m4_catalog_authoring_runbook.md). M4 has actual isolated browser evidence; no production deployment or public checkout opening occurred.
