# AlphaZee Backend — Milestone 1

FastAPI catalog service and local development environment for AlphaZee.

---

## 1. Prerequisites

- **Python**: 3.13 (`.python-version` pinned to 3.13)
  > **Note on Python Version:** Python 3.13 is required. Python 3.14 (pre-release) introduces internal typing evaluation changes that trigger errors in SQLAlchemy 2.0 declarative mapper when scanning `Mapped[Optional[...]]` annotations. Python 3.13 is the stable release with full ecosystem support.
- **Docker & Docker Compose**: for local PostgreSQL
- **Git**

---

## 2. Quickstart

### 2.1 Start Local Database

From repository root (`f:/AlphaZee`):
```bash
docker compose up -d db
```
This spins up PostgreSQL 16 on port `5433` (container port 5432).

### 2.2 Setup Virtual Environment & Install Dependencies

From `backend/`:
```bash
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
```

### 2.3 Configure Environment Variables

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Default connection string:
```
DATABASE_URL=postgresql://alphazee:changeme@localhost:5433/alphazee_dev
APP_ENV=development
DEBUG=true
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

### 2.4 Run Development Server

```bash
uvicorn app.main:app --reload --port 8000
```
- API root: `http://localhost:8000/`
- Health check: `http://localhost:8000/api/v1/health`
- Readiness check: `http://localhost:8000/api/v1/ready`
- Interactive docs (when `DEBUG=true`): `http://localhost:8000/docs`

---

## 3. Running Tests

```bash
# Run unit and configuration tests (no database required):
pytest tests/test_config.py tests/test_readiness.py -v

# Run full integration tests (requires PostgreSQL running):
pytest tests/ -v
```
Integration tests run strictly against `alphazee_test` on `localhost:5433` and validate database targets before executing.

---

## 4. Database & Migration Verification Strategy

### 4.1 Schema Verification Boundary
Calling `Base.metadata.create_all()` inside test fixtures is a convenient test-isolation shortcut, but it **does not verify Alembic migrations**.

### 4.2 Alembic Environment Redirection
Alembic migrations read `DATABASE_URL` from application settings (`app.config.settings.database_url`). Setting `TEST_DATABASE_URL` alone does not redirect Alembic CLI commands. When testing migrations against an isolated test database, `DATABASE_URL` must be set explicitly:
```bash
$env:DATABASE_URL="postgresql://alphazee:changeme@localhost:5433/alphazee_test"
alembic upgrade head
```

### 4.3 Verified Migration Lifecycle Procedure
When migrations are authorized and generated, verify them against a guarded disposable test database using the full 4-step lifecycle:
1. **Upgrade**: `alembic upgrade head`
2. **Inspect**: Verify tables, unique indices (`NULLS NOT DISTINCT`), foreign keys, and check constraints match model definitions.
3. **Downgrade**: `alembic downgrade base` to verify full rollback cleanliness without leftover types or tables.
4. **Re-upgrade**: `alembic upgrade head` to confirm migrations are repeatable and idempotent from a clean state.

