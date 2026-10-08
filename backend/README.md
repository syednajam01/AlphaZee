# AlphaZee Backend — Milestone 1

FastAPI catalog service and local development environment for AlphaZee.

---

## 1. Prerequisites

- **Python**: 3.13 (`.python-version` pinned to 3.13)
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
pytest tests/test_health.py -v
```
Tests run against `alphazee_test` on `localhost:5433`.
