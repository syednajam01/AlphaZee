"""
AlphaZee FastAPI application factory.

Architecture rules enforced here:
- CORS allows only configured origins; only GET methods for this milestone.
- The /docs and /redoc UIs are available only in development (debug=True).
- No database tables are created on startup — Alembic owns schema creation.
- The app is import-safe: all side effects (DB connection, etc.) happen at
  request time via FastAPI dependencies.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import health as health_router
from app.config import settings

# ── Application instance ──────────────────────────────────────────────────────
# Swagger UI (/docs) and ReDoc (/redoc) are disabled in production to avoid
# exposing schema details. Set DEBUG=true in .env to enable them locally.
app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description=(
        "AlphaZee catalog API — Milestone 1.\n\n"
        "Read-only endpoints for product catalog and application diagnostics. "
        "Admin, order, and payment endpoints are out of scope for this milestone."
    ),
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Allowed origins are configured via ALLOWED_ORIGINS in .env.
# Only GET is permitted — no write operations are exposed by this milestone.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["Accept", "Content-Type"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
# All public endpoints are versioned under /api/v1.
app.include_router(health_router.router, prefix="/api/v1")

# Catalog routes (Phase 3) will be registered here:
# app.include_router(collections_router.router, prefix="/api/v1")
# app.include_router(products_router.router, prefix="/api/v1")


# ── Root ──────────────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
def root() -> dict:
    """Minimal root response — confirms the API is reachable."""
    return {
        "service": settings.app_title,
        "version": settings.app_version,
        "environment": settings.app_env,
        "docs": "/docs" if settings.debug else "disabled",
    }
