# AlphaZee — Pakistan Direct-to-Consumer Streetwear & Essentials

Current checkout containment and isolated test setup are documented in
[the Phase 0 runbook](.context/phase0_baseline_and_runbook.md).
Full development and production container deployment is documented in
[the Docker deployment runbook](.context/docker_deployment_runbook.md).
For the current full local stack, run `docker compose up --build --wait -d` from the
repository root. It starts PostgreSQL, runs Alembic migrations, and serves the
API and storefront at localhost:8000 and localhost:3000. Production uses
`compose.prod.yml` with a private `.env.production` and a real HTTPS domain.
Public checkout is disabled server-side; only an explicitly configured local
test database can accept sample orders. Historical milestone notes below do not
establish current migration or launch readiness.

AlphaZee is a Pakistan ecommerce brand with its own identity, storefront, customer relationships, order operations, and reporting.

---

## 1. Operating Model & Vision

- **Market**: Pakistan launch with prices quoted in PKR.
- **Fulfillment Model**: List products from approved local suppliers and manually coordinate fulfillment. Supplier shipping terms, payment mechanics, stock confirmation, and return arrangements are verified before offering items to customers.
- **Payment Methods**: Cash on Delivery (COD) and manual bank transfer. Transfer funds are personally verified in the bank account by the business owner before dispatching goods.
- **Current Milestone**: Catalog foundation, frontend integration, resilient cart, preview safety, test isolation, and architectural documentation.
- **Database Pause Boundary**: Discussion on the finalized database design is in progress. No migrations, seed data, or schema alterations have been applied to live or development databases.

---

## 2. System Architecture

```
AlphaZee Workspace
├── frontend/             # Single Page Application (Vite, Vanilla JS, Custom CSS)
│   ├── src/components/   # Header, Hero, Collections, FeaturedProducts, CartDrawer, etc.
│   ├── src/utils/        # Central API client, money formatting, cart store
│   └── vite.config.js    # Dev server with /api proxy to backend:8000
├── backend/              # RESTful API Service (FastAPI, Python 3.13)
│   ├── app/models/       # Catalog models (Collection, Product, Variant)
│   ├── app/queries/      # Read queries with deterministic ordering and eager loads
│   ├── app/api/v1/       # Endpoints (/collections, /products, /products/hero, /health, /ready)
│   ├── alembic/          # Migration environment (create_engine directly, .gitkeep)
│   └── tests/            # Pytest test suite with guarded disposable database target
├── docker-compose.yml    # PostgreSQL 16 on port 5433
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
