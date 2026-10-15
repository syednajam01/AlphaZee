# AlphaZee — Pakistan Direct-to-Consumer Streetwear & Essentials

Current checkout containment and isolated test setup are documented in
[the Phase 0 runbook](.context/phase0_baseline_and_runbook.md).
Full development and production container deployment is documented in
[the Docker deployment runbook](.context/docker_deployment_runbook.md).
For the current full local stack, run `docker compose up --build --wait -d` from the
repository root. It starts PostgreSQL, runs Alembic migrations, and serves the
API and storefront on the host ports configured in your environment. The local
`.env.docker.local` stack uses localhost:18000 and localhost:13000. Production uses
`compose.prod.yml` with a private `.env.production` and a real HTTPS domain.
Public checkout is disabled server-side; only an explicitly configured local
test database can accept sample orders. Historical milestone notes below do not
establish current migration or launch readiness.
The current verification status is in
[the repair verification report](.context/repair_verification_report.md). All
automated and terminal checks are distinct from browser verification, which the
owner asked us to skip. Do not enable public checkout based on these checks.

AlphaZee is a Pakistan ecommerce brand with its own identity, storefront, customer relationships, order operations, and reporting.

---

## 1. Operating Model & Vision

- **Market**: Pakistan launch with prices quoted in PKR.
- **Fulfillment Model**: List products from approved local suppliers and manually coordinate fulfillment. Supplier shipping terms, payment mechanics, stock confirmation, and return arrangements are verified before offering items to customers.
- **Payment Methods**: Cash on Delivery (COD) and manual bank transfer. Transfer funds are personally verified in the bank account by the business owner before dispatching goods.
- **Current Milestone**: Owner workflows and accounting repairs implemented; final terminal verification recorded separately from browser and production launch checks.
- **Database State**: Development migrations have been applied through `e15a9c2b7046`. Disposable `_test` databases hold migration and concurrency evidence. No production deployment has been performed.

Direct owner dashboard: `http://localhost:13000/admin` for the local port profile.
Catalog lifecycle APIs are implemented; managed uploads and dashboard authoring
are the next phases. See [the M2 guide](.context/m2_catalog_runbook.md).

---

## 2. System Architecture

```
AlphaZee Workspace
├── frontend/             # Single Page Application (Vite, Vanilla JS, Custom CSS)
│   ├── src/components/   # Header, Hero, Collections, FeaturedProducts, CartDrawer, etc.
│   ├── src/utils/        # Central API client, money formatting, cart store
│   └── vite.config.js    # Dev server with /api proxy to backend:8000
├── backend/              # FastAPI service, commerce models, migrations and tests
│   ├── app/              # Catalog, orders, owner operations, access and accounting
│   ├── alembic/          # Versioned PostgreSQL migrations
│   └── tests/            # Pytest suite with guarded isolated database target
├── docker-compose.yml    # Development DB, migrations, API and Vite storefront
├── compose.prod.yml      # Production DB, migrations, API and HTTPS web server
└── docs/                 # Architecture, decisions, progress, and pending DB topics
```

---

## 3. Quickstart

The current full-stack path is `docker compose up --build --wait -d` as described
in the [Docker deployment runbook](.context/docker_deployment_runbook.md). The
split-service steps below remain available for manual local development.

### 3.1 Local PostgreSQL Database
```bash
docker compose up -d db
```
Spins up PostgreSQL 16 on host port `5433` (container port 5432).

### 3.2 Backend Service (Python 3.13)
```bash
cd backend
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```
- API root: `http://localhost:8000/`
- Health check: `http://localhost:8000/api/v1/health`
- Readiness check: `http://localhost:8000/api/v1/ready`
- Interactive docs: `http://localhost:8000/docs`

### 3.3 Frontend Storefront (Vite)
```bash
cd frontend
npm install
npm run dev
```
Serves storefront at `http://localhost:3000/`, proxying `/api` requests to backend on port 8000.

---

## 4. Documentation Index

- [`docs/architecture.md`](docs/architecture.md) — Implemented architecture, contracts, and invariants.
- [`docs/decisions.md`](docs/decisions.md) — Confirmed business decisions and proposed models.
- [`docs/progress.md`](docs/progress.md) — Completed work, test execution results, and deferred checks.
- [`docs/database-design-pending.md`](docs/database-design-pending.md) — Open database and commerce decisions for owner alignment.

## Owner Console access

Owner access uses username/password login and revocable HttpOnly sessions. After applying migrations, run `python scripts/provision_owner.py YOUR_USERNAME` interactively from `backend` to choose credentials. No default password or shared admin key grants access. See the [owner access runbook](.context/phase_a_owner_auth_runbook.md) for setup, password resets and production configuration.
