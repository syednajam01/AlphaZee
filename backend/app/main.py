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

from app.api.v1 import admin as admin_router
from app.api.v1 import catalog as catalog_router
from app.api.v1 import coupons as coupons_router
from app.api.v1 import health as health_router
from app.api.v1 import orders as orders_router
from app.api.v1 import returns as returns_router
from app.config import settings

# ── Application instance ──────────────────────────────────────────────────────
# Swagger UI (/docs) and ReDoc (/redoc) are disabled in production to avoid
# exposing schema details. Set DEBUG=true in .env to enable them locally.
app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description=(
        "AlphaZee Commerce API.\n\n"
        "Endpoints for product catalog, storefront orders, payment verification, "
        "and owner inventory administration."
    ),
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Allowed origins are configured via ALLOWED_ORIGINS in .env.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Content-Type", "Authorization", "X-Admin-Key", "Idempotency-Key"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
# All public endpoints are versioned under /api/v1.
app.include_router(health_router.router, prefix="/api/v1")
app.include_router(catalog_router.router, prefix="/api/v1")
app.include_router(orders_router.router, prefix="/api/v1")
app.include_router(coupons_router.router, prefix="/api/v1")
app.include_router(returns_router.router, prefix="/api/v1")
app.include_router(admin_router.router, prefix="/api/v1")



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
